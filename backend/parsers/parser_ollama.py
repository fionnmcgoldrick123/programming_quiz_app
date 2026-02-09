from pydantic_models import QuizSchema, CodingQuestionSchema
import json
import re

def ollama_parser(response: dict) -> list[QuizSchema]:
    """
    Parses the response from the local-running ollama model
    by fixing formatting issues and extracting quiz data. 
    Parses the cleaned content into QuizSchema objects.

    Args:
        response (dict): The response dictionary from the ollama model.

    Returns:
        list[QuizSchema]: A list of QuizSchema objects extracted from the response.
    """
    content = response["response"]


    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print("JSON parsing failed:", e)
        print("Final content was:\n", content)
        return {"Error": "Failed to parse JSON"}

    quiz_title = data.get("title", "Untitled Quiz")

    questions = []

    for q in data.get("questions", []):
        raw_opts = q.get("options", [])

        # Clean options by removing prefixes like "A: ", "B: ", etc.
        clean_options = [
            opt.split(": ", 1)[1] if ": " in opt else opt
        for opt in raw_opts
        ]

        questions.append(
            QuizSchema(
                title=quiz_title,
                question=q["question"],
                options=clean_options,
                correct_answer=q["answer"]
            )
        )

    return questions


def ollama_coding_parser(response: dict) -> list[CodingQuestionSchema]:
    """
    Parses the response from the local-running ollama model
    into CodingQuestionSchema objects for coding challenges.

    Args:
        response (dict): The response dictionary from the ollama model.

    Returns:
        list[CodingQuestionSchema]: A list of coding question objects.
    """
    content = response["response"]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print("JSON parsing failed:", e)
        print("Final content was:\n", content)
        return {"Error": "Failed to parse JSON"}

    questions = []

    for q in data.get("questions", []):
        questions.append(
            CodingQuestionSchema(
                question=q["question"],
                starter_code=q.get("starter_code", ""),
                test_cases=q.get("test_cases", []),
                hints=q.get("hints", []),
            )
        )

    return questions