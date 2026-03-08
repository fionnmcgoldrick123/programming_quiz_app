"""
Topic Classifier — Full Training Script
=========================================
Trains and compares seven sklearn pipelines to predict the primary algorithmic
topic of a LeetCode-style programming question from its title + description.

Script sections
---------------
  1. Data loading and cleaning
  2. Exploratory data analysis       (4 figures — shown + saved)
  3. Model definitions               (7 classifiers with GridSearchCV param grids)
  4. Training with cross-validation  (default vs tuned, 5-fold GridSearchCV)
        → Figure 05: Validation F1-Macro comparison bar chart
        → Figure 06: Default vs tuned validation accuracy (grouped bars)
        → Figure 07: CV fold score distributions (box plot)
        → Figure 08: Training time per model
  5. Final evaluation on test set
        → Figure 09: Grouped metrics (Accuracy / F1-Macro / F1-Weighted)
        → Figure 10: Per-class F1 heatmap (all models × classes)
        → Figure 11: Confusion matrix for best model (row-normalised)
        → Figure 12: Top discriminative features for best linear model
  6. Save the best model             → topic_model.pkl

Split: 60 % train / 20 % validation / 20 % test  (stratified, like difficulty_predictor)
All figures are shown interactively AND written to ml_models/topic_classifier/figures/

Run from the project root:
    python ml_models/topic_classifier/train.py
"""

import os
import re
import time
import joblib

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB, ComplementNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

_HERE           = os.path.dirname(os.path.abspath(__file__))
CSV_PATH        = os.path.join(_HERE, "..", "leetcode.csv")
MODEL_SAVE_PATH = os.path.join(_HERE, "topic_model.pkl")
FIGURES_DIR     = os.path.join(_HERE, "figures")

# Classes with fewer than this many samples are dropped before training.
# With only 2-3 examples a classifier cannot generalise and evaluation
# metrics (precision/recall) are not statistically meaningful.
MIN_SAMPLES  = 20
RANDOM_STATE = 42

# Split: 60 / 20 / 20  (train / val / test) — stratified on class label.
# Two-stage split: first carve off 20 % test, then split the remaining
# 80 % into 75 % train (= 60 % overall) and 25 % val (= 20 % overall).
TEST_SIZE = 0.20
VAL_SIZE  = 0.25   # 25 % of the 80 % train+val pool → 20 % overall

os.makedirs(FIGURES_DIR, exist_ok=True)

# Apply whitegrid theme and sensible defaults to all figures
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (11, 6)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Data loading and cleaning
# ─────────────────────────────────────────────────────────────────────────────

def parse_tags(raw: str) -> list:
    """
    Convert the malformed topic_tags string from the CSV into a Python list.

    Raw format (as stored in the CSV):  "'Array', 'Hash Table'"
    re.findall captures every substring enclosed in single quotes.
    Result:                             ['Array', 'Hash Table']
    """
    return re.findall(r"'([^']+)'", str(raw))


