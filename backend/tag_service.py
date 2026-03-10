"""
Tag Service — Tagging questions with AI-predicted topics
=========================================================
Uses the trained topic classifier to automatically tag coding and MCQ questions
with their primary algorithmic topics.

The topic classifier predicts topics like: Array, Hash Table, String, 
Dynamic Programming, Graph, etc.
"""

import os
import sys

# Add the topic_classifier directory to sys.path so predict.py can be imported directly
_BACKEND_DIR       = os.path.dirname(os.path.abspath(__file__))
_TOPIC_DIR         = os.path.normpath(os.path.join(_BACKEND_DIR, "..", "ml_models", "topic_classifier"))

if _TOPIC_DIR not in sys.path:
    sys.path.insert(0, _TOPIC_DIR)

try:
    from predict import predict_topic_from_parts  # type: ignore[import]
    PREDICTOR_AVAILABLE = True
    print("\n" + "="*80)
    print("[TAG_SERVICE] Topic classifier: LOADED OK")
    print("="*80 + "\n")
except Exception as e:
    PREDICTOR_AVAILABLE = False
    print(
        f"\n[TAG_SERVICE] WARNING: Topic classifier not available ({e}). "
        "Questions will not be automatically tagged. "
        "Train the model first: python ml_models/topic_classifier/train.py\n"
    )


def predict_tags_for_question(
    title: str, 
    description: str, 
    top_n: int = 1
) -> list:
    """
    Predict the primary algorithmic topic(s) for a question.
    
    Parameters
    ----------
    title : str
        The question title/name.
    description : str
        The question description/problem statement.
    top_n : int, optional
        Number of top predictions to return. Default is 1.
        (Currently the model returns one prediction; top_n is for future extension)
    
    Returns
    -------
    list[str]
        A list of predicted topic tags, e.g., ["Array"] or ["Dynamic Programming"].
        Returns an empty list if the predictor is unavailable.
    
    Examples
    --------
    >>> predict_tags_for_question("Two Sum", "Given an array of integers...")
    ["Array"]
    
    >>> predict_tags_for_question("Fibonacci", "Find the nth Fibonacci number...")
    ["Dynamic Programming"]
    """
    if not PREDICTOR_AVAILABLE:
        return []
    
    try:
        predicted_topic = predict_topic_from_parts(title, description)
        return [predicted_topic] if predicted_topic else []
    except Exception as e:
        print(f"[ERROR] Tag prediction failed: {e}")
        return []


def enrich_question_with_tags(
    question_dict: dict,
    title_field: str = "title",
    description_field: str = "question"
) -> dict:
    """
    Automatically populate topic_tags field if empty.
    
    Parameters
    ----------
    question_dict : dict
        The question data (typically converted from a Pydantic model).
    title_field : str
        Name of the field containing the question title.
    description_field : str
        Name of the field containing the question description.
    
    Returns
    -------
    dict
        The question data with topic_tags populated if it wasn't already.
    
    Examples
    --------
    >>> q = {"title": "Two Sum", "question": "Find two numbers that sum to target", 
    ...      "topic_tags": []}
    >>> enrich_question_with_tags(q)
    {"title": "Two Sum", "question": "...", "topic_tags": ["Array"]}
    """
    # Only predict tags if the field is empty
    if question_dict.get("topic_tags") is None or (
        isinstance(question_dict.get("topic_tags"), list) 
        and len(question_dict["topic_tags"]) == 0
    ):
        title = question_dict.get(title_field, "")
        description = question_dict.get(description_field, "")
        
        if title or description:
            predicted_tags = predict_tags_for_question(title, description)
            question_dict["topic_tags"] = predicted_tags
    
    return question_dict
