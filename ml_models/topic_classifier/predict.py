"""
Topic Classifier — Prediction Module
======================================
Provides a simple interface for loading the trained topic_model.pkl and
running inference on new programming questions.

The trained pipeline expects a single combined string of
    "<title>. <problem_description>"
as its input.  Two convenience functions are exposed:

  predict_topic(text)
      Takes a single raw string and returns the predicted topic label.

  predict_topic_from_parts(title, description)
      Combines title + description in the same format used during training,
      then calls predict_topic.  Use this from the backend service.

Usage example:
    from ml_models.topic_classifier.predict import predict_topic_from_parts
    tag = predict_topic_from_parts("Two Sum", "Given an array of integers...")
    print(tag)   # -> "Array"
"""

import os
import joblib

# ── Locate the model file relative to this script ────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_MODEL_PATH = os.path.join(_HERE, "topic_model.pkl")

# ── Module-level cache: load the model once, reuse on every call ─────────────
# Deserialising a joblib pkl on every prediction would add unnecessary latency,
# so we store the pipeline and class list in module globals after the first load.
_pipeline = None
_classes  = None


def _load_model() -> None:
    """
    Load topic_model.pkl from disk into the module-level cache.
    Called automatically on the first prediction; subsequent calls are no-ops.
    Raises FileNotFoundError if the model has not been trained yet.
    """
    global _pipeline, _classes

    if _pipeline is not None:
        # Model already loaded — nothing to do
        return

    if not os.path.exists(_MODEL_PATH):
        raise FileNotFoundError(
            f"Topic model not found at '{_MODEL_PATH}'. "
            "Run ml_models/topic_classifier/train.py first to generate it."
        )

    # joblib.load returns the dict saved by save_model() in train.py:
    #   { "pipeline": <sklearn Pipeline>, "classes": [list of label strings] }
    payload    = joblib.load(_MODEL_PATH)
    _pipeline  = payload["pipeline"]
    _classes   = payload["classes"]
    print(f"[topic_classifier] Model loaded — {len(_classes)} classes: {_classes}")


def predict_topic(text: str) -> str:
    """
    Predict the primary algorithmic topic for a single question text string.

    Parameters
    ----------
    text : str
        A combined string of the form "<title>. <problem description>", or
        just the problem description on its own.  Longer, richer text will
        produce more confident predictions.

    Returns
    -------
    str
        The predicted topic label, e.g. "Array", "Dynamic Programming",
        "Hash Table", "String", etc.
    """
    # Lazy-load the model on first call
    _load_model()

    # pipeline.predict expects a list/array of strings, not a bare string.
    # We wrap in a list and unpack the single result.
    prediction = _pipeline.predict([text])
    return prediction[0]


def predict_topic_from_parts(title: str, description: str) -> str:
    """
    Predict the primary topic from separate title and description strings.

    This function mirrors the feature-engineering step in train.py so that
    inference uses exactly the same input format as training:

        "<title>. <problem_description>"

    Parameters
    ----------
    title       : str  — Question title, e.g. "Two Sum"
    description : str  — Full problem description text

    Returns
    -------
    str
        Predicted topic label.
    """
    # Replicate the text combination used in load_and_clean() in train.py
    combined = f"{title.strip()}. {description.strip()}"
    return predict_topic(combined)


# ── Quick standalone test ─────────────────────────────────────────────────────
# Run this file directly to verify the model loads and predicts correctly:
#   python ml_models/topic_classifier/predict.py
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

    print("Running prediction tests...\n")
    for title, desc in test_cases:
        tag = predict_topic_from_parts(title, desc)
        print(f"  Title      : {title}")
        print(f"  Prediction : {tag}\n")