def load_and_clean(csv_path: str):
    """
    Load the LeetCode CSV and return:
      df_clean  — final cleaned DataFrame ready for training, with columns:
                    'text'        : title + ". " + problem_description
                    'primary_tag' : first parsed tag (the model target label)
                    'word_count'  : token count of 'text' (used in EDA)
      df_raw    — intermediate snapshot after null-drop but before class filter,
                  used in EDA to show the full tag-distribution long tail.

    Cleaning steps applied in order
    --------------------------------
    1. Drop rows where problem_description OR topic_tags is null.
       Both columns have the same 840 null rows (premium-only questions that
       LeetCode does not expose without a subscription).
    2. Parse the malformed topic_tags string into a Python list.
    3. Extract the first tag as the single primary label.
       Using one label per question keeps this a standard multi-class problem
       rather than a multi-label one, which is simpler and more appropriate
       for the number of training samples available.
    4. Combine title + description into one 'text' field.
       Prepending the title gives TF-IDF a compact, keyword-dense summary
       (e.g. "Binary Tree Inorder Traversal") before the longer description.
    5. Drop classes that have fewer than MIN_SAMPLES examples.
       Prevents the model learning from 2-3 instances, which would produce
       uninformative evaluation metrics.
    """
    print("=" * 65)
    print("SECTION 1 — DATA LOADING & CLEANING")
    print("=" * 65)

    df = pd.read_csv(csv_path)
    print(f"  Raw rows loaded              : {len(df)}")
    print(f"  Columns                      : {df.columns.tolist()}")
    print(f"  Null counts (key columns):")
    for col in ["title", "problem_description", "topic_tags"]:
        print(f"    {col:<28}: {df[col].isnull().sum()}")

    # Step 1 — drop nulls
    df = df.dropna(subset=["problem_description", "topic_tags"]).copy()
    print(f"\n  Rows after null drop         : {len(df)}  (dropped {3000 - len(df)})")

    # Step 2+3 — parse tags, assign primary label
    df["tags_list"]   = df["topic_tags"].apply(parse_tags)
    df["primary_tag"] = df["tags_list"].apply(lambda t: t[0] if t else None)
    df = df.dropna(subset=["primary_tag"])
    print(f"  Rows after tag parsing       : {len(df)}")

    # Step 4 — build combined text feature and compute word count for EDA
    df["text"]       = df["title"].fillna("") + ". " + df["problem_description"].fillna("")
    df["word_count"] = df["text"].str.split().str.len()

    # Snapshot before class filter (needed in EDA)
    df_raw = df.copy()

    # Step 5 — drop rare classes
    counts        = df["primary_tag"].value_counts()
    valid_classes = counts[counts >= MIN_SAMPLES].index
    dropped       = sorted(set(df_raw["primary_tag"]) - set(valid_classes))
    df            = df[df["primary_tag"].isin(valid_classes)].reset_index(drop=True)

    print(f"  Classes dropped (< {MIN_SAMPLES} samples): {dropped}")
    print(f"  Classes kept                 : {len(valid_classes)}")
    print(f"  Rows for training/testing    : {len(df)}")
    print(f"\n  Final class distribution:")
    for cls, n in df["primary_tag"].value_counts().items():
        bar = "█" * (n // 30)
        print(f"    {cls:<30} {n:>4}  {bar}")

    return df[["text", "primary_tag", "word_count"]], df_raw


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Exploratory Data Analysis
# ─────────────────────────────────────────────────────────────────────────────

def fig01_class_distribution(df_clean: pd.DataFrame, df_raw: pd.DataFrame) -> None:
    """
    Figure 01 — Class Distribution (before vs after MIN_SAMPLES filter).

    Left panel  : full tag distribution across all 2160 parsed questions,
                  showing the long tail of rare classes.
    Right panel : only the classes kept for training, colour-coded by frequency.
    Comparing the two panels justifies why rare classes were dropped.
    """
    fig, axes = plt.subplots(1, 2, figsize=(20, 9))

    # Left: raw distribution (all classes)
    counts_raw = df_raw["primary_tag"].value_counts()
    axes[0].barh(counts_raw.index[::-1], counts_raw.values[::-1], color="steelblue")
    axes[0].set_title("All Primary Tags — before class filter", fontsize=12)
    axes[0].set_xlabel("Number of questions")
    for i, v in enumerate(counts_raw.values[::-1]):
        axes[0].text(v + 1, i, str(v), va="center", fontsize=7)

    # Right: kept classes with viridis gradient
    counts_clean = df_clean["primary_tag"].value_counts()
    palette      = sns.color_palette("viridis", len(counts_clean))
    axes[1].barh(
        counts_clean.index[::-1], counts_clean.values[::-1],
        color=palette[::-1],
    )
    axes[1].set_title(f"Kept Classes — ≥ {MIN_SAMPLES} samples", fontsize=12)
    axes[1].set_xlabel("Number of questions")
    for i, v in enumerate(counts_clean.values[::-1]):
        axes[1].text(v + 1, i, str(v), va="center", fontsize=9)

    fig.suptitle("LeetCode — Primary Topic Tag Distribution", fontsize=15, fontweight="bold")
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "01_class_distribution.png"))


def fig02_text_length_by_class(df_clean: pd.DataFrame) -> None:
    """
    Figure 02 — Combined Text Word Count per Topic Class (box plot).

    Shows how description length varies across categories.
    Longer descriptions (e.g. Dynamic Programming) tend to require
    more context to explain the problem, which is itself a signal the
    TF-IDF model can exploit.
    """
    order = (
        df_clean.groupby("primary_tag")["word_count"]
        .median()
        .sort_values(ascending=False)
        .index
    )
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.boxplot(
        data=df_clean,
        x="primary_tag", y="word_count",
        order=order,
        hue="primary_tag", palette="tab10",
        legend=False, ax=ax,
    )
    ax.set_title("Word Count Distribution per Topic Class  (title + description)", fontsize=13)
    ax.set_xlabel("Primary Topic Tag")
    ax.set_ylabel("Word Count")
    ax.tick_params(axis="x", rotation=38)
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "02_text_length_by_class.png"))


def fig03_top_words_overall(df_clean: pd.DataFrame) -> None:
    """
    Figure 03 — Top 30 Words Across All Questions (after stop-word removal).

    Uses CountVectorizer to obtain raw term frequencies for the whole corpus.
    Reveals which programming terms the vocabulary is built around and confirms
    the text corpus is domain-specific (e.g. 'array', 'string', 'integer').
    """
    cv       = CountVectorizer(max_features=5000, stop_words="english")
    X        = cv.fit_transform(df_clean["text"])
    freqs    = np.asarray(X.sum(axis=0)).flatten()
    vocab    = cv.get_feature_names_out()
    top_idx  = freqs.argsort()[-30:][::-1]

    fig, ax = plt.subplots(figsize=(14, 7))
    palette = sns.color_palette("Blues_r", 30)
    ax.barh(vocab[top_idx][::-1], freqs[top_idx][::-1], color=palette)
    ax.set_title("Top 30 Words Across All Questions  (English stop words removed)", fontsize=13)
    ax.set_xlabel("Total Occurrences in Corpus")
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "03_top_words_overall.png"))


def fig04_top_words_per_class(df_clean: pd.DataFrame) -> None:
    """
    Figure 04 — Top 10 Words per Topic Class (grid of subplots).

    For each class a separate CountVectorizer is fitted on only that class's
    questions, so the word frequencies reflect that class exclusively rather
    than being diluted by the whole corpus.

    Verifies the vocabulary is semantically discriminative:
      - 'Tree' class highlights 'node', 'root', 'left', 'right'
      - 'Dynamic Programming' highlights 'dp', 'subsequence', 'minimum'
      - 'Math' highlights 'integer', 'prime', 'sum'
    This supports the hypothesis that TF-IDF can separate the classes.
    """
    classes  = sorted(df_clean["primary_tag"].unique())
    n_cols   = 3
    n_rows   = -(-len(classes) // n_cols)   # ceiling division
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, n_rows * 3.8))
    axes_flat = axes.flatten()

    tab_colors = sns.color_palette("tab10", 10)
    cv = CountVectorizer(max_features=3000, stop_words="english")

    for i, cls in enumerate(classes):
        texts     = df_clean.loc[df_clean["primary_tag"] == cls, "text"].tolist()
        X         = cv.fit_transform(texts)
        freqs     = np.asarray(X.sum(axis=0)).flatten()
        vocab     = cv.get_feature_names_out()
        top_idx   = freqs.argsort()[-10:][::-1]
        top_w     = vocab[top_idx]
        top_c     = freqs[top_idx]

        color = tab_colors[i % 10]
        axes_flat[i].barh(top_w[::-1], top_c[::-1], color=color)
        axes_flat[i].set_title(f"{cls}  (n={len(texts)})", fontsize=10, fontweight="bold")
        axes_flat[i].tick_params(axis="y", labelsize=8)
        axes_flat[i].set_xlabel("Count", fontsize=8)

    # Hide any unused subplot cells
    for j in range(len(classes), len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle("Top 10 Words per Topic Class  (stop words removed)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "04_top_words_per_class.png"))


def run_eda(df_clean: pd.DataFrame, df_raw: pd.DataFrame) -> None:
    print("\n" + "=" * 65)
    print("SECTION 2 — EXPLORATORY DATA ANALYSIS")
    print("=" * 65)
    fig01_class_distribution(df_clean, df_raw)
    fig02_text_length_by_class(df_clean)
    fig03_top_words_overall(df_clean)
    fig04_top_words_per_class(df_clean)
    print("  EDA complete.\n")


def _save_and_show(path: str) -> None:
    """Save the current figure to disk, then display it interactively."""
    plt.savefig(path, dpi=150)
    plt.show()
    print(f"    Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Model definitions with GridSearchCV param grids
# ─────────────────────────────────────────────────────────────────────────────

def _shared_tfidf() -> TfidfVectorizer:
    """
    Shared TF-IDF configuration used as the first step in every pipeline.
    All models receive identical vectorised input so results are directly
    comparable — the only variable is the classifier.

    Settings:
      max_features=15000  — Cap vocabulary; limits memory on sparse matrices.
      ngram_range=(1, 2)  — Include bigrams so 'binary search', 'linked list',
                            and 'dynamic programming' are treated as atomic tokens.
      sublinear_tf=True   — Apply 1 + log(tf) instead of raw tf.
      stop_words='english'— Remove uninformative function words.
    """
    return TfidfVectorizer(
        max_features=15000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        stop_words="english",
    )


def get_model_definitions() -> dict:
    """
    Returns {name: (unfitted Pipeline, param_grid_for_GridSearchCV)}.

    Param-grid keys must be prefixed with 'clf__' because the classifier sits
    at the 'clf' step of the Pipeline.

    Models span five hypothesis classes so the report covers the full landscape:
      Linear:       Logistic Regression, Linear SVC, SGD (hinge)
      Probabilistic:Multinomial NB, Complement NB
      Ensemble:     Random Forest
      Lazy:         k-Nearest Neighbours
    """
    return {
        "Logistic Regression": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", LogisticRegression(
                    class_weight="balanced", max_iter=1000, random_state=RANDOM_STATE,
                )),
            ]),
            # Tune regularisation strength C (higher = less regularisation)
            {"clf__C": [0.1, 1.0, 10.0]},
        ),
        "Linear SVC": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", LinearSVC(
                    class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE,
                )),
            ]),
            {"clf__C": [0.1, 1.0, 10.0]},
        ),
        "SGD Classifier": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", SGDClassifier(
                    loss="hinge", class_weight="balanced",
                    max_iter=200, random_state=RANDOM_STATE, n_jobs=-1,
                )),
            ]),
            # Tune regularisation alpha (inverse of C for SVM)
            {"clf__alpha": [1e-4, 1e-3, 1e-2]},
        ),
        "Multinomial NB": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", MultinomialNB()),
            ]),
            # alpha is the Laplace smoothing parameter
            {"clf__alpha": [0.01, 0.1, 1.0]},
        ),
        "Complement NB": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", ComplementNB()),
            ]),
            {"clf__alpha": [0.01, 0.1, 1.0]},
        ),
        "Random Forest": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", RandomForestClassifier(
                    class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1,
                )),
            ]),
            {
                "clf__n_estimators": [100, 200],
                "clf__max_depth":    [20, None],
            },
        ),
        "k-Nearest Neighbours": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", KNeighborsClassifier(
                    metric="cosine", algorithm="brute", n_jobs=-1,
                )),
            ]),
            {"clf__n_neighbors": [5, 7, 11]},
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Training with 5-fold GridSearchCV
# ─────────────────────────────────────────────────────────────────────────────

