from typing import List, Optional, Literal
from pydantic import BaseModel, field_validator
from datetime import datetime

# Supported languages for code generation
SUPPORTED_LANGUAGES = {
    "python", "javascript", "typescript", "java", "cpp", "c", 
    "csharp", "ruby", "go", "rust", "php", "swift", "kotlin"
}

class QuizSchema(BaseModel):
    title: str
    question: str
    options: List[str]
    correct_answer: str
    topic_tags: List[str] = []  # AI-predicted topic tags


class PromptRequest(BaseModel):
    prompt: str
    num_questions: Optional[int] = None
    quiz_type: Optional[str] = None
    language: Optional[str] = None
    topic: Optional[str] = None
    
    @field_validator('num_questions')
    @classmethod
    def validate_num_questions(cls, v):
        if v is not None and (v < 1 or v > 20):
            raise ValueError('num_questions must be between 1 and 20')
        return v
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        if v is not None and v.lower() not in SUPPORTED_LANGUAGES:
            raise ValueError(f'language must be one of: {", ".join(sorted(SUPPORTED_LANGUAGES))}')
        return v
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v):
        if v is not None and (len(v) < 3 or len(v) > 100):
            raise ValueError('topic must be between 3 and 100 characters')
        return v


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


class EmailRequest(BaseModel):
    email: str


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


class SaveQuizResultRequest(BaseModel):
    quiz_type: str  # "mcq" or "coding"
    total_questions: int
    correct_answers: int
    tags: List[str] = []
    language: Optional[str] = None
    prompt: Optional[str] = None


class QuizSessionSchema(BaseModel):
    """Schema for a saved quiz session with questions and score."""
    id: int
    user_id: int
    topic: str
    language: Optional[str]
    quiz_type: str
    questions: List[dict]  # Stored as JSONB
    score: int
    created_at: datetime


class FriendRequestAction(BaseModel):
    friendship_id: int


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3 or len(v) > 30:
            raise ValueError("Display name must be between 3 and 30 characters")
        return v

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v):
        if v is None:
            return v
        if len(v) > 300:
            raise ValueError("Bio must be 300 characters or fewer")
        return v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v):
        if v is None:
            return v
        # Max 5MB base64 string (roughly 5mil chars)
        if len(v) > 5_000_000:
            raise ValueError("Image too large (max 5 MB)")
        return v


class FriendRequestAction(BaseModel):
    friendship_id: int
    action: str  # "accept" or "reject"


