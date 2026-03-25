"""
Multi-Label Topic Classifier — Prediction Module
==================================================
Loads the trained multi-label model and predicts topic tags for
coding questions. Returns multiple tags per question using
per-label optimised thresholds from training.

The trained pipeline expects a single combined string of
    "<title>. <problem_description>"
as input.

Functions:
  predict_topics(text, top_n=5)
      Returns a list of predicted tag strings.

  predict_topic_from_parts(title, description, top_n=5)
      Combines title + description, then calls predict_topics.

Usage:
    from ml_models.tag_classifier.predict import predict_topic_from_parts
    tags = predict_topic_from_parts("Two Sum", "Given an array of integers...")
    print(tags)   # -> ["Array", "Hash Table"]
"""

import os
import numpy as np
import joblib

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODEL_PATH = os.path.join(_HERE, "topic_model.pkl")

_pipeline   = None
_mlb        = None
_thresholds = None
_classes    = None


def _load_model() -> None:
    """Load multi-label model from disk. Called once on first prediction."""
    global _pipeline, _mlb, _thresholds, _classes

    if _pipeline is not None:
        return

    if not os.path.exists(_MODEL_PATH):
        raise FileNotFoundError(
            f"Topic model not found at '{_MODEL_PATH}'. "
            "Run ml_models/tag_classifier/train.py first."
        )

    payload = joblib.load(_MODEL_PATH)

    if "mlb" not in payload:
        raise FileNotFoundError(
            "Old single-label model format detected. "
            "Please retrain: python ml_models/tag_classifier/train.py"
        )

    _pipeline   = payload["pipeline"]
    _mlb        = payload["mlb"]
    _thresholds = payload["thresholds"]
    _classes    = payload["classes"]
    print(f"[topic_classifier] Multi-label model loaded — {len(_classes)} labels")


def predict_topics(text: str, top_n: int = 5) -> list:
    """
    Predict topic tags for a coding question.

    Uses per-label optimised thresholds from training.
    Always returns at least one tag (the highest confidence one).
    Returns at most top_n tags, ranked by confidence.

    Parameters
    ----------
    text  : str — Combined "<title>. <description>" string.
    top_n : int — Maximum number of tags to return (default 5).

    Returns
    -------
    list[str] — Predicted tag names, e.g. ["Array", "Hash Table"].
    """
    _load_model()

    proba = _pipeline.predict_proba([text])[0]
    thresh_array = np.array([_thresholds[c] for c in _mlb.classes_])
    predictions = proba >= thresh_array

    # Guarantee at least one tag
    if not predictions.any():
        predictions[proba.argmax()] = True

    # Get predicted tags sorted by confidence (highest first)
    indices = np.where(predictions)[0]
    indices_sorted = indices[np.argsort(proba[indices])[::-1]]

    # Limit to top_n
    if len(indices_sorted) > top_n:
        indices_sorted = indices_sorted[:top_n]

    tags = [_mlb.classes_[i] for i in indices_sorted]
    return tags


def predict_topic(text: str) -> str:
    """Backward-compatible: returns the single highest-confidence tag."""
    tags = predict_topics(text, top_n=1)
    return tags[0] if tags else ""


def predict_topic_from_parts(title: str, description: str, top_n: int = 5) -> list:
    """
    Predict topic tags from separate title and description strings.

    Parameters
    ----------
    title       : str — Question title, e.g. "Two Sum"
    description : str — Full problem description text
    top_n       : int — Maximum tags to return (default 5)

    Returns
    -------
    list[str] — Predicted tag names.
    """
    combined = f"{title.strip()}. {description.strip()}"
    return predict_topics(combined, top_n=top_n)


if __name__ == "__main__":
    test_cases = [
        (
            "Two Sum",
            "Given an array of integers nums and an integer target, return indices "
            "of the two numbers such that they add up to target.",
        ),
        (
            "Longest Common Subsequence",
            "Given two strings text1 and text2, return the length of their longest "
            "common subsequence. Use dynamic programming and memoization.",
        ),
        (
            "Binary Tree Inorder Traversal",
            "Given the root of a binary tree, return the inorder traversal of its "
            "node values using depth-first search.",
        ),
        (
            "Valid Parentheses",
            "Given a string s containing just the characters '(', ')', '{', '}', "
            "'[' and ']', determine if the input string is valid using a stack.",
        ),
    ]

    print("Running multi-label prediction tests...\n")
    for title, desc in test_cases:
        tags = predict_topic_from_parts(title, desc)
        print(f"  Title      : {title}")
        print(f"  Tags       : {tags}\n")