def train_and_evaluate(
    models: dict,
    X_train, X_val, X_test,
    y_train, y_val, y_test,
):
    """
    For every model:
      1. Fit with default parameters, print train and validation accuracy —
         shows whether the default is over/underfitting before tuning.
      2. Run 5-fold GridSearchCV on the training set, scoring by f1_macro.
         f1_macro weights every class equally, which matters here because
         'Array' makes up 55 % of the data.
      3. Evaluate the best estimator on the validation set.
      4. Record per-fold CV scores (from cv_results_) so we can plot the
         score distribution for each model.

    Returns
    -------
    results_df     — pd.DataFrame: one row per model with all metrics
    per_class      — {model: {class: val_f1}} for the heatmap
    best_pipelines — {model: fitted Pipeline from GridSearchCV best estimator}
    cv_fold_scores — {model: np.array of 5 fold scores at best params}
    """
    print("=" * 65)
    print("SECTION 3 — MODEL TRAINING WITH 5-FOLD GRIDSEARCHCV")
    print("=" * 65)

    rows           = []
    per_class      = {}
    best_pipelines = {}
    cv_fold_scores = {}

    for name, (pipeline, param_grid) in models.items():
        print(f"\n  +- {name} {'-' * max(1, 50 - len(name))}+")

        # ── Step A: Default fit (no tuning) ──────────────────────────────────
        t0 = time.time()
        pipeline.fit(X_train, y_train)
        default_train_acc = accuracy_score(y_train, pipeline.predict(X_train))
        default_val_acc   = accuracy_score(y_val,   pipeline.predict(X_val))
        print(f"  |  Default fit  ->  train acc: {default_train_acc:.4f}  |  val acc: {default_val_acc:.4f}")

        # ── Step B: GridSearchCV (5-fold, scored on f1_macro) ─────────────────
        # Fits len(param_grid combinations) × 5 models — may take a minute
        # for Random Forest but is fast for all linear models.
        grid = GridSearchCV(
            pipeline,
            param_grid,
            cv=5,
            scoring="f1_macro",
            n_jobs=-1,
            verbose=0,
            return_train_score=True,   # enables comparison of train and val CV scores
        )
        grid.fit(X_train, y_train)
        train_time = time.time() - t0

        print(f"  |  Best params  : {grid.best_params_}")
        print(f"  |  Best CV F1   : {grid.best_score_:.4f}  (5-fold mean on training set)")

        # ── Step C: Evaluate best estimator on the held-out validation set ────
        best = grid.best_estimator_
        y_val_pred = best.predict(X_val)
        val_acc    = accuracy_score(y_val, y_val_pred)
        val_f1_mac = f1_score(y_val, y_val_pred, average="macro",    zero_division=0)
        val_f1_wt  = f1_score(y_val, y_val_pred, average="weighted", zero_division=0)
        print(f"  |  Tuned val    ->  acc: {val_acc:.4f}  |  f1_macro: {val_f1_mac:.4f}  |  f1_weighted: {val_f1_wt:.4f}")
        print(f"  |  Total time   : {train_time:.1f}s")
        print(f"  +{'-' * 55}+")

        # ── Step D: Extract per-fold CV scores at the best parameter index ────
        # cv_results_ stores a score per fold per param combination.
        # best_index_ gives the row of the best combination; we read all
        # split0..split4 columns at that row to get individual fold scores.
        best_idx   = grid.best_index_
        fold_scores = np.array([
            grid.cv_results_[f"split{k}_test_score"][best_idx]
            for k in range(5)
        ])
        cv_fold_scores[name] = fold_scores

        # Per-class F1 on the validation set (used in the heatmap)
        report    = classification_report(y_val, y_val_pred, output_dict=True, zero_division=0)
        per_class[name] = {
            cls: report[cls]["f1-score"]
            for cls in report
            if cls not in ("accuracy", "macro avg", "weighted avg")
        }

        best_pipelines[name] = best

        rows.append({
            "Model":              name,
            "Default Val Acc":    round(default_val_acc,  4),
            "Tuned Val Acc":      round(val_acc,           4),
            "Best CV F1 Macro":   round(grid.best_score_,  4),
            "Val F1 Macro":       round(val_f1_mac,        4),
            "Val F1 Weighted":    round(val_f1_wt,         4),
            "Train Time (s)":     round(train_time,        2),
        })

    results_df = (
        pd.DataFrame(rows)
        .sort_values("Val F1 Macro", ascending=False)
        .reset_index(drop=True)
    )

    print("\n\n" + "=" * 65)
    print("  MODEL COMPARISON — VALIDATION METRICS  (sorted by F1 Macro)")
    print("=" * 65)
    print(results_df.to_string(index=False))

    return results_df, per_class, best_pipelines, cv_fold_scores


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Comparison figures (shown interactively + saved)
# ─────────────────────────────────────────────────────────────────────────────

def fig05_model_comparison_f1(results_df: pd.DataFrame) -> None:
    """
    Figure 05 — Validation F1-Macro comparison bar chart (like model_comparison.png
    in difficulty_predictor).

    Sorted ascending so the best model appears at the top of the horizontal bars.
    The dashed vertical line marks the best score for reference.
    Score labels are printed beside each bar.
    """
    df_s    = results_df.sort_values("Val F1 Macro")
    palette = sns.color_palette("Blues", len(df_s))

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(df_s["Model"], df_s["Val F1 Macro"], color=palette)
    ax.axvline(df_s["Val F1 Macro"].max(), color="gray", linestyle="--",
               linewidth=0.9, alpha=0.7, label="Best score")
    ax.set_xlim(0, 1.12)
    ax.set_title("Model Comparison — Validation F1-Macro", fontsize=14, fontweight="bold")
    ax.set_xlabel("F1-Macro (validation set)")
    for bar, v in zip(bars, df_s["Val F1 Macro"]):
        ax.text(v + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{v:.4f}", va="center", fontsize=10)
    ax.legend()
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "05_model_comparison_f1.png"))


def fig06_default_vs_tuned(results_df: pd.DataFrame) -> None:
    """
    Figure 06 — Default parameter validation accuracy vs tuned (GridSearchCV best).

    Grouped horizontal bars per model.  The gap between the two bars shows
    how much hyperparameter tuning actually helped each classifier.
    """
    df_s     = results_df.sort_values("Tuned Val Acc")
    models   = df_s["Model"].tolist()
    default  = df_s["Default Val Acc"].tolist()
    tuned    = df_s["Tuned Val Acc"].tolist()
    y_pos    = np.arange(len(models))
    height   = 0.35

    fig, ax = plt.subplots(figsize=(13, 6))
    b1 = ax.barh(y_pos - height / 2, default, height, label="Default params", color="#3498db", alpha=0.8)
    b2 = ax.barh(y_pos + height / 2, tuned,   height, label="Tuned (GridSearchCV)", color="#2ecc71", alpha=0.9)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(models)
    ax.set_xlim(0, 1.12)
    ax.set_xlabel("Validation Accuracy")
    ax.set_title("Default Parameters vs GridSearchCV Tuning — Validation Accuracy",
                 fontsize=13, fontweight="bold")
    ax.legend()
    for bar, v in zip(b1, default):
        ax.text(v + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{v:.3f}", va="center", fontsize=8, color="#1a5276")
    for bar, v in zip(b2, tuned):
        ax.text(v + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{v:.3f}", va="center", fontsize=8, color="#145a32")
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "06_default_vs_tuned.png"))


