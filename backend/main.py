from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import os
import httpx
from db import get_connection
import bcrypt
import jwt
from datetime import datetime, timedelta
import json
from pydantic_models import PromptRequest, RegisterRequest, ModelRequest, LoginRequest, UserResponse, AddXpRequest
from parsers.parser_openai import openai_parser
from parsers.parser_ollama import ollama_parser

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

app = FastAPI()
security = HTTPBearer()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:8000",
]

prompt_guide_file = "./prompt_guide.txt"

current_model = "openai"

# Reads through 'prompt_guide.txt' and stores it inside QUIZ_FORMAT_GUIDE
with open(prompt_guide_file, "r", encoding="utf-8") as file:
    # This variable stores a string. A set of rules that is sent with the users prompt to the AI model. 
    QUIZ_FORMAT_GUIDE = file.read()


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,   
    allow_credentials=True,
    allow_methods=["*"],           
    allow_headers=["*"],            
)

# --- Endpoints ---

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/prompt")
async def send_prompt(prompt: PromptRequest):  
    """
    Takes in a prompt from the user and sends it to the currently selected model by
    using the global 'current_model' variable.
    
    Args:
        prompt (PromptRequest): The prompt request object containing the user's prompt.
        
    Returns:
        Parsed quiz data from the selected model.
    """  
    global current_model
    if current_model == "openai":
        return await openai_request(prompt)
    if current_model == "llama3.1:8b":
        return await llama3_req(prompt)
        

async def openai_request(prompt: PromptRequest):
    """
    Determines the appropriate headers, payload, and URL for the OpenAI API request.
    Sends the request and processes the response using the openai_parser.
    Returns the parsed quiz data to the caller (send_prompt()).
    
    Args:
        prompt (PromptRequest): The prompt request object containing the user's prompt.
        
    Returns:
        Parsed quiz data from the OpenAI model.
    """
    prompt_request =  QUIZ_FORMAT_GUIDE + " \n" + prompt.prompt
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload  = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "you are a quiz generation assistant"},
            {"role": "user", "content": prompt_request}
        ]
    }
    
    timeout = httpx.Timeout(120.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout = timeout) as client: 
        response = await client.post(url, headers=headers, json=payload)
        
    print(response.json())
    
    # Use the OpenAI parser to parse the response
    parsed_quiz = openai_parser(response.json())
    print(f"\n\n\n{parsed_quiz}")
    return parsed_quiz
    
    
async def llama3_req(prompt: PromptRequest):
    """
    Determines the appropriate headers, payload, and URL for the local ollama API request.
    Sends the request and processes the response using the ollama_parser.
    Returns the parsed quiz data to the caller (send_prompt()).
    
    Args:
        prompt (PromptRequest): The prompt request object containing the user's prompt.
        
    Returns:
        Parsed quiz data from the local ollama model.
    """
    prompt_request =  QUIZ_FORMAT_GUIDE + " \n" + prompt.prompt
    
    url = "http://localhost:11434/api/generate"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload  = {
        "model": "llama3.1:8b",
        "prompt": prompt_request,
        "stream": False,  
    }
    
    timeout = httpx.Timeout(120.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout = timeout) as client: 
        response = await client.post(url, headers=headers, json=payload)
        
    print(response.json())
    parsed_quiz = ollama_parser(response.json())
    print(f"\n\n\n{parsed_quiz}")
    return parsed_quiz

@app.get("/health")
async def health_check():
    return{"status" : "alive"}

@app.post("/register")
async def register_user(user_data: RegisterRequest):
    """
    Registers a new user by inserting their data into the database.
    Args:
        user_data (RegisterRequest): The registration request object containing user details.
        
    Returns:
        dict: A success message or an error if the user already exists.
        
    """
    
    # Check if user already exists
    if await user_exists(user_data.email):
        return {"error": "User already exists"}
    
    # Hash the user's password using bcrypt before storing it.
    password_hash = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt()).decode()
    
    # Connect to the database and use a cursor to execute the insert statement
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
            INSERT INTO users(first_name, second_name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (
                user_data.first_name,
                user_data.second_name,
                user_data.email,         
                password_hash
            )
            )
            
            new_user_id = cur.fetchone()["id"]
            print(new_user_id)
    
async def user_exists(email: str) -> bool:
    """
    Checks if a user with the given email already exists in the database.
    
    Args:
        email (str): The email address to check.
        
    Returns:
        bool: True if the user exists, False otherwise.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM users
                WHERE email = %s
                LIMIT 1;
                """,
                (email,)
            )
            return cur.fetchone() is not None

@app.post("/model")
async def change_model(model: ModelRequest):
    
    if model.model not in ["openai", "llama3.1:8b"]:
        return {"error": "Unknown Model"}
    
    global current_model
    current_model = model.model
    
    print(f"Now using {current_model}")
    return {"message":  f"now using {current_model}"}

# --- JWT Helper Functions ---

def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token for a user."""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token and return the payload."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Login Endpoint ---

@app.post("/login")
async def login(login_data: LoginRequest):
    """
    Authenticate a user and return a JWT token.
    
    Args:
        login_data (LoginRequest): The login request containing email and password.
        
    Returns:
        dict: JWT token and user data or an error message.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, second_name, email, password_hash, exp, level, created_at, updated_at
                FROM users
                WHERE email = %s
                LIMIT 1;
                """,
                (login_data.email,)
            )
            user = cur.fetchone()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not bcrypt.checkpw(login_data.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create JWT token
    token = create_access_token(user["id"], user["email"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "first_name": user["first_name"],
            "second_name": user["second_name"],
            "email": user["email"],
            "exp": user["exp"],
            "level": user["level"],
            "created_at": user["created_at"].isoformat() if user["created_at"] else None,
            "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None
        }
    }

# --- Get Current User Endpoint ---

@app.get("/me")
async def get_current_user(token_data: dict = Depends(verify_token)):
    """
    Get the current authenticated user's profile.
    
    Returns:
        dict: User profile data.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, second_name, email, exp, level, created_at, updated_at
                FROM users
                WHERE id = %s
                LIMIT 1;
                """,
                (token_data["user_id"],)
            )
            user = cur.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user["id"],
        "first_name": user["first_name"],
        "second_name": user["second_name"],
        "email": user["email"],
        "exp": user["exp"],
        "level": user["level"],
        "created_at": user["created_at"].isoformat() if user["created_at"] else None,
        "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None
    }

# --- Add XP Endpoint ---

@app.post("/add-xp")
async def add_xp(xp_data: AddXpRequest, token_data: dict = Depends(verify_token)):
    """
    Add XP to the authenticated user's account.
    
    Args:
        xp_data (AddXpRequest): The XP amount to add.
        token_data (dict): The decoded JWT token data.
        
    Returns:
        dict: Updated user data with new XP and level.
    """
    user_id = token_data["user_id"]
    xp_to_add = xp_data.xp_amount
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Get current XP and level
            cur.execute(
                """
                SELECT exp, level
                FROM users
                WHERE id = %s
                LIMIT 1;
                """,
                (user_id,)
            )
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            current_exp = user["exp"] or 0
            current_level = user["level"] or 1
            
            # Calculate new XP and level
            new_exp = current_exp + xp_to_add
            
            # Level up logic: 100 XP per level
            xp_per_level = 100
            new_level = (new_exp // xp_per_level) + 1
            
            # Update user's XP and level
            cur.execute(
                """
                UPDATE users
                SET exp = %s, level = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, first_name, second_name, email, exp, level, created_at, updated_at;
                """,
                (new_exp, new_level, user_id)
            )
            updated_user = cur.fetchone()
            conn.commit()
    
    return {
        "id": updated_user["id"],
        "first_name": updated_user["first_name"],
        "second_name": updated_user["second_name"],
        "email": updated_user["email"],
        "exp": updated_user["exp"],
        "level": updated_user["level"],
        "created_at": updated_user["created_at"].isoformat() if updated_user["created_at"] else None,
        "updated_at": updated_user["updated_at"].isoformat() if updated_user["updated_at"] else None,
        "xp_gained": xp_to_add
    }
