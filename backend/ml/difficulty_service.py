"""
Difficulty prediction service.

Loads difficulty_model.pkl exactly once at import time so every request
pays only inference cost, not deserialization cost.

Usage (from a parser):
    from difficulty_service import predict_difficulty_for_question
    difficulty = predict_difficulty_for_question(question_schema)
"""

import os
import sys
import re

import joblib
import pandas as pd

# ── Locate the model and the ml_models package ───────────────────────────────
_BACKEND_DIR        = os.path.dirname(os.path.dirname(__file__))  # backend/ml/ -> backend/
_ML_MODELS_DIR      = os.path.normpath(os.path.join(_BACKEND_DIR, "..", "ml_models"))
_DIFFICULTY_DIR     = os.path.join(_ML_MODELS_DIR, "difficulty_classifier")
_MODEL_PATH         = os.path.join(_DIFFICULTY_DIR, "difficulty_model.pkl")

# Add difficulty_classifier dir to sys.path to allow importing difficulty_predictor.
if _DIFFICULTY_DIR not in sys.path:
    sys.path.insert(0, _DIFFICULTY_DIR)

try:
    import difficulty_predictor as _dp_module  # type: ignore[import]
    from difficulty_predictor import extract_description_features  # type: ignore[import]
    _HAS_EXTRACTOR = True
    print("\n" + "="*80)
    print("[DIFFICULTY_SERVICE] Extract Description Features: IMPORTED OK")
    print("="*80)

    # ── Joblib pickle fix ─────────────────────────────────────────────────────
    # The pipeline was pickled while difficulty_predictor.py ran as __main__, so
    # joblib stored _squeeze_array / _to_dense under the '__main__' namespace.
    # These are injected back into __main__ here so joblib.load() can resolve them.
    #
    # _squeeze_array is also redefined to use np.atleast_1d so that a single-row
    # DataFrame text column is never squeezed to a scalar string, which would
    # cause the TF-IDF vectorizer to fail with "string object received".
    import numpy as _np
    import sys as _sys

    def _squeeze_array(x):
        """Safe squeeze: never returns a 0-d scalar (fixes single-row inference)."""
        arr = x.squeeze() if hasattr(x, "squeeze") else x
        return _np.atleast_1d(arr)

    _main_module = _sys.modules.get("__main__")
    _INJECT = ["_squeeze_array", "_to_dense"]
    for _fn_name in _INJECT:
        if _main_module is not None:
            fn = _squeeze_array if _fn_name == "_squeeze_array" else getattr(_dp_module, _fn_name, None)
            if fn is not None and not hasattr(_main_module, _fn_name):
                setattr(_main_module, _fn_name, fn)
                print(f"   Injected {_fn_name} into __main__")
    print()

except Exception as e:
    print(f"\n[DIFFICULTY_SERVICE] ERROR: could not import extract_description_features: {e}\n")
    _HAS_EXTRACTOR = False

# ── Load model once ───────────────────────────────────────────────────────────
_model = None
_le    = None

def _load_model():
    global _model, _le
    if _model is not None:
        return
    if not os.path.exists(_MODEL_PATH):
        print("\n" + "="*80)
        print("[DIFFICULTY_SERVICE] MODEL LOADING: FAILED")
        print("="*80)
        print(f"   Model file not found at: {_MODEL_PATH}")
        print("="*80 + "\n")
        return
    try:
        print("\n" + "="*80)
        print("[DIFFICULTY_SERVICE] MODEL LOADING: STARTING")
        print("="*80)
        print(f"  • Loading from: {_MODEL_PATH}")
        bundle = joblib.load(_MODEL_PATH)
        _model = bundle["pipeline"]
        _le    = bundle["label_encoder"]
        classes = list(_le.classes_)
        print(f"   Pipeline loaded successfully")
        print(f"   Label encoder loaded successfully")
        print(f"   Classes: {classes}")
        print("="*80)
        print("[DIFFICULTY_SERVICE] MODEL LOADING: SUCCESS")
        print("="*80 + "\n")
    except Exception as e:
        print("\n" + "="*80)
        print("[DIFFICULTY_SERVICE] MODEL LOADING: ERROR")
        print("="*80)
        print(f"   {str(e)}")
        print("="*80 + "\n")

_load_model()


# ── Plain-text helper (strips Markdown without BeautifulSoup) ─────────────────
def _markdown_to_plain(md: str) -> str:
    """Strip Markdown syntax to get a plain text description for the model."""
    # Fenced code blocks
    md = re.sub(r"```[\s\S]*?```", " ", md)
    # Inline code
    md = re.sub(r"`[^`]*`", " ", md)
    # Heading markers, bold/italic, links, tables
    md = re.sub(r"[#*_\[\]()>|]", " ", md)
    return re.sub(r"\s+", " ", md).strip()


# ── Public API ────────────────────────────────────────────────────────────────
def predict_difficulty_for_question(q) -> str:
    """
    Predict difficulty ("easy" / "medium" / "hard") for a CodingQuestionSchema.

    Falls back to "medium" gracefully if the model is unavailable or errors.

    Parameters
    ----------
    q : CodingQuestionSchema
        The generated coding question (must have time_limit_ms, memory_limit_kb,
        avg_cpu_time_ms, avg_memory_kb, avg_code_lines, question fields populated).
    """
    if _model is None or _le is None:
        print("\n[DIFFICULTY_SERVICE] PREDICTION: MODEL NOT AVAILABLE → Fallback 'medium'\n")
        return "medium"

    try:
        print("\n" + "="*80)
        print("[DIFFICULTY_SERVICE] PREDICTION: STARTING")
        print("="*80)

        # ── Step 1: Extract and clean text ─────────────────────────────────────
        plain_text = _markdown_to_plain(q.question)
        preview = plain_text[:100].replace("\n", " ")
        print(f"\n  [STEP 1] Text Extraction & Cleaning")
        print(f"    • Original length: {len(q.question)} chars")
        print(f"    • Cleaned length:  {len(plain_text)} chars")
        print(f"    • Preview: \"{preview}...\"")

        # ── Step 2: Extract description features ────────────────────────────────
        print(f"\n  [STEP 2] Description Features Extraction")
        if _HAS_EXTRACTOR:
            desc_feats = extract_description_features(f"<p>{plain_text}</p>")
            print(f"     Using full feature extractor (extract_description_features)")
        else:
            desc_feats = {
                "desc_char_len":           len(plain_text),
                "desc_word_count":         len(plain_text.split()),
                "num_sample_inputs":       plain_text.lower().count("sample input"),
                "has_constraints":         int("constraints" in plain_text.lower()),
                "has_recursion_keywords":  0,
                "has_dp_keywords":         0,
                "has_graph_keywords":      0,
                "has_sort_keywords":       0,
                "has_search_keywords":     0,
                "has_string_keywords":     0,
                "has_math_keywords":       0,
                "has_greedy_keywords":     0,
                "has_stack_keywords":      0,
                "has_complexity_keywords": 0,
                "num_large_numbers":       0,
                "num_code_tokens":         0,
                "description_text":        plain_text,
            }
            print(f"    ⚠ Using fallback feature extractor (limited keywords)")

        print(f"    • desc_char_len:          {desc_feats['desc_char_len']}")
        print(f"    • desc_word_count:        {desc_feats['desc_word_count']}")
        print(f"    • num_sample_inputs:      {desc_feats['num_sample_inputs']}")
        print(f"    • has_constraints:        {bool(desc_feats['has_constraints'])}")
        print(f"    • num_large_numbers:      {desc_feats['num_large_numbers']}")
        print(f"    • num_code_tokens:        {desc_feats['num_code_tokens']}")

        # ── Step 3: Map schema fields to model features ─────────────────────────
        print(f"\n  [STEP 3] Schema Field Mapping")
        avg_cpu_time  = float(q.avg_cpu_time_ms  or 0)
        avg_memory    = float(q.avg_memory_kb    or 0)
        avg_code_size = float((q.avg_code_lines  or 0) * 40)
        time_limit    = float(q.time_limit_ms    or 1000)
        memory_limit  = float(q.memory_limit_kb  or 65536)

        print(f"    • time_limit_ms:          {q.time_limit_ms} → {time_limit} in model")
        print(f"    • memory_limit_kb:        {q.memory_limit_kb} → {memory_limit} in model")
        print(f"    • avg_cpu_time_ms:        {q.avg_cpu_time_ms} → {avg_cpu_time} in model")
        print(f"    • avg_memory_kb:          {q.avg_memory_kb} → {avg_memory} in model")
        print(f"    • avg_code_lines:         {q.avg_code_lines} → {avg_code_size} bytes (est.)")

        # ── Step 4: Build feature row ──────────────────────────────────────────
        print(f"\n  [STEP 4] Building Feature Row for Inference")
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
            "desc_words_x_large_nums":  desc_feats["desc_word_count"] * desc_feats["num_large_numbers"],
            "cpu_time_x_code_size":     avg_cpu_time * avg_code_size,
            "description_text":         desc_feats["description_text"],
        }])
        print(f"     Feature row created ({row.shape[0]} row × {row.shape[1]} features)")

        # ── Step 5: Run inference ──────────────────────────────────────────────
        print(f"\n  [STEP 5] Running Model Inference")
        label_int = _model.predict(row)[0]
        result = str(_le.inverse_transform([label_int])[0])
        print(f"    • Raw prediction (encoded): {label_int}")
        print(f"    • Decoded result: {result}")

        # ── Final output ───────────────────────────────────────────────────────
        print("\n" + "="*80)
        color_marker = {
            "easy": "🟢",
            "medium": "🟡",
            "hard": "🔴"
        }.get(result, "○")
        print(f"[DIFFICULTY_SERVICE] PREDICTION: {color_marker} {result.upper()}")
        print("="*80 + "\n")

        return result

    except Exception as e:
        print("\n" + "="*80)
        print("[DIFFICULTY_SERVICE] PREDICTION: ERROR")
        print("="*80)
        print(f"   {str(e)}")
        print("  → Falling back to 'medium'")
        print("="*80 + "\n")
        return "medium"
