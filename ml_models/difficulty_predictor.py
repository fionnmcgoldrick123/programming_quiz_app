"""
Coding Problem Difficulty Predictor
====================================
Predicts easy / medium / hard for a coding problem using scikit-learn.

Data sources (all from CODENET_PATH):
  - metadata/problem_list.csv  — time_limit, memory_limit per problem
  - metadata/p*.csv            — per-problem submission records
                                 -> acceptance_rate, avg_cpu_time, avg_memory, avg_code_size
  - problem_descriptions/*.html — problem statement text -> TF-IDF + keyword features

Models trained:
  Random Forest, Gradient Boosting, XGBoost (if available),
  Linear SVM, Logistic Regression, kNN

Run:
  python ml_models/difficulty_predictor.py
"""

import os
import re
import glob
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from html.parser import HTMLParser

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
)
from sklearn.inspection import permutation_importance
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    from imblearn.over_sampling import SMOTE
    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False
    print("imbalanced-learn not installed — SMOTE disabled. Run: pip install imbalanced-learn")

# ============================================================
# Config — reads CODENET_PATH from .env if available
# ============================================================

def _load_codenet_path() -> str:
    """Read CODENET_PATH from .env file or fall back to env var."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("CODENET_PATH"):
                    _, _, val = line.partition("=")
                    return val.strip()
    return os.environ.get("CODENET_PATH", r"C:\Users\fionn\data-sets\Project_CodeNet")


CODENET_PATH = _load_codenet_path()
MODEL_SAVE_PATH = os.path.join(os.path.dirname(__file__), "difficulty_model.pkl")

# Cache files so the slow CSV-aggregation loop only runs once
_CACHE_DIR        = os.path.dirname(__file__)
STATS_CACHE_PATH  = os.path.join(_CACHE_DIR, "_cache_stats.csv")
DESC_CACHE_PATH   = os.path.join(_CACHE_DIR, "_cache_desc.csv")

# ============================================================
# HTML text extractor (stdlib only, no beautifulsoup needed)
# ============================================================

class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML -> plain text extractor using stdlib HTMLParser."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def html_to_text(html: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    p = _HTMLTextExtractor()
    p.feed(html)
    return re.sub(r"\s+", " ", p.get_text()).strip()


# ============================================================
# Feature extraction from problem descriptions
# ============================================================

_RECURSION_KW = ["recursion", "recursive", "fibonacci", "factorial", "backtrack", "divide and conquer", "merge sort", "quicksort"]
_DP_KW        = ["dynamic programming", " dp ", "memoization", "memoisation", "tabulation", "longest common", "knapsack", "coin change", "edit distance", "subarray sum"]
_GRAPH_KW     = ["graph", " tree", "node", "edge", " path", "bfs", "dfs", "dijkstra", "topological", "spanning tree", "shortest path", "connected component", "cycle", "bipartite", "adjacency"]
_SORT_KW      = ["sort", "order", "ascending", "descending", "minimum", "maximum", "priority queue", "heap", "median", "kth largest", "kth smallest"]
_SEARCH_KW    = ["binary search", "search", "find the k", "lower bound", "upper bound", "bisect"]
_STRING_KW    = ["string", "substring", "palindrome", "anagram", "character", "lexicograph", "concatenat", "prefix", "suffix", "regex", "pattern match"]
_MATH_KW      = ["prime", "gcd", "lcm", "modulo", "modular", "combinat", "permut", "factorial", "fibonacci", "power", "sqrt", "logarithm", "matrix", "determinant"]
_GREEDY_KW    = ["greedy", "interval", "schedule", "activity selection", "minimum cost", "maximum profit", "locally optimal"]
_STACK_KW     = ["stack", "queue", "deque", "monotonic", "bracket", "parenthes", "balanced"]
_COMPLEXITY_KW = ["o(n)", "o(n^2)", "o(log n)", "o(n log n)", "o(1)", "time complexity", "space complexity", "complexity"]


def extract_description_features(html: str) -> dict:
    """
    Extract numeric + text features from a problem HTML description.

    Numeric features:
      desc_char_len, desc_word_count, num_sample_inputs,
      has_constraints, has_recursion_keywords, has_dp_keywords,
      has_graph_keywords, has_sort_keywords, has_search_keywords,
      has_string_keywords, has_math_keywords, has_greedy_keywords,
      has_stack_keywords, has_complexity_keywords,
      num_large_numbers, num_code_tokens

    Text field (for TF-IDF):
      description_text
    """
    text = html_to_text(html)
    lower = html.lower()
    text_lower = text.lower()

    # Count numbers >= 1000 (large constraint values hint at harder problems)
    large_numbers = len(re.findall(r'\b\d{4,}\b', text))
    # Count code-like tokens: sequences of uppercase letters (e.g. N, M, K variable names)
    code_tokens = len(re.findall(r'\b[A-Z][A-Z0-9_]*\b', text))

    return {
        "desc_char_len":            len(text),
        "desc_word_count":          len(text.split()),
        "num_sample_inputs":        lower.count("sample input"),
        "has_constraints":          int("constraints" in lower),
        "has_recursion_keywords":   int(any(w in text_lower for w in _RECURSION_KW)),
        "has_dp_keywords":          int(any(w in text_lower for w in _DP_KW)),
        "has_graph_keywords":       int(any(w in text_lower for w in _GRAPH_KW)),
        "has_sort_keywords":        int(any(w in text_lower for w in _SORT_KW)),
        "has_search_keywords":      int(any(w in text_lower for w in _SEARCH_KW)),
        "has_string_keywords":      int(any(w in text_lower for w in _STRING_KW)),
        "has_math_keywords":        int(any(w in text_lower for w in _MATH_KW)),
        "has_greedy_keywords":      int(any(w in text_lower for w in _GREEDY_KW)),
        "has_stack_keywords":       int(any(w in text_lower for w in _STACK_KW)),
        "has_complexity_keywords":  int(any(w in text_lower for w in _COMPLEXITY_KW)),
        "num_large_numbers":        large_numbers,
        "num_code_tokens":          code_tokens,
        "description_text":         text,
    }


# ============================================================
# Build per-problem submission stats
# ============================================================

def build_problem_stats(codenet_path: str) -> pd.DataFrame:
    """
    Aggregate each per-problem submission CSV into one summary row.

    Computed features:
      num_submissions, acceptance_rate,
      avg_cpu_time, avg_memory, avg_code_size

    Results are cached to STATS_CACHE_PATH so the slow loop runs only once.
    """
    if os.path.exists(STATS_CACHE_PATH):
        print(f"Loading stats from cache: {STATS_CACHE_PATH}")
        return pd.read_csv(STATS_CACHE_PATH)

    metadata_dir = os.path.join(codenet_path, "metadata")
    csv_files = sorted(glob.glob(os.path.join(metadata_dir, "p*.csv")))

    rows = []
    t0 = time.time()
    print(f"Aggregating {len(csv_files)} per-problem CSVs ...")

    for i, csv_path in enumerate(csv_files):
        if i % 500 == 0 and i > 0:
            elapsed = time.time() - t0
            print(f"  {i}/{len(csv_files)}  ({elapsed:.1f}s elapsed)")

        problem_id = os.path.splitext(os.path.basename(csv_path))[0]

        try:
            df = pd.read_csv(
                csv_path,
                usecols=["status", "cpu_time", "memory", "code_size"],
                dtype={"cpu_time": float, "memory": float, "code_size": float},
            )
        except Exception:
            continue

        total = len(df)
        if total == 0:
            continue

        accepted = df[df["status"] == "Accepted"]
        n_acc = len(accepted)

        rows.append({
            "problem_id":       problem_id,
            "num_submissions":  total,
            "acceptance_rate":  n_acc / total,
            "avg_cpu_time":     accepted["cpu_time"].mean() if n_acc > 0 else np.nan,
            "avg_memory":       accepted["memory"].mean()   if n_acc > 0 else np.nan,
            "avg_code_size":    accepted["code_size"].mean() if n_acc > 0 else np.nan,
        })

    print(f"  Done in {time.time() - t0:.1f}s  ({len(rows)} problems)")
    result = pd.DataFrame(rows)
    result.to_csv(STATS_CACHE_PATH, index=False)
    print(f"  Stats cached → {STATS_CACHE_PATH}")
    return result


# ============================================================
# Build description features for a list of problem IDs
# ============================================================

_DESC_REQUIRED_COLS = {
    "has_string_keywords", "has_math_keywords", "has_greedy_keywords",
    "has_stack_keywords", "has_complexity_keywords",
    "num_large_numbers", "num_code_tokens",
}


def build_description_features(codenet_path: str, problem_ids: list[str]) -> pd.DataFrame:
    """
    Extract HTML description features for the given list of problem IDs.

    Results are cached to DESC_CACHE_PATH so parsing only runs once.
    Cache is invalidated automatically if its schema is out of date.
    """
    if os.path.exists(DESC_CACHE_PATH):
        cached = pd.read_csv(DESC_CACHE_PATH, nrows=0)  # headers only
        if not _DESC_REQUIRED_COLS.issubset(set(cached.columns)):
            print("  Description cache is stale (missing new columns) — regenerating ...")
            os.remove(DESC_CACHE_PATH)
        else:
            print(f"Loading description features from cache: {DESC_CACHE_PATH}")
            cached = pd.read_csv(DESC_CACHE_PATH)
            # Fill any missing problems not in cache (e.g. cache is partial)
        missing = [pid for pid in problem_ids if pid not in cached["problem_id"].values]
        if missing:
            print(f"  {len(missing)} problems not in cache, parsing them now ...")
            extra = _parse_descriptions(codenet_path, missing)
            cached = pd.concat([cached, extra], ignore_index=True)
            cached.to_csv(DESC_CACHE_PATH, index=False)
        return cached

    result = _parse_descriptions(codenet_path, problem_ids)
    result.to_csv(DESC_CACHE_PATH, index=False)
    print(f"  Description features cached → {DESC_CACHE_PATH}")
    return result


def _parse_descriptions(codenet_path: str, problem_ids: list[str]) -> pd.DataFrame:
    """Internal: parse HTML files and return a DataFrame of description features."""
    desc_dir = os.path.join(codenet_path, "problem_descriptions")
    rows = []

    print(f"Parsing {len(problem_ids)} HTML problem descriptions ...")
    for i, pid in enumerate(problem_ids):
        if i % 500 == 0 and i > 0:
            print(f"  {i}/{len(problem_ids)}")

        html_path = os.path.join(desc_dir, f"{pid}.html")
        if not os.path.exists(html_path):
            rows.append({
                "problem_id": pid,
                "desc_char_len": 0, "desc_word_count": 0,
                "num_sample_inputs": 0, "has_constraints": 0,
                "has_recursion_keywords": 0, "has_dp_keywords": 0,
                "has_graph_keywords": 0, "has_sort_keywords": 0,
                "has_search_keywords": 0, "description_text": "",
            })
            continue

        with open(html_path, encoding="utf-8", errors="ignore") as f:
            html = f.read()

        feats = extract_description_features(html)
        feats["problem_id"] = pid
        rows.append(feats)

    print(f"  Done.")
    return pd.DataFrame(rows)



# ============================================================
# Label derivation from acceptance_rate
# ============================================================

def derive_labels(df: pd.DataFrame) -> pd.Series:
    """
    Bin problems into easy / medium / hard by acceptance_rate percentiles.
    Top 33% acceptance = easy, middle = medium, bottom = hard.
    """
    low, high = df["acceptance_rate"].quantile([1 / 3, 2 / 3]).values

    def _label(rate: float) -> str:
        if rate >= high:
            return "easy"
        if rate >= low:
            return "medium"
        return "hard"

    return df["acceptance_rate"].apply(_label)


# ============================================================
# Main training pipeline
# ============================================================

NUMERIC_FEATURES = [
    "avg_cpu_time", "avg_memory", "avg_code_size",
    "time_limit", "memory_limit",
    "desc_char_len", "desc_word_count", "num_sample_inputs",
    "has_constraints", "has_recursion_keywords", "has_dp_keywords",
    "has_graph_keywords", "has_sort_keywords", "has_search_keywords",
    "has_string_keywords", "has_math_keywords", "has_greedy_keywords",
    "has_stack_keywords", "has_complexity_keywords",
    "num_large_numbers", "num_code_tokens",
    # Interaction features
    "desc_words_x_large_nums",  # long problem + big constraints = harder
    "cpu_time_x_code_size",     # slow + verbose = harder
]
TEXT_FEATURE = "description_text"


def _add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived interaction columns in-place."""
    df = df.copy()
    df["desc_words_x_large_nums"] = df["desc_word_count"] * df["num_large_numbers"]
    df["cpu_time_x_code_size"]    = df["avg_cpu_time"].fillna(0) * df["avg_code_size"].fillna(0)
    return df


