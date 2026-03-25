"""
Multi-Label Topic Classifier — Training Script
================================================
Trains a multi-label classifier to predict ALL relevant algorithmic
topic tags for a coding question from its title + description.

Key changes from the previous single-label model:
  - Multi-label: predicts ALL tags per question, not just the first one
  - MultiLabelBinarizer for multi-hot encoding
  - OneVsRestClassifier for per-label binary classification
  - Per-label threshold optimisation on validation set
  - class_weight='balanced' handles uneven tag frequencies

Split: 60 % train / 20 % validation / 20 % test
Figures saved to  ml_models/tag_classifier/figures/
Model saved to    ml_models/tag_classifier/topic_model.pkl

Run from the project root:
    python ml_models/tag_classifier/train.py
"""

import os
import re
import time
import warnings
import joblib
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")           # non-interactive backend for terminal runs
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.multiclass import OneVsRestClassifier
from sklearn.naive_bayes import ComplementNB
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import (
    f1_score,
    hamming_loss,
    classification_report,
)

warnings.filterwarnings("ignore", category=UserWarning)

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

_HERE           = os.path.dirname(os.path.abspath(__file__))
CSV_PATH        = os.path.join(_HERE, "leetcode.csv")
if not os.path.exists(CSV_PATH):
    CSV_PATH    = os.path.join(_HERE, "..", "leetcode.csv")

MODEL_SAVE_PATH = os.path.join(_HERE, "topic_model.pkl")
FIGURES_DIR     = os.path.join(_HERE, "figures")

# Tags occurring in fewer than this many questions are dropped.
MIN_TAG_SAMPLES = 25
RANDOM_STATE    = 42
TEST_SIZE       = 0.20
VAL_SIZE        = 0.25      # 25 % of the remaining 80 % = 20 % overall

os.makedirs(FIGURES_DIR, exist_ok=True)
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Data Loading & Cleaning  (Multi-Label)
# ═════════════════════════════════════════════════════════════════════════════

def parse_tags(raw: str) -> list:
    """Parse CSV tag string  "'Array', 'Hash Table'"  ->  ['Array', 'Hash Table']"""
    return re.findall(r"'([^']+)'", str(raw))


def load_and_clean(csv_path: str):
    """
    Load the LeetCode CSV and prepare multi-label targets.

    Steps:
      1. Drop rows without descriptions or tags.
      2. Parse ALL tags per question (not just the first one).
      3. Remove tags that appear in fewer than MIN_TAG_SAMPLES questions.
      4. Drop questions left with zero valid tags.
      5. Combine title + description into a single text feature.

    Returns (df, tag_counts) where df has columns ['text', 'tags'].
    """
    print("=" * 65)
    print("SECTION 1 — DATA LOADING & CLEANING  (MULTI-LABEL)")
    print("=" * 65)

    df = pd.read_csv(csv_path)
    print(f"  Raw rows loaded           : {len(df)}")

    # 1 — Drop nulls
    df = df.dropna(subset=["problem_description", "topic_tags"]).copy()
    print(f"  After null drop           : {len(df)}")

    # 2 — Parse ALL tags per question
    df["tags"] = df["topic_tags"].apply(parse_tags)
    df = df[df["tags"].apply(len) > 0].reset_index(drop=True)
    print(f"  After tag parsing         : {len(df)}")

    # 3 — Count tag frequencies across all questions
    tag_counts_raw = Counter()
    for tags in df["tags"]:
        tag_counts_raw.update(tags)

    valid_tags = sorted(t for t, c in tag_counts_raw.items() if c >= MIN_TAG_SAMPLES)
    dropped    = sorted(t for t, c in tag_counts_raw.items() if c < MIN_TAG_SAMPLES)
    print(f"\n  Total unique tags         : {len(tag_counts_raw)}")
    print(f"  Tags kept (>= {MIN_TAG_SAMPLES} samples) : {len(valid_tags)}")
    print(f"  Tags dropped              : {len(dropped)}")

    # 4 — Filter tags and drop empty rows
    valid_set = set(valid_tags)
    df["tags"] = df["tags"].apply(lambda t: sorted(set(x for x in t if x in valid_set)))
    df = df[df["tags"].apply(len) > 0].reset_index(drop=True)

    # 5 — Build combined text feature
    df["text"] = df["title"].fillna("") + ". " + df["problem_description"].fillna("")

    # Final statistics
    tag_counts = Counter()
    for tags in df["tags"]:
        tag_counts.update(tags)

    print(f"  Rows for training         : {len(df)}")
    print(f"  Avg tags per question     : {df['tags'].apply(len).mean():.2f}")
    print(f"\n  Multi-label tag distribution:")
    for tag, count in tag_counts.most_common():
        bar = "█" * (count // 30)
        print(f"    {tag:<30} {count:>4}  {bar}")

    return df[["text", "tags"]], tag_counts


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Exploratory Data Analysis
# ═════════════════════════════════════════════════════════════════════════════

def run_eda(df, tag_counts):
    """Generate three EDA figures for multi-label analysis."""
    print("\n" + "=" * 65)
    print("SECTION 2 — EXPLORATORY DATA ANALYSIS")
    print("=" * 65)

    # ── Figure 01: Tag frequency ─────────────────────────────────────────────
    tags_sorted = tag_counts.most_common()
    fig, ax = plt.subplots(figsize=(14, max(8, len(tags_sorted) * 0.35)))
    names  = [t[0] for t in tags_sorted]
    values = [t[1] for t in tags_sorted]
    colors = sns.color_palette("viridis", len(names))
    ax.barh(names[::-1], values[::-1], color=colors)
    ax.set_title("Multi-Label Tag Frequency Distribution", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of questions containing this tag")
    for i, v in enumerate(values[::-1]):
        ax.text(v + 3, i, str(v), va="center", fontsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "01_tag_frequency.png"), dpi=150)
    plt.close()
    print("  Saved: 01_tag_frequency.png")

    # ── Figure 02: Tags per question histogram ───────────────────────────────
    tags_per_q = df["tags"].apply(len)
    fig, ax = plt.subplots(figsize=(10, 6))
    bins = range(1, tags_per_q.max() + 2)
    ax.hist(tags_per_q, bins=bins, color="steelblue", edgecolor="black", align="left")
    ax.set_title("Number of Tags per Question", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of Tags")
    ax.set_ylabel("Question Count")
    ax.set_xticks(range(1, tags_per_q.max() + 1))
    mean_t = tags_per_q.mean()
    ax.axvline(mean_t, color="red", linestyle="--", label=f"Mean = {mean_t:.1f}")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "02_tags_per_question.png"), dpi=150)
    plt.close()
    print("  Saved: 02_tags_per_question.png")

    # ── Figure 03: Tag co-occurrence matrix ──────────────────────────────────
    mlb_eda = MultiLabelBinarizer()
    Y_eda = mlb_eda.fit_transform(df["tags"])
    cooc = Y_eda.T @ Y_eda
    np.fill_diagonal(cooc, 0)
    co_df = pd.DataFrame(cooc, index=mlb_eda.classes_, columns=mlb_eda.classes_)

    fig, ax = plt.subplots(figsize=(18, 16))
    sns.heatmap(co_df, annot=True, fmt="d", cmap="YlOrRd", ax=ax,
                linewidths=0.3, annot_kws={"fontsize": 6})
    ax.set_title("Tag Co-occurrence Matrix", fontsize=14, fontweight="bold")
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.tick_params(axis="y", rotation=0, labelsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "03_tag_cooccurrence.png"), dpi=150)
    plt.close()
    print("  Saved: 03_tag_cooccurrence.png")
    print("  EDA complete.\n")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Model Definitions
# ═════════════════════════════════════════════════════════════════════════════

