from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class QuizSchema(BaseModel):
    title: str
    question: str
    options: List[str]
    correct_answer: str


class PromptRequest(BaseModel):
    prompt: str
    num_questions: Optional[int] = None
    quiz_type: Optional[str] = None
    language: Optional[str] = None


class CodingQuestionSchema(BaseModel):
    question: str
    starter_code: str = ""
    test_cases: List[str] = []
    hints: List[str] = []
    difficulty: str = ""  # "easy" | "medium" | "hard" — predicted by ML model
    # AI-generated metadata
    time_limit_ms: int = 1000
    memory_limit_kb: int = 65536
    topic_tags: List[str] = []
    avg_cpu_time_ms: int = 0
    avg_memory_kb: int = 0
    avg_code_lines: int = 0
    # Computed from text
    desc_char_len: int = 0
    desc_word_count: int = 0
    num_sample_inputs: int = 0
    has_constraints: bool = False
    num_large_numbers: int = 0
    num_code_tokens: int = 0


class ModelRequest(BaseModel):
    model: str


class RegisterRequest(BaseModel):
    first_name: str
    second_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    first_name: str
    second_name: str
    email: str
    exp: int
    level: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AddXpRequest(BaseModel):
    xp_amount: int


class RunCodeRequest(BaseModel):
    code: str
    language: str


class SubmitCodeRequest(BaseModel):
    code: str
    language: str
    test_cases: List[str]


class McqHintRequest(BaseModel):
    question: str
    options: List[str]