def _squeeze_array(x):
    """Squeeze 2-D single-column array to 1-D for TfidfVectorizer."""
    return x.squeeze() if hasattr(x, "squeeze") else x


def _to_dense(x):
    """Convert a sparse matrix to a dense numpy array (required by some estimators)."""
    return x.toarray() if hasattr(x, "toarray") else x


# Estimator types that require dense (non-sparse) input
_NEEDS_DENSE = (HistGradientBoostingClassifier, GradientBoostingClassifier)


def _build_preprocessor() -> ColumnTransformer:
    """Build the ColumnTransformer: numeric impute+scale, dual TF-IDF (word + char)."""
    from sklearn.preprocessing import FunctionTransformer
    from sklearn.pipeline import FeatureUnion

    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])

    # Word n-gram TF-IDF (semantics)
    word_tfidf = TfidfVectorizer(
        max_features=1000, stop_words="english",
        ngram_range=(1, 2), sublinear_tf=True, min_df=2,
    )
    # Char n-gram TF-IDF (catches code tokens, variable names, operators)
    char_tfidf = TfidfVectorizer(
        max_features=500, analyzer="char_wb",
        ngram_range=(3, 5), sublinear_tf=True, min_df=2,
    )
    text_pipe = Pipeline([
        ("squeeze", FunctionTransformer(_squeeze_array)),
        ("tfidf",   FeatureUnion([
            ("word", word_tfidf),
            ("char", char_tfidf),
        ])),
    ])
    return ColumnTransformer([
        ("num",  numeric_pipe, NUMERIC_FEATURES),
        ("text", text_pipe,    [TEXT_FEATURE]),   # list -> 2D DataFrame column
    ])


def _define_models() -> dict:
    """Return {name: (estimator, param_grid)} for all models to compare."""
    models = {
        "Random Forest": (
            RandomForestClassifier(random_state=42),
            {
                "classifier__n_estimators": [100, 200],
                "classifier__max_depth":    [10, 20, None],
            },
        ),
        # HistGradientBoosting: faster, handles NaNs natively, better on large data
        "HistGradientBoosting": (
            HistGradientBoostingClassifier(random_state=42),
            {
                "classifier__max_iter":      [100, 200],
                "classifier__learning_rate": [0.05, 0.1],
                "classifier__max_depth":     [3, 5, None],
            },
        ),
        "Gradient Boosting": (
            GradientBoostingClassifier(random_state=42),
            {
                "classifier__n_estimators":   [100, 200],
                "classifier__learning_rate":  [0.05, 0.1],
                "classifier__max_depth":      [3, 5],
            },
        ),
        "Linear SVM": (
            SVC(kernel="linear", random_state=42, probability=True),
            {"classifier__C": [0.01, 0.1, 1, 10]},
        ),
        "Logistic Regression": (
            LogisticRegression(max_iter=1000, random_state=42),
            {"classifier__C": [0.01, 0.1, 1, 10]},
        ),
        "kNN": (
            KNeighborsClassifier(),
            {"classifier__n_neighbors": [3, 5, 7, 11]},
        ),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = (
            XGBClassifier(
                random_state=42, eval_metric="mlogloss", verbosity=0,
            ),
            {
                "classifier__n_estimators":  [100, 200],
                "classifier__learning_rate": [0.05, 0.1],
                "classifier__max_depth":     [3, 6],
            },
        )

    return models


def main() -> None:
    sns.set_style("whitegrid")
    plt.rcParams["figure.figsize"] = (10, 6)
    pd.set_option("display.max_columns", 20)

    OUT_DIR = os.path.dirname(__file__)

    # ------------------------------------------------------------------ #
    # STEP 1 — Load and merge data                                        #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STEP 1: Loading CodeNet data")
    print("=" * 60)

    problem_list = pd.read_csv(
        os.path.join(CODENET_PATH, "metadata", "problem_list.csv")
    ).rename(columns={"id": "problem_id"})

    stats_df = build_problem_stats(CODENET_PATH)

    # Keep only problems with enough submissions for a reliable acceptance rate
    stats_df = stats_df[stats_df["num_submissions"] >= 10].reset_index(drop=True)
    print(f"\nProblems with >=10 submissions: {len(stats_df)}")

    desc_df = build_description_features(CODENET_PATH, stats_df["problem_id"].tolist())

    # Merge everything
    df = stats_df.merge(
        problem_list[["problem_id", "time_limit", "memory_limit"]],
        on="problem_id", how="left"
    ).merge(desc_df, on="problem_id", how="left")

    print(f"\nFinal dataset shape: {df.shape}")

    # ------------------------------------------------------------------ #
    # STEP 2 — Derive difficulty labels                                   #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STEP 2: Deriving difficulty labels from acceptance_rate")
    print("=" * 60)

    df["difficulty"] = derive_labels(df)
    print("\nClass distribution:")
    print(df["difficulty"].value_counts().sort_index().to_string())

    plt.figure(figsize=(6, 4))
    (
        df["difficulty"]
        .value_counts()
        .reindex(["easy", "medium", "hard"])
        .plot(kind="bar", color=["#2ecc71", "#f39c12", "#e74c3c"])
    )
    plt.title("Difficulty Class Balance")
    plt.xlabel("Difficulty")
    plt.ylabel("Count")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "difficulty_distribution.png"))
    plt.show()
    print("Saved: difficulty_distribution.png")

    # ------------------------------------------------------------------ #
    # STEP 3 — Feature engineering + Train / Val / Test split (60/20/20) #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STEP 3: Feature engineering + Train / Validation / Test split (60 / 20 / 20)")
    print("=" * 60)

    # Add interaction features before any split so all sets get them
    df = _add_interaction_features(df)

    X = df[NUMERIC_FEATURES + [TEXT_FEATURE]].copy()
    X[TEXT_FEATURE] = X[TEXT_FEATURE].fillna("")
    y_str = df["difficulty"]

    # Encode string labels -> integers (required by XGBoost; harmless for others)
    le = LabelEncoder()
    y = pd.Series(le.fit_transform(y_str), index=y_str.index, name="difficulty")
    CLASS_NAMES = list(le.classes_)  # e.g. ['easy', 'hard', 'medium']
    print(f"  Label encoding: {dict(zip(le.classes_, le.transform(le.classes_)))}")

    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.25, random_state=42, stratify=y_train_val
    )

    print(f"  Train : {len(X_train)}")
    print(f"  Val   : {len(X_val)}")
    print(f"  Test  : {len(X_test)}")

    # ------------------------------------------------------------------ #
    # SMOTE — oversample minority classes on training set only            #
    # ------------------------------------------------------------------ #
    if HAS_SMOTE:
        print("\n  Applying SMOTE to training set ...")
        pre_smote = _build_preprocessor()
        X_train_t = pre_smote.fit_transform(X_train, y_train)
        counts = pd.Series(y_train).value_counts()
        k = min(5, int(counts.min()) - 1)
        if k >= 1:
            sm = SMOTE(random_state=42, k_neighbors=k)
            X_resampled, y_resampled = sm.fit_resample(X_train_t, y_train)
            _smote_pre = pre_smote    # already fitted preprocessor
            _smote_X   = X_resampled  # resampled transformed features
            _smote_y   = y_resampled  # resampled labels
            print(f"  SMOTE: training set expanded to {len(y_resampled)} samples")
        else:
            print("  SMOTE skipped — smallest class too small for k_neighbors")
            _smote_pre = _smote_X = _smote_y = None
    else:
        _smote_pre = _smote_X = _smote_y = None
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STEP 4: Training and tuning models")
    print("=" * 60)

    preprocessor = _build_preprocessor()
    models = _define_models()

    val_scores: dict[str, float] = {}
    best_pipelines: dict[str, Pipeline] = {}

    for name, (estimator, param_grid) in models.items():
        print(f"\n--- {name} ---")

        # HistGradientBoosting and GradientBoosting require dense input;
        # insert a densify step between the (sparse) preprocessor and classifier.
        from sklearn.preprocessing import FunctionTransformer
        pipe_steps = [("preprocessor", preprocessor)]
        if isinstance(estimator, _NEEDS_DENSE):
            pipe_steps.append(("densify", FunctionTransformer(_to_dense)))
        pipe_steps.append(("classifier", estimator))

        pipe = Pipeline(pipe_steps)

        # Quick default fit to check for over/underfitting
        pipe.fit(X_train, y_train)
        train_acc = pipe.score(X_train, y_train)
        val_acc_default = pipe.score(X_val, y_val)
        print(f"  Default  →  train: {train_acc:.4f}  |  val: {val_acc_default:.4f}")

        # GridSearchCV with 5-fold CV — f1_macro balances precision/recall across all 3 classes
        grid = GridSearchCV(
            pipe, param_grid, cv=5, n_jobs=-1, scoring="f1_macro", verbose=0
        )
        grid.fit(X_train, y_train)

        tuned_val_acc = grid.score(X_val, y_val)
        print(f"  Best params : {grid.best_params_}")
        print(f"  Best CV f1  : {grid.best_score_:.4f}  |  Tuned val acc: {tuned_val_acc:.4f}")

        val_scores[name] = tuned_val_acc
        best_pipelines[name] = grid.best_estimator_

    # ------------------------------------------------------------------ #
    # STEP 5 — Validation score summary                                   #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STEP 5: Validation Scores Summary")
    print("=" * 60)

    print("\nValidation scores (ranked):")
    for name, acc in sorted(val_scores.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name:25s}: {acc:.4f}")

    best_name = max(val_scores, key=val_scores.get)
    print(f"\nBest model: {best_name}  ({val_scores[best_name]:.4f})")

    # Bar chart of validation results
    sorted_names = sorted(val_scores, key=val_scores.get, reverse=True)
    sorted_accs  = [val_scores[n] for n in sorted_names]

    plt.figure(figsize=(9, 5))
    palette = sns.color_palette("Blues_r", len(sorted_names))
    bars = plt.bar(sorted_names, sorted_accs, color=palette)
    plt.ylim(0, 1.05)
    plt.ylabel("Validation Accuracy")
    plt.title("Model Comparison — Validation Accuracy")
    plt.xticks(rotation=15, ha="right")
    for bar, acc in zip(bars, sorted_accs):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{acc:.3f}",
            ha="center", fontsize=10,
        )
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "model_comparison.png"))
    plt.show()
    print("Saved: model_comparison.png")

    # ------------------------------------------------------------------ #
    # STEP 6 — Final evaluation on the held-out test set                  #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STEP 6: Final Evaluation on Test Set")
    print("=" * 60)

    # Retrain winner on train + val combined
    X_trainval = pd.concat([X_train, X_val])
    y_trainval  = pd.concat([y_train, y_val])

    final_model = best_pipelines[best_name]
    final_model.fit(X_trainval, y_trainval)

    y_pred   = final_model.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred)

    # Decode numeric labels back to strings for human-readable output
    y_test_str = le.inverse_transform(y_test)
    y_pred_str = le.inverse_transform(y_pred)
    ordered    = ["easy", "medium", "hard"]

    print(f"\nTest accuracy ({best_name}): {test_acc:.4f}\n")
    print(classification_report(y_test_str, y_pred_str, labels=ordered))

    ConfusionMatrixDisplay(
        confusion_matrix(y_test_str, y_pred_str, labels=ordered),
        display_labels=ordered,
    ).plot(cmap="Blues")
    plt.title(f"Final Model ({best_name}) — Test Set")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "confusion_matrix.png"))
    plt.show()
    print("Saved: confusion_matrix.png")

    # Feature importance for tree-based winners
    if any(kw in best_name for kw in ("Forest", "Boosting")):
        _print_feature_importance(final_model, X_val, y_val)

    # ------------------------------------------------------------------ #
    # Save model                                                          #
    # ------------------------------------------------------------------ #
    joblib.dump({"pipeline": final_model, "label_encoder": le}, MODEL_SAVE_PATH)
    print(f"\nModel saved → {MODEL_SAVE_PATH}")