def _shared_tfidf():
    """
    Shared TF-IDF configuration.

    - max_features=20000 : generous vocabulary for multi-label discrimination
    - ngram_range=(1,2)  : captures 'binary search', 'dynamic programming' etc.
    - sublinear_tf=True  : dampens high-frequency terms
    - min_df=2           : removes hapax legomena (typos, unique identifiers)
    """
    return TfidfVectorizer(
        max_features=20000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        stop_words="english",
        min_df=2,
    )


def get_model_definitions():
    """
    Returns {name: (Pipeline, param_grid)} for multi-label classifiers.

    All use OneVsRestClassifier which trains one binary classifier per label.
    class_weight='balanced' compensates for label imbalance (Array=1168 vs
    Game Theory=21) by weighting minority-class samples more heavily.
    """
    return {
        "OVR Logistic Regression": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", OneVsRestClassifier(
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=RANDOM_STATE,
                        solver="liblinear",
                    )
                )),
            ]),
            {"clf__estimator__C": [0.5, 1.0, 5.0, 10.0]},
        ),
        "OVR SGD (log_loss)": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", OneVsRestClassifier(
                    SGDClassifier(
                        loss="log_loss",        # supports predict_proba
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=RANDOM_STATE,
                    )
                )),
            ]),
            {"clf__estimator__alpha": [1e-5, 1e-4, 1e-3]},
        ),
        "OVR Complement NB": (
            Pipeline([
                ("tfidf", _shared_tfidf()),
                ("clf", OneVsRestClassifier(ComplementNB())),
            ]),
            {"clf__estimator__alpha": [0.01, 0.1, 0.5, 1.0]},
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Training with GridSearchCV
# ═════════════════════════════════════════════════════════════════════════════

def train_and_evaluate(models, X_train, X_val, Y_train, Y_val, mlb):
    """
    Train each model with GridSearchCV (3-fold, scored on f1_micro)
    and evaluate on the held-out validation set.
    """
    print("=" * 65)
    print("SECTION 3 — MODEL TRAINING WITH GRIDSEARCHCV")
    print("=" * 65)

    rows           = []
    best_pipelines = {}

    for name, (pipeline, param_grid) in models.items():
        print(f"\n  +-- {name} {'-' * max(1, 48 - len(name))}+")

        t0 = time.time()

        # A — Default fit (no tuning) for baseline comparison
        pipeline.fit(X_train, Y_train)
        Y_val_default = pipeline.predict(X_val)
        def_f1_micro   = f1_score(Y_val, Y_val_default, average="micro",   zero_division=0)
        def_f1_samples = f1_score(Y_val, Y_val_default, average="samples", zero_division=0)
        print(f"  |  Default:  F1-micro={def_f1_micro:.4f}  F1-samples={def_f1_samples:.4f}")

        # B — GridSearchCV  (3-fold, scored on f1_micro)
        grid = GridSearchCV(
            pipeline,
            param_grid,
            cv=3,
            scoring="f1_micro",
            n_jobs=-1,
            verbose=0,
        )
        grid.fit(X_train, Y_train)
        train_time = time.time() - t0

        best = grid.best_estimator_
        Y_val_pred = best.predict(X_val)

        # C — Validation metrics
        val_f1_micro    = f1_score(Y_val, Y_val_pred, average="micro",    zero_division=0)
        val_f1_macro    = f1_score(Y_val, Y_val_pred, average="macro",    zero_division=0)
        val_f1_samples  = f1_score(Y_val, Y_val_pred, average="samples",  zero_division=0)
        val_f1_weighted = f1_score(Y_val, Y_val_pred, average="weighted", zero_division=0)
        val_hamming     = 1.0 - hamming_loss(Y_val, Y_val_pred)
        val_subset      = float(np.mean(np.all(Y_val == Y_val_pred, axis=1)))

        print(f"  |  Best params : {grid.best_params_}")
        print(f"  |  Best CV F1  : {grid.best_score_:.4f}")
        print(f"  |  Val F1-micro   : {val_f1_micro:.4f}")
        print(f"  |  Val F1-macro   : {val_f1_macro:.4f}")
        print(f"  |  Val F1-samples : {val_f1_samples:.4f}")
        print(f"  |  Val F1-weighted: {val_f1_weighted:.4f}")
        print(f"  |  Val Hamming acc: {val_hamming:.4f}")
        print(f"  |  Val Subset acc : {val_subset:.4f}")
        print(f"  |  Time           : {train_time:.1f}s")
        print(f"  +{'-' * 52}+")

        best_pipelines[name] = best
        rows.append({
            "Model":           name,
            "Default F1-micro": round(def_f1_micro, 4),
            "Val F1-micro":    round(val_f1_micro, 4),
            "Val F1-macro":    round(val_f1_macro, 4),
            "Val F1-samples":  round(val_f1_samples, 4),
            "Val F1-weighted": round(val_f1_weighted, 4),
            "Val Hamming Acc":  round(val_hamming, 4),
            "Val Subset Acc":   round(val_subset, 4),
            "Train Time (s)":  round(train_time, 2),
        })

    results_df = (
        pd.DataFrame(rows)
        .sort_values("Val F1-micro", ascending=False)
        .reset_index(drop=True)
    )

    print("\n" + "=" * 65)
    print("  MODEL COMPARISON  (sorted by F1-micro)")
    print("=" * 65)
    print(results_df.to_string(index=False))

    return results_df, best_pipelines


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Per-Label Threshold Optimisation
# ═════════════════════════════════════════════════════════════════════════════

def optimize_thresholds(pipeline, X_val, Y_val, mlb):
    """
    Find the per-label probability threshold that maximises F1 for each label.

    This is the single most important step for handling class imbalance in
    multi-label classification:
      - Frequent labels (Array, String) keep thresholds near 0.5
      - Rare labels (Game Theory, Trie) get lower thresholds so the model
        is more willing to predict them when there is reasonable evidence

    Falls back to 0.5 for all labels if the pipeline does not support
    predict_proba (should not happen with our model choices).
    """
    print("\n" + "=" * 65)
    print("SECTION 4 — PER-LABEL THRESHOLD OPTIMISATION")
    print("=" * 65)

    if not hasattr(pipeline, "predict_proba"):
        print("  Pipeline does not support predict_proba — using default 0.5.")
        return {c: 0.5 for c in mlb.classes_}

    proba = pipeline.predict_proba(X_val)
    thresholds = {}

    for i, label in enumerate(mlb.classes_):
        best_thresh = 0.5
        best_f1     = 0.0
        for t in np.arange(0.10, 0.85, 0.025):
            preds = (proba[:, i] >= t).astype(int)
            f1 = f1_score(Y_val[:, i], preds, zero_division=0)
            if f1 > best_f1:
                best_f1     = f1
                best_thresh = t
        thresholds[label] = round(float(best_thresh), 3)
        print(f"    {label:<30}  threshold={best_thresh:.3f}  F1={best_f1:.4f}")

    # ── Evaluate with optimised thresholds ────────────────────────────────────
    thresh_array = np.array([thresholds[c] for c in mlb.classes_])
    Y_opt = (proba >= thresh_array).astype(int)

    # Guarantee at least one label per sample (pick the most confident)
    for i in range(len(Y_opt)):
        if Y_opt[i].sum() == 0:
            Y_opt[i, proba[i].argmax()] = 1

    f1_mi = f1_score(Y_val, Y_opt, average="micro",   zero_division=0)
    f1_sa = f1_score(Y_val, Y_opt, average="samples",  zero_division=0)
    f1_ma = f1_score(Y_val, Y_opt, average="macro",    zero_division=0)
    h_acc = 1.0 - hamming_loss(Y_val, Y_opt)

    print(f"\n  After threshold optimisation (validation set):")
    print(f"    F1-micro   : {f1_mi:.4f}")
    print(f"    F1-macro   : {f1_ma:.4f}")
    print(f"    F1-samples : {f1_sa:.4f}")
    print(f"    Hamming acc: {h_acc:.4f}")

    return thresholds


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Final Evaluation on Test Set
# ═════════════════════════════════════════════════════════════════════════════

def _print_multilabel_metrics(Y_true, Y_pred):
    """Print a comprehensive set of multi-label quality metrics."""
    f1_mi  = f1_score(Y_true, Y_pred, average="micro",    zero_division=0)
    f1_ma  = f1_score(Y_true, Y_pred, average="macro",    zero_division=0)
    f1_sa  = f1_score(Y_true, Y_pred, average="samples",  zero_division=0)
    f1_wt  = f1_score(Y_true, Y_pred, average="weighted", zero_division=0)
    h_acc  = 1.0 - hamming_loss(Y_true, Y_pred)
    subset = float(np.mean(np.all(Y_true == Y_pred, axis=1)))

    # "At least one correct tag" — practical relevance metric
    at_least_one = float(np.mean([
        len(set(np.where(Y_true[i])[0]) & set(np.where(Y_pred[i])[0])) > 0
        for i in range(len(Y_true))
    ]))

    print(f"    F1-micro            : {f1_mi:.4f}")
    print(f"    F1-macro            : {f1_ma:.4f}")
    print(f"    F1-samples          : {f1_sa:.4f}")
    print(f"    F1-weighted         : {f1_wt:.4f}")
    print(f"    Hamming accuracy    : {h_acc:.4f}")
    print(f"    Subset accuracy     : {subset:.4f}")
    print(f"    >=1 correct tag     : {at_least_one:.4f}")

    return {
        "f1_micro": f1_mi, "f1_macro": f1_ma, "f1_samples": f1_sa,
        "f1_weighted": f1_wt, "hamming_acc": h_acc,
        "subset_acc": subset, "at_least_one": at_least_one,
    }


def final_evaluation(pipeline, thresholds, X_train, X_val, Y_train, Y_val,
                      X_test, Y_test, mlb):
    """
    Retrain the winning model on train + val (80 % of data), then evaluate
    once on the held-out test set with both default and optimised thresholds.
    """
    print("\n" + "=" * 65)
    print("SECTION 5 — FINAL EVALUATION ON TEST SET")
    print("=" * 65)

    # Retrain on train + val combined for maximum data usage
    X_tv = np.concatenate([X_train, X_val])
    Y_tv = np.vstack([Y_train, Y_val])
    print(f"\n  Retraining on train + val ({len(X_tv)} samples) ...")
    pipeline.fit(X_tv, Y_tv)

    # ── Default threshold prediction ──────────────────────────────────────────
    Y_pred_default = pipeline.predict(X_test)
    print(f"\n  DEFAULT thresholds (0.5):")
    _print_multilabel_metrics(Y_test, Y_pred_default)

    # ── Optimised threshold prediction ────────────────────────────────────────
    if hasattr(pipeline, "predict_proba"):
        proba = pipeline.predict_proba(X_test)
        thresh_array = np.array([thresholds[c] for c in mlb.classes_])
        Y_pred_opt = (proba >= thresh_array).astype(int)
        for i in range(len(Y_pred_opt)):
            if Y_pred_opt[i].sum() == 0:
                Y_pred_opt[i, proba[i].argmax()] = 1
    else:
        Y_pred_opt = Y_pred_default

    print(f"\n  OPTIMISED thresholds:")
    metrics = _print_multilabel_metrics(Y_test, Y_pred_opt)

    # Per-label classification report
    print(f"\n  Per-label classification report (optimised thresholds):")
    print(classification_report(
        Y_test, Y_pred_opt,
        target_names=mlb.classes_,
        zero_division=0,
    ))

    return pipeline, metrics


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Figures
# ═════════════════════════════════════════════════════════════════════════════

def save_figures(results_df, pipeline, X_val, Y_val, mlb, thresholds):
    """Generate and save comparison and analysis figures."""
    print("\n" + "=" * 65)
    print("SECTION 6 — FIGURES")
    print("=" * 65)

    # ── Fig 04: Model comparison bars ─────────────────────────────────────────
    df_s = results_df.sort_values("Val F1-micro")
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = sns.color_palette("Blues", len(df_s))
    bars = ax.barh(df_s["Model"], df_s["Val F1-micro"], color=colors)
    ax.set_title("Model Comparison — Validation F1-micro", fontsize=14, fontweight="bold")
    ax.set_xlabel("F1-micro")
    ax.set_xlim(0, 1.1)
    for bar, v in zip(bars, df_s["Val F1-micro"]):
        ax.text(v + 0.01, bar.get_y() + bar.get_height() / 2, f"{v:.4f}", va="center")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "04_model_comparison.png"), dpi=150)
    plt.close()
    print("  Saved: 04_model_comparison.png")

    # ── Fig 05: Per-label F1 with optimised thresholds ────────────────────────
    if hasattr(pipeline, "predict_proba"):
        proba = pipeline.predict_proba(X_val)
        thresh_array = np.array([thresholds[c] for c in mlb.classes_])
        Y_pred = (proba >= thresh_array).astype(int)
        for i in range(len(Y_pred)):
            if Y_pred[i].sum() == 0:
                Y_pred[i, proba[i].argmax()] = 1
    else:
        Y_pred = pipeline.predict(X_val)

    per_label_f1 = []
    for i, label in enumerate(mlb.classes_):
        f1 = f1_score(Y_val[:, i], Y_pred[:, i], zero_division=0)
        per_label_f1.append((label, f1))
    per_label_f1.sort(key=lambda x: x[1])

    fig, ax = plt.subplots(figsize=(13, max(8, len(per_label_f1) * 0.35)))
    labels_s = [x[0] for x in per_label_f1]
    f1s_s    = [x[1] for x in per_label_f1]
    colors   = sns.color_palette("RdYlGn", len(labels_s))
    ax.barh(labels_s, f1s_s, color=colors)
    ax.set_title("Per-Label F1 Score  (Optimised Thresholds, Validation Set)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("F1 Score")
    ax.set_xlim(0, 1.1)
    ax.axvline(0.80, color="gray", linestyle="--", alpha=0.5, label="0.80 target")
    for i, v in enumerate(f1s_s):
        ax.text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=8)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "05_per_label_f1.png"), dpi=150)
    plt.close()
    print("  Saved: 05_per_label_f1.png")

    # ── Fig 06: Optimised threshold distribution per label ────────────────────
    thresh_items = sorted(thresholds.items(), key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(13, max(8, len(thresh_items) * 0.35)))
    thr_labels = [x[0] for x in thresh_items]
    thr_values = [x[1] for x in thresh_items]
    thr_colors = [
        "#e74c3c" if v < 0.3 else "#f39c12" if v < 0.5 else "#27ae60"
        for v in thr_values
    ]
    ax.barh(thr_labels, thr_values, color=thr_colors)
    ax.set_title("Optimised Prediction Threshold per Label", fontsize=14, fontweight="bold")
    ax.set_xlabel("Threshold")
    ax.axvline(0.5, color="gray", linestyle="--", alpha=0.5, label="Default 0.5")
    for i, v in enumerate(thr_values):
        ax.text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=8)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "06_thresholds.png"), dpi=150)
    plt.close()
    print("  Saved: 06_thresholds.png")

    # ── Fig 07: Multi-metric grouped bar chart ────────────────────────────────
    metrics = ["Val F1-micro", "Val F1-macro", "Val F1-samples", "Val F1-weighted"]
    df_plot  = results_df.sort_values("Val F1-micro")
    n        = len(df_plot)
    x        = np.arange(n)
    w        = 0.18
    pal      = ["#3498db", "#2ecc71", "#9b59b6", "#e67e22"]

    fig, ax = plt.subplots(figsize=(14, 6))
    for j, (metric, col) in enumerate(zip(metrics, pal)):
        bars = ax.bar(x + j * w, df_plot[metric], w, label=metric, color=col)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.008,
                    f"{h:.3f}", ha="center", fontsize=7)
    ax.set_xticks(x + 1.5 * w)
    ax.set_xticklabels(df_plot["Model"], rotation=10, ha="right", fontsize=9)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Score")
    ax.set_title("All Models — Multi-Label Validation Metrics", fontsize=13, fontweight="bold")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "07_multi_metric_comparison.png"), dpi=150)
    plt.close()
    print("  Saved: 07_multi_metric_comparison.png")

    print("  All figures saved.\n")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Save Model
