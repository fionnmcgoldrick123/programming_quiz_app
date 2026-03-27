"""
Utility helpers for computing text-derived metadata from a generated coding question.
These fields can be calculated deterministically from the AI's output and do not
need to be asked of the model.
"""

import re


def _strip_markdown(text: str) -> str:
    """Remove common markdown syntax to get plain text for word/char counting."""
    # Remove fenced code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    text = re.sub(r"`[^`]*`", "", text)
    # Remove heading markers, bold/italic markers, links
    text = re.sub(r"[#*_\[\]()>|]", " ", text)
    return text


def compute_coding_metadata(question: str, starter_code: str, test_cases: list[str]) -> dict:
    """
    Compute the text-derived metadata fields for a coding problem.

    Args:
        question:      The Markdown-formatted question string.
        starter_code:  The code stub provided as starter code.
        test_cases:    List of test case strings.

    Returns:
        dict with keys: desc_char_len, desc_word_count, num_sample_inputs,
                        has_constraints, num_large_numbers, num_code_tokens.
    """
    plain = _strip_markdown(question)

    desc_char_len = len(question)
    desc_word_count = len(plain.split())
    num_sample_inputs = len(test_cases)
    has_constraints = bool(re.search(r"constraints", question, re.IGNORECASE))

    # Count numbers in the question that are >= 10,000 (large numbers / exponents)
    # Also treat scientific exponents like 10^4 as large
    raw_numbers = re.findall(r"\b\d[\d,]*\b", question)
    large_count = 0
    for n in raw_numbers:
        try:
            val = int(n.replace(",", ""))
            if val >= 10_000:
                large_count += 1
        except ValueError:
            pass
    # Count explicit power-of-ten expressions like 10^4, 10^9
    exponent_matches = re.findall(r"10\^(\d+)", question)
    for exp in exponent_matches:
        if int(exp) >= 4:
            large_count += 1

    num_large_numbers = large_count

    # Approximate code token count: split on whitespace and common delimiters.
    code_tokens = re.split(r"[\s\(\)\[\]{},;:.=+\-*/!<>\"'\\]+", starter_code)
    num_code_tokens = len([t for t in code_tokens if t])

    return {
        "desc_char_len": desc_char_len,
        "desc_word_count": desc_word_count,
        "num_sample_inputs": num_sample_inputs,
        "has_constraints": has_constraints,
        "num_large_numbers": num_large_numbers,
        "num_code_tokens": num_code_tokens,
    }