def _print_feature_importance(pipeline: Pipeline, X_val: pd.DataFrame, y_val: pd.Series, top_n: int = 20) -> None:
    """
    Print feature importances using permutation importance (more reliable than
    tree built-in importances, especially for high-cardinality TF-IDF columns).
    """
    print(f"\nTop {top_n} Features (permutation importance on validation set):")
    try:
        result = permutation_importance(
            pipeline, X_val, y_val,
            n_repeats=10, random_state=42, n_jobs=-1,
            scoring="f1_macro",
        )
        preprocessor = pipeline.named_steps["preprocessor"]
        text_step    = preprocessor.named_transformers_["text"].named_steps["tfidf"]
        tfidf_names: list[str] = []
        if hasattr(text_step, "transformer_list"):
            for _, sub in text_step.transformer_list:
                tfidf_names += sub.get_feature_names_out().tolist()
        else:
            tfidf_names = text_step.get_feature_names_out().tolist()
        feature_names = NUMERIC_FEATURES + tfidf_names

        top_idx = np.argsort(result.importances_mean)[::-1][:top_n]
        for rank, idx in enumerate(top_idx, 1):
            if idx < len(feature_names):
                print(
                    f"  {rank:2d}. {feature_names[idx]:40s}"
                    f"  mean={result.importances_mean[idx]:.4f}"
                    f"  std={result.importances_std[idx]:.4f}"
                )
    except Exception as exc:
        print(f"  (Could not compute permutation importance: {exc})")


# ============================================================
# Inference helper — import and call from backend
# ============================================================

def predict_difficulty(
    avg_cpu_time: float,
    avg_memory: float,
    avg_code_size: float,
    time_limit: float,
    memory_limit: float,
    description_text: str = "",
    model_path: str = MODEL_SAVE_PATH,
) -> str:
    """
    Predict the difficulty of a coding problem.

    Parameters
    ----------
    avg_cpu_time    : float   average CPU time of accepted submissions (ms)
    avg_memory      : float   average memory of accepted submissions (KB)
    avg_code_size   : float   average code size of accepted submissions (bytes)
    time_limit      : float   problem time limit (ms)
    memory_limit    : float   problem memory limit (KB)
    description_text: str     plain-text problem statement (optional)

    Returns
    -------
    "easy" | "medium" | "hard"
    """
    model_bundle = joblib.load(model_path)
    model = model_bundle["pipeline"]
    le    = model_bundle["label_encoder"]
    desc_feats = extract_description_features(f"<p>{description_text}</p>")

    row = pd.DataFrame([{
        "avg_cpu_time":             avg_cpu_time,
        "avg_memory":               avg_memory,
        "avg_code_size":            avg_code_size,
        "time_limit":               time_limit,
        "memory_limit":             memory_limit,
        "desc_char_len":            desc_feats["desc_char_len"],
        "desc_word_count":          desc_feats["desc_word_count"],
        "num_sample_inputs":        desc_feats["num_sample_inputs"],
        "has_constraints":          desc_feats["has_constraints"],
        "has_recursion_keywords":   desc_feats["has_recursion_keywords"],
        "has_dp_keywords":          desc_feats["has_dp_keywords"],
        "has_graph_keywords":       desc_feats["has_graph_keywords"],
        "has_sort_keywords":        desc_feats["has_sort_keywords"],
        "has_search_keywords":      desc_feats["has_search_keywords"],
        "has_string_keywords":      desc_feats["has_string_keywords"],
        "has_math_keywords":        desc_feats["has_math_keywords"],
        "has_greedy_keywords":      desc_feats["has_greedy_keywords"],
        "has_stack_keywords":       desc_feats["has_stack_keywords"],
        "has_complexity_keywords":  desc_feats["has_complexity_keywords"],
        "num_large_numbers":        desc_feats["num_large_numbers"],
        "num_code_tokens":          desc_feats["num_code_tokens"],
        # Interaction features
        "desc_words_x_large_nums":  desc_feats["desc_word_count"] * desc_feats["num_large_numbers"],
        "cpu_time_x_code_size":     (avg_cpu_time or 0) * (avg_code_size or 0),
        "description_text":         desc_feats["description_text"],
    }])

    return str(le.inverse_transform(model.predict(row))[0])


if __name__ == "__main__":
    main()