# ═════════════════════════════════════════════════════════════════════════════

def save_model(pipeline, mlb, thresholds, path):
    """
    Serialise the trained pipeline, MultiLabelBinarizer, and optimised
    per-label thresholds to a single .pkl file.
    """
    payload = {
        "pipeline":   pipeline,
        "mlb":        mlb,
        "thresholds": thresholds,
        "classes":    list(mlb.classes_),
        "version":    2,               # v2 = multi-label format
    }
    joblib.dump(payload, path)
    print(f"  Model saved: {path}")


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

def main():
    # 1 — Load and clean
    df, tag_counts = load_and_clean(CSV_PATH)

    # 2 — EDA
    run_eda(df, tag_counts)

    # 3 — Encode multi-label targets
    mlb = MultiLabelBinarizer()
    Y   = mlb.fit_transform(df["tags"])
    X   = df["text"].values
    print(f"\n  Labels ({len(mlb.classes_)}): {list(mlb.classes_)}")
    print(f"  Label matrix shape: {Y.shape}")

    # 4 — Train / val / test split  (60 / 20 / 20)
    X_tv, X_test, Y_tv, Y_test = train_test_split(
        X, Y, test_size=TEST_SIZE, random_state=RANDOM_STATE,
    )
    X_train, X_val, Y_train, Y_val = train_test_split(
        X_tv, Y_tv, test_size=VAL_SIZE, random_state=RANDOM_STATE,
    )
    print(f"  Train: {len(X_train)}   Val: {len(X_val)}   Test: {len(X_test)}")

    # Quick check: label coverage in each split
    for name, Ys in [("Train", Y_train), ("Val", Y_val), ("Test", Y_test)]:
        col_sums = Ys.sum(axis=0)
        empty = int((col_sums == 0).sum())
        if empty > 0:
            print(f"  WARNING: {name} split has {empty} labels with zero examples!")

    # 5 — Train and compare models
    models = get_model_definitions()
    results_df, best_pipelines = train_and_evaluate(
        models, X_train, X_val, Y_train, Y_val, mlb,
    )

    # 6 — Select best model
    best_name     = results_df.iloc[0]["Model"]
    best_pipeline = best_pipelines[best_name]
    print(f"\n  * Best model: {best_name}")

    # 7 — Threshold optimisation
    thresholds = optimize_thresholds(best_pipeline, X_val, Y_val, mlb)

    # 8 — Figures
    save_figures(results_df, best_pipeline, X_val, Y_val, mlb, thresholds)

    # 9 — Final evaluation on test set  (retrain on train + val)
    final_pipeline, metrics = final_evaluation(
        best_pipeline, thresholds,
        X_train, X_val, Y_train, Y_val,
        X_test, Y_test, mlb,
    )

    # 10 — Save
    print("\n" + "=" * 65)
    print("SECTION 7 — SAVING MODEL")
    print("=" * 65)
    save_model(final_pipeline, mlb, thresholds, MODEL_SAVE_PATH)

    print(f"\n  * Winner         : {best_name}")
    print(f"  * Test F1-micro  : {metrics['f1_micro']:.4f}")
    print(f"  * Test F1-samples: {metrics['f1_samples']:.4f}")
    print(f"  * >=1 correct tag: {metrics['at_least_one']:.4f}")
    print(f"\n  Figures -> {FIGURES_DIR}")
    print("  Done!\n")


if __name__ == "__main__":
    main()
