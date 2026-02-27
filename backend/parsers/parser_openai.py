from pydantic_models import QuizSchema, CodingQuestionSchema
import json


def openai_parser(response: dict) -> QuizSchema:
    """
    Parses the response from the OpenAI model into QuizSchema objects.
    It extracts quiz title, questions, options, and correct answers.

    Args:
        response (dict): The response dictionary from the OpenAI model.

    Returns:
        list[QuizSchema]: A list of QuizSchema objects extracted from the response.
    """
    content = response["choices"][0]["message"]["content"]

    # Attempt to parse the content as JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print("JSON parsing failed: ", e)
        return {"Error": "Failed to parse JSON"}

    print("Parsed Quiz Data:", data)

    # Accept both 'quiz_title' and 'title' keys, fallback to a generated title if missing/empty
    quiz_title = data.get("quiz_title") or data.get("title")
    if (
        not quiz_title
        or not isinstance(quiz_title, str)
        or not quiz_title.strip()
        or quiz_title.strip().lower() == "untitled quiz"
    ):
        quiz_title = f"Quiz ({len(data.get('questions', []))} Questions)"

    questions = []

    # Iterate through each question and create QuizSchema objects. Push to list.
    for q in data["questions"]:
        questions.append(
            QuizSchema(
                title=quiz_title,
                question=q["question"],
                options=q["options"],
                correct_answer=q["answer"],
            )
        )
    return questions


def openai_coding_parser(response: dict) -> list[CodingQuestionSchema]:
    """
    Parses the response from the OpenAI model into CodingQuestionSchema objects.
    Extracts coding challenge questions from the AI response.

    Args:
        response (dict): The response dictionary from the OpenAI model.

    Returns:
        list[CodingQuestionSchema]: A list of coding question objects.
    """
    content = response["choices"][0]["message"]["content"]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print("JSON parsing failed: ", e)
        return {"Error": "Failed to parse JSON"}

    print("Parsed Coding Quiz Data:", data)

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