def fig07_cv_score_distributions(cv_fold_scores: dict) -> None:
    """
    Figure 07 — Cross-Validation F1-Macro Score Distributions (box plot).

    Each box represents the distribution of 5 fold scores at the best parameter
    combination found by GridSearchCV.  A tighter box indicates more stable
    performance across folds; a lower median indicates a weaker model.

    This is the most reliable single graph for comparing models because it shows
    variance as well as central tendency.
    """
    # Sort models by median fold score ascending → best at right in vertical boxplot
    order       = sorted(cv_fold_scores, key=lambda k: np.median(cv_fold_scores[k]))
    data        = [cv_fold_scores[k] for k in order]
    palette     = sns.color_palette("RdYlGn", len(order))

    fig, ax = plt.subplots(figsize=(13, 6))
    bp = ax.boxplot(
        data,
        labels=order,
        patch_artist=True,
        medianprops={"color": "black", "linewidth": 2},
        widths=0.5,
    )
    for patch, col in zip(bp["boxes"], palette):
        patch.set_facecolor(col)
        patch.set_alpha(0.85)

    # Overlay individual fold points so every data point is visible
    for i, scores in enumerate(data, 1):
        ax.scatter(
            np.full(len(scores), i), scores,
            color="black", s=25, zorder=5, alpha=0.7,
        )

    # Annotate each box with its mean ± std
    for i, scores in enumerate(data, 1):
        ax.text(i, min(scores) - 0.015, f"{np.mean(scores):.3f}±{np.std(scores):.3f}",
                ha="center", fontsize=8, color="#555")

    ax.set_title("Cross-Validation F1-Macro Score Distributions  (5-fold, best params)",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("F1-Macro per CV fold")
    ax.set_xlabel("Model")
    ax.tick_params(axis="x", rotation=15)
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "07_cv_score_distributions.png"))


def fig08_training_time(results_df: pd.DataFrame) -> None:
    """
    Figure 08 — Total wall-clock training time per model (including GridSearchCV).

    Colour-coded: green < 15 s, amber 15–60 s, red > 60 s.
    Important context for the report's speed-vs-accuracy trade-off discussion.
    """
    df_s = results_df.sort_values("Train Time (s)")

    def _col(t):
        if t < 15:  return "#27ae60"
        if t < 60:  return "#f39c12"
        return "#e74c3c"

    colors = [_col(t) for t in df_s["Train Time (s)"]]
    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.barh(df_s["Model"], df_s["Train Time (s)"], color=colors)
    ax.set_title("Total Training Time Including GridSearchCV", fontsize=13, fontweight="bold")
    ax.set_xlabel("Seconds")
    for bar, t in zip(bars, df_s["Train Time (s)"]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{t:.1f}s", va="center", fontsize=9)
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "08_training_time.png"))


def run_training_plots(
    results_df: pd.DataFrame,
    cv_fold_scores: dict,
) -> None:
    print("\n" + "=" * 65)
    print("SECTION 4 — TRAINING COMPARISON FIGURES")
    print("=" * 65)
    fig05_model_comparison_f1(results_df)
    fig06_default_vs_tuned(results_df)
    fig07_cv_score_distributions(cv_fold_scores)
    fig08_training_time(results_df)
    print("  Training figures complete.\n")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Final evaluation on the held-out test set
# ─────────────────────────────────────────────────────────────────────────────

def fig09_grouped_metrics(results_df: pd.DataFrame, test_row: dict) -> None:
    """
    Figure 09 — Grouped bar chart: Tuned Val Acc / Val F1-Macro / Val F1-Weighted
    for every model, plus the best model's final test-set scores highlighted.

    Three metric bars side by side per model make it easy to see at a glance
    whether high accuracy is coming at the cost of F1 on minority classes.
    """
    df_s     = results_df.sort_values("Val F1 Macro")
    models   = df_s["Model"].tolist()
    n        = len(models)
    x        = np.arange(n)
    w        = 0.25

    fig, ax = plt.subplots(figsize=(15, 6))
    b1 = ax.bar(x - w,   df_s["Tuned Val Acc"],    w, label="Val Accuracy",    color="#3498db")
    b2 = ax.bar(x,       df_s["Val F1 Macro"],     w, label="Val F1-Macro",    color="#2ecc71")
    b3 = ax.bar(x + w,   df_s["Val F1 Weighted"],  w, label="Val F1-Weighted", color="#9b59b6")

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=18, ha="right", fontsize=9)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Score")
    ax.set_title("All Models — Validation Accuracy, F1-Macro & F1-Weighted",
                 fontsize=13, fontweight="bold")
    ax.legend()

    # Annotate each bar group
    for bars in (b1, b2, b3):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.01,
                    f"{h:.3f}", ha="center", fontsize=7)

    # Shade the best model's column
    best_model = results_df.iloc[0]["Model"]
    if best_model in models:
        best_idx = models.index(best_model)
        ax.axvspan(best_idx - 0.45, best_idx + 0.45, alpha=0.07,
                   color="gold", zorder=0, label=f"★ {best_model}")
        ax.legend()

    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "09_grouped_metrics.png"))


def fig10_per_class_f1_heatmap(per_class: dict, all_classes: list) -> None:
    """
    Figure 10 — Per-Class F1 Heatmap (models × classes, evaluated on val set).

    Each cell is the F1 score for one (model, class) pair.
    Column patterns reveal which topics are inherently hard to classify
    (e.g. 'Two Pointers' overlaps heavily with 'Array').
    Row patterns reveal which models generalise best to minority classes.
    """
    order       = list(per_class.keys())
    data        = [[per_class[m].get(cls, 0.0) for cls in all_classes] for m in order]
    hmap        = pd.DataFrame(data, index=order, columns=all_classes)

    fig, ax = plt.subplots(figsize=(17, max(5, len(order) + 2)))
    sns.heatmap(
        hmap, annot=True, fmt=".2f", cmap="YlGnBu",
        linewidths=0.5, ax=ax, vmin=0, vmax=1,
        cbar_kws={"label": "F1 Score"},
    )
    ax.set_title("Per-Class F1 Score — All Models  (validation set)", fontsize=14)
    ax.set_xlabel("Topic Class")
    ax.set_ylabel("Model")
    ax.tick_params(axis="x", rotation=40, labelsize=9)
    ax.tick_params(axis="y", rotation=0,  labelsize=9)
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "10_per_class_f1_heatmap.png"))


def fig11_confusion_matrix(name: str, pipeline, X_test, y_test) -> None:
    """
    Figure 11 — Normalised confusion matrix for the best model on the test set.

    Row-normalised: each cell = fraction of samples from that true class that
    were predicted as the column class.  Removes class-size bias so errors
    on small classes (e.g. 'Two Pointers' with 7 test samples) are as visible
    as errors on 'Array' (234 test samples).
    """
    y_pred = pipeline.predict(X_test)
    labels = sorted(set(y_test))
    cm     = confusion_matrix(y_test, y_pred, labels=labels, normalize="true")

    fig, ax = plt.subplots(figsize=(13, 11))
    sns.heatmap(
        cm, annot=True, fmt=".2f", cmap="Blues",
        xticklabels=labels, yticklabels=labels,
        linewidths=0.4, ax=ax, vmin=0, vmax=1,
        cbar_kws={"label": "Fraction of True Class"},
    )
    ax.set_title(f"Confusion Matrix — {name}  (test set, row-normalised)", fontsize=13)
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.tick_params(axis="y", rotation=0,  labelsize=9)
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "11_confusion_matrix_best.png"))


def fig12_top_features(name: str, pipeline) -> None:
    """
    Figure 12 — Top discriminative bigrams/unigrams per class for linear models.

    For Logistic Regression and Linear SVC, the classifier has a weight matrix
    of shape (n_classes, n_features).  The highest-weight tokens for each class
    are the n-grams the model learned are most informative for that class.

    This is useful in the dissertation for interpreting model behaviour:
    'Array' class highlighting 'nums', 'index' confirms the model learned
    semantically meaningful features, not random correlations.
    """
    clf_step = pipeline.named_steps.get("clf")
    if not hasattr(clf_step, "coef_"):
        print(f"  [fig12] Skipped — {name} has no coef_ attribute.")
        return

    tfidf_step  = pipeline.named_steps["tfidf"]
    feature_names = np.array(tfidf_step.get_feature_names_out())
    coef          = clf_step.coef_   # shape: (n_classes, n_features)

    # For binary outputs LinearSVC returns shape (1, n_features); expand to 2D
    if coef.ndim == 1:
        coef = coef.reshape(1, -1)

    # Use the classes seen during training (attribute varies by estimator type)
    if hasattr(clf_step, "classes_"):
        classes = clf_step.classes_
    else:
        # LinearSVC stores classes as clf_step.classes_  via sklearn ≥ 1.0
        classes = [f"class_{i}" for i in range(coef.shape[0])]

    top_n    = 12
    n_cols   = 3
    n_rows   = -(-len(classes) // n_cols)
    tab_cols = sns.color_palette("tab10", 10)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, n_rows * 3.6))
    axes_flat = axes.flatten()

    for i, (cls, weights) in enumerate(zip(classes, coef)):
        top_idx = weights.argsort()[-top_n:][::-1]
        top_w   = feature_names[top_idx]
        top_v   = weights[top_idx]

        axes_flat[i].barh(top_w[::-1], top_v[::-1], color=tab_cols[i % 10])
        axes_flat[i].set_title(f"{cls}", fontsize=10, fontweight="bold")
        axes_flat[i].tick_params(axis="y", labelsize=8)
        axes_flat[i].set_xlabel("Classifier weight", fontsize=8)

    for j in range(len(classes), len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle(f"Top {top_n} Features per Class — {name}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    _save_and_show(os.path.join(FIGURES_DIR, "12_top_features_per_class.png"))


def run_final_evaluation(
    best_name: str,
    best_pipelines: dict,
    per_class: dict,
    all_classes: list,
    results_df: pd.DataFrame,
    X_train, X_val, X_test,
    y_train, y_val, y_test,
) -> None:
    """
    Retrain the best model on train + val combined (60 + 20 = 80 % of data),
    then evaluate once on the held-out test set.

    Retraining on the combined set is important: the model was selected using
    validation performance, so to make full use of all labelled data before the
    final deployment we include validation samples in the last fit.
    """
    print("\n" + "=" * 65)
    print("SECTION 5 — FINAL EVALUATION ON TEST SET")
    print("=" * 65)

    best_pipeline = best_pipelines[best_name]

    # Retrain winner on train + val combined
    X_tv = np.concatenate([X_train, X_val])
    y_tv = np.concatenate([y_train, y_val])
    print(f"\n  Retraining {best_name} on train + val ({len(X_tv)} samples) ...")
    best_pipeline.fit(X_tv, y_tv)

    y_pred    = best_pipeline.predict(X_test)
    test_acc  = accuracy_score(y_test, y_pred)
    test_f1m  = f1_score(y_test, y_pred, average="macro",    zero_division=0)
    test_f1w  = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    print(f"\n  Test accuracy   : {test_acc:.4f}")
    print(f"  Test F1 Macro   : {test_f1m:.4f}")
    print(f"  Test F1 Weighted: {test_f1w:.4f}")
    print(f"\n  Full Classification Report — {best_name}:")
    print(classification_report(y_test, y_pred, zero_division=0))

    test_row = {"acc": test_acc, "f1_mac": test_f1m, "f1_wt": test_f1w}

    # Update per_class with test-set per-class F1 for the best model
    report      = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    per_class[best_name + " (test)"] = {
        cls: report[cls]["f1-score"]
        for cls in report
        if cls not in ("accuracy", "macro avg", "weighted avg")
    }

    # Figures
    print("\n" + "=" * 65)
    print("SECTION 6 — FINAL EVALUATION FIGURES")
    print("=" * 65)
    fig09_grouped_metrics(results_df, test_row)
    fig10_per_class_f1_heatmap(per_class, all_classes)
    fig11_confusion_matrix(best_name, best_pipeline, X_test, y_test)
    fig12_top_features(best_name, best_pipeline)
    print("  Evaluation figures complete.\n")

    return best_pipeline


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Save best model
# ─────────────────────────────────────────────────────────────────────────────

def save_model(pipeline, classes: list, path: str) -> None:
    """
    Serialise the best trained sklearn Pipeline and the ordered list of class
    labels to disk using joblib.

    The class list is bundled with the pipeline so predict.py can map predictions
    back to human-readable tag strings without loading any external data.
    """
    joblib.dump({"pipeline": pipeline, "classes": classes}, path)
    print(f"  Saved best model to: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # 1 — Load and clean
    df_clean, df_raw = load_and_clean(CSV_PATH)

    # 2 — EDA
    run_eda(df_clean, df_raw)

    # 3 — Three-way stratified split: 60 / 20 / 20
    # stratify=y is critical because 'Array' is 55 % of data; without it
    # one split might be predominantly Array and another largely minority classes.
    X = df_clean["text"].values
    y = df_clean["primary_tag"].values

    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=VAL_SIZE, random_state=RANDOM_STATE, stratify=y_trainval,
    )
    print(f"\n  Split summary (stratified):")
    print(f"    Train : {len(X_train):>4}  ({len(X_train)/len(X)*100:.0f} %)")
    print(f"    Val   : {len(X_val):>4}  ({len(X_val)/len(X)*100:.0f} %)")
    print(f"    Test  : {len(X_test):>4}  ({len(X_test)/len(X)*100:.0f} %)")
    print(f"    Total : {len(X)}")

    # 4 — Train all seven models with GridSearchCV
    models = get_model_definitions()
    results_df, per_class, best_pipelines, cv_fold_scores = train_and_evaluate(
        models, X_train, X_val, X_test, y_train, y_val, y_test,
    )

    # 5 — Training comparison figures (shown as training finishes)
    run_training_plots(results_df, cv_fold_scores)

    # 6 — Final evaluation on test set + evaluation figures
    all_classes  = sorted(set(y))
    best_name    = results_df.iloc[0]["Model"]
    final_model  = run_final_evaluation(
        best_name, best_pipelines, per_class, all_classes,
        results_df, X_train, X_val, X_test, y_train, y_val, y_test,
    )

    # 7 — Save
    print("=" * 65)
    print("SECTION 7 — SAVING BEST MODEL")
    print("=" * 65)
    save_model(final_model, all_classes, MODEL_SAVE_PATH)

    print(f"\n  WINNER: {best_name}  (Val F1-Macro = {results_df.iloc[0]['Val F1 Macro']})")
    print(f"\nAll done.  Figures → {FIGURES_DIR}")


if __name__ == "__main__":
    main()
