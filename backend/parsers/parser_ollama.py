from pydantic_models import QuizSchema, CodingQuestionSchema
from ml.quiz_metadata import compute_coding_metadata
from ml.difficulty_service import predict_difficulty_for_question
from ml.tag_service import predict_tags_for_question
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

    # Accept both 'title' and 'quiz_title' keys, fallback to a generated title if missing/empty
    quiz_title = data.get("title") or data.get("quiz_title")
    if (
        not quiz_title
        or not isinstance(quiz_title, str)
        or not quiz_title.strip()
        or quiz_title.strip().lower() == "untitled quiz"
    ):
        quiz_title = f"Quiz ({len(data.get('questions', []))} Questions)"

    questions = []

    for q in data.get("questions", []):
        raw_opts = q.get("options", [])

        # Clean options by removing prefixes like "A: ", "B: ", etc.
        clean_options = [
            opt.split(": ", 1)[1] if ": " in opt else opt for opt in raw_opts
        ]

        # Get topic tags from AI response, or predict them
        topic_tags = q.get("topic_tags", [])
        if not topic_tags:
            topic_tags = predict_tags_for_question(quiz_title, q["question"])
            print(f"[TAG_SERVICE] MCQ predicted tags: {topic_tags}")
        else:
            print(f"[TAG_SERVICE] MCQ tags from AI: {topic_tags}")

        questions.append(
            QuizSchema(
                title=quiz_title,
                question=q["question"],
                options=clean_options,
                correct_answer=q["answer"],
                topic_tags=topic_tags,
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
        question = q["question"]
        starter_code = q.get("starter_code", "")
        test_cases = q.get("test_cases", [])
        computed = compute_coding_metadata(question, starter_code, test_cases)
        
        # Get topic tags from AI response, or predict them
        topic_tags = q.get("topic_tags", [])
        if not topic_tags:
            question_title = q.get("title", "Coding Challenge")
            topic_tags = predict_tags_for_question(question_title, question)
            print(f"[TAG_SERVICE] Coding predicted tags: {topic_tags}")
        else:
            print(f"[TAG_SERVICE] Coding tags from AI: {topic_tags}")
            topic_tags = predict_tags_for_question(question_title, question)
        
        schema = CodingQuestionSchema(
            question=question,
            starter_code=starter_code,
            test_cases=test_cases,
            hints=q.get("hints", []),
            time_limit_ms=q.get("time_limit_ms", 1000),
            memory_limit_kb=q.get("memory_limit_kb", 65536),
            topic_tags=topic_tags,
            avg_cpu_time_ms=q.get("avg_cpu_time_ms", 0),
            avg_memory_kb=q.get("avg_memory_kb", 0),
            avg_code_lines=q.get("avg_code_lines", 0),
            **computed,
        )
        schema.difficulty = predict_difficulty_for_question(schema)
        questions.append(schema)

    return questions
