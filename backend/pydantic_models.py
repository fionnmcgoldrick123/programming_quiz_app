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