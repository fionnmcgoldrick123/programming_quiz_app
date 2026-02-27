"""
GraphCodeBERT Hints Module.

GraphCodeBERT's role here is honest and specific:
  - Compare student code against the starter stub to measure progress
  - Detect if the student has written anything meaningful yet
  - Produce a structured signal that gets passed to the LLM for hint generation

The LLM (OpenAI/Llama) then generates the actual English hint text.
"""

from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import httpx
import json
import re

# Load model once at startup 
MODEL_NAME = "microsoft/graphcodebert-base"
print("Loading GraphCodeBERT...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
gcb_model = AutoModel.from_pretrained(MODEL_NAME)
gcb_model.eval()
print("GraphCodeBERT ready.")


def get_embedding(text: str) -> np.ndarray:
    """Convert code/text to a GraphCodeBERT embedding vector."""
    inputs = tokenizer(
        text,
        return_tensors="pt",
        max_length=512,
        truncation=True,
        padding="max_length"
    )
    with torch.no_grad():
        outputs = gcb_model(**inputs)
    return outputs.last_hidden_state[:, 0, :].squeeze().numpy()


def analyse_student_code(
    student_code: str,
    starter_code: str,
    test_cases: list[str],
    language: str
) -> dict:
    
    """
    Use GraphCodeBERT to analyse the student's code against the starter stub.
    Returns a structured signal dict that gets passed to the LLM.

    This is what GraphCodeBERT is genuinely good at:
      - Has the student changed anything from the stub?
      - How much progress have they made structurally?
      - Is the code still essentially empty?
    """
    student_emb = get_embedding(f"{language} {student_code}").reshape(1, -1)
    starter_emb = get_embedding(f"{language} {starter_code}").reshape(1, -1)

    # High similarity = barely changed from stub, low = significant work done
    similarity_to_stub = float(cosine_similarity(student_emb, starter_emb)[0][0])
    progress_score = round(1.0 - similarity_to_stub, 3)

    # Count meaningful lines — ignore comments, blanks, stub boilerplate
    lines = student_code.strip().splitlines()
    meaningful_lines = [
        l for l in lines
        if l.strip()
        and not l.strip().startswith("//")
        and not l.strip().startswith("#")
        and not l.strip().startswith("*")
        and "TODO" not in l
        and "Write your solution here" not in l
    ]
    meaningful_line_count = len(meaningful_lines)

    # Determine progress stage
    if progress_score < 0.03 or meaningful_line_count < 2:
        stage = "not_started"
    elif progress_score < 0.15 or meaningful_line_count < 5:
        stage = "early"
    elif progress_score < 0.35:
        stage = "in_progress"
    else:
        stage = "substantial"

    return {
        "progress_score": progress_score,
        "similarity_to_stub": round(similarity_to_stub, 3),
        "meaningful_line_count": meaningful_line_count,
        "stage": stage,
    }


# MCQ Hints (uses LLM directly)

async def generate_mcq_hints(
    question: str,
    options: list[str],
    model: str = "openai"
) -> list[str]:
    """
    Generate hints for an MCQ question using the AI model.
    Asks the model for hints that guide without revealing the answer.
    """
    options_text = "\n".join([f"{['A','B','C','D'][i]}: {opt}" for i, opt in enumerate(options)])

    prompt = f"""A student is answering this multiple choice question:

Question: {question}

Options:
{options_text}

Give 2 short hints that help the student think in the right direction WITHOUT revealing or implying the correct answer.
Do not mention any option by letter or say which is correct.
Each hint should be one sentence. Return only the hints as a JSON array of strings, nothing else.
Example: ["hint one", "hint two"]"""

    if model == "openai":
        from config import OPENAI_API_KEY
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a helpful quiz tutor. Never reveal correct answers."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
        content = response.json()["choices"][0]["message"]["content"]
    else:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                headers={"Content-Type": "application/json"},
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False}
            )
        content = response.json()["response"]

    match = re.search(r'\[.*?\]', content, re.DOTALL)
    if match:
        return json.loads(match.group())
    return [
        "Think carefully about what the question is specifically asking.",
        "Consider the core concept the question is testing."
    ]


# Coding Hints (GraphCodeBERT analysis → LLM hint generation)

async def generate_coding_hints(
    question: str,
    student_code: str,
    starter_code: str,
    test_cases: list[str],
    language: str = "python",
    model: str = "openai"
) -> list[str]:
    """
    Generate coding hints by combining GraphCodeBERT analysis with LLM generation.

    GraphCodeBERT analyses how far the student has progressed from the starter stub.
    That signal is passed as context to the LLM which generates the actual hint text.
    """

    # Step 1: GraphCodeBERT analyses progress from starter stub 
    analysis = analyse_student_code(student_code, starter_code, test_cases, language)

    stage = analysis["stage"]
    progress = analysis["progress_score"]
    lines = analysis["meaningful_line_count"]

    # Step 2: Translate the analysis into plain English context 
    if stage == "not_started":
        code_context = "The student has not written any meaningful code yet — they still have the empty starter stub."
    elif stage == "early":
        code_context = f"The student has just started — they have written about {lines} meaningful lines and made small changes to the stub (progress score: {progress})."
    elif stage == "in_progress":
        code_context = f"The student is working on it — they have written {lines} meaningful lines and made moderate progress from the stub (progress score: {progress})."
    else:
        code_context = f"The student has written a substantial attempt — {lines} meaningful lines, significantly different from the starter stub (progress score: {progress})."

    test_cases_text = "\n".join(test_cases) if test_cases else "No test cases provided."

    # Step 3: LLM generates relevant hint text using all the context
    prompt = f"""A student is working on this coding challenge:

Question: {question}

Language: {language}

Test Cases:
{test_cases_text}

Their current code:
```{language}
{student_code}
```

Code progress context (from static analysis): {code_context}

Based on their current code and progress stage, give 2 helpful hints.
- Do NOT give away the solution or write code for them
- Do NOT just repeat the question back
- Be specific to what they have written (or not written) so far
- If they haven't started, hint about how to approach the problem
- If they're in progress, hint about what might be missing or wrong
Return only a JSON array of 2 hint strings, nothing else.
Example: ["hint one", "hint two"]"""

    if model == "openai":
        from config import OPENAI_API_KEY
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a coding tutor. Never reveal the full solution."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
        content = response.json()["choices"][0]["message"]["content"]
    else:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                headers={"Content-Type": "application/json"},
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False}
            )
        content = response.json()["response"]

    match = re.search(r'\[.*?\]', content, re.DOTALL)
    if match:
        return json.loads(match.group())
    return [
        "Think about what the problem is asking you to return.",
        "Consider what data structure or algorithm fits this problem best."
    ]