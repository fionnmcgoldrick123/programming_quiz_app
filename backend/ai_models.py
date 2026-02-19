"""
AI Models module.
Handles requests to different AI models (OpenAI, Ollama) for quiz generation.
"""

import httpx
from config import OPENAI_API_KEY, QUIZ_FORMAT_GUIDE, CODING_FORMAT_GUIDE
from pydantic_models import PromptRequest
from parsers.parser_openai import openai_parser, openai_coding_parser
from parsers.parser_ollama import ollama_parser, ollama_coding_parser


async def send_prompt_to_model(prompt: PromptRequest, model: str):
    """
    Send a prompt to the specified AI model.

    Args:
        prompt (PromptRequest): The prompt request object.
        model (str): The model to use ('openai' or 'llama3.1:8b').

    Returns:
        Parsed quiz data from the selected model.
    """
    if model == "openai":
        return await openai_request(prompt)
    elif model == "llama3.1:8b":
        return await llama3_request(prompt)
    else:
        raise ValueError(f"Unknown model: {model}")


async def openai_request(prompt: PromptRequest):
    """
    Send a request to OpenAI API and parse the response.

    Args:
        prompt (PromptRequest): The prompt request object containing the user's prompt.

    Returns:
        Parsed quiz data from the OpenAI model.
    """
    is_coding = prompt.quiz_type == "coding"
    guide = CODING_FORMAT_GUIDE if is_coding else QUIZ_FORMAT_GUIDE

    prompt_request = guide + " \n"
    if prompt.num_questions:
        prompt_request += f"Generate exactly {prompt.num_questions} questions. \n"
    if is_coding and prompt.language:
        prompt_request += f"The programming language is {prompt.language}. \n"
    prompt_request += prompt.prompt

    url = "https://api.openai.com/v1/chat/completions"

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

    system_content = "you are a coding challenge generation assistant" if is_coding else "you are a quiz generation assistant"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "system", "content": system_content}, {"role": "user", "content": prompt_request}],
    }

    timeout = httpx.Timeout(120.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)

    print(response.json())

    # Use the appropriate parser based on quiz type
    if is_coding:
        parsed_quiz = openai_coding_parser(response.json())
    else:
        parsed_quiz = openai_parser(response.json())
    print(f"\n\n\n{parsed_quiz}")
    return parsed_quiz


async def llama3_request(prompt: PromptRequest):
    """
    Send a request to local Ollama API and parse the response.

    Args:
        prompt (PromptRequest): The prompt request object containing the user's prompt.

    Returns:
        Parsed quiz data from the local Ollama model.
    """
    is_coding = prompt.quiz_type == "coding"
    guide = CODING_FORMAT_GUIDE if is_coding else QUIZ_FORMAT_GUIDE

    prompt_request = guide + " \n"
    if prompt.num_questions:
        prompt_request += f"Generate exactly {prompt.num_questions} questions. \n"
    if is_coding and prompt.language:
        prompt_request += f"The programming language is {prompt.language}. \n"
    prompt_request += prompt.prompt

    url = "http://localhost:11434/api/generate"

    headers = {"Content-Type": "application/json"}

    payload = {
        "model": "llama3.1:8b",
        "prompt": prompt_request,
        "stream": False,
    }

    timeout = httpx.Timeout(120.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)

    print(response.json())
    if is_coding:
        parsed_quiz = ollama_coding_parser(response.json())
    else:
        parsed_quiz = ollama_parser(response.json())
    print(f"\n\n\n{parsed_quiz}")
    return parsed_quiz
