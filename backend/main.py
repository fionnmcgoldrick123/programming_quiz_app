"""
Main FastAPI application.
Routes requests to appropriate modules for handling.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import configuration
from config import CORS_ORIGINS, DEFAULT_MODEL, SUPPORTED_MODELS

# Import authentication
from auth import verify_token

# Import Pydantic models
from pydantic_models import (
    PromptRequest, 
    RegisterRequest, 
    ModelRequest, 
    LoginRequest, 
    AddXpRequest,
    RunCodeRequest,
    SubmitCodeRequest
)

# Import service modules
from users import register_user, login_user, get_user_profile, add_user_xp
from ai_models import send_prompt_to_model
from code_executor import run_code, submit_code

# Initialize FastAPI app
app = FastAPI()

# Global variable for current model
current_model = DEFAULT_MODEL

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,   
    allow_credentials=True,
    allow_methods=["*"],           
    allow_headers=["*"],            
)


# --- Root Endpoints ---

@app.get("/")
async def read_root():
    """Root endpoint returning a simple greeting."""
    return {"Hello": "World"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "alive"}


# --- AI Model Endpoints ---


@app.post("/prompt")
async def send_prompt(prompt: PromptRequest):  
    """
    Send a prompt to the currently selected AI model for quiz generation.
    
    Args:
        prompt (PromptRequest): The prompt request object containing the user's prompt.
        
    Returns:
        Parsed quiz data from the selected model.
    """  
    global current_model
    return await send_prompt_to_model(prompt, current_model)


@app.post("/model")
async def change_model(model: ModelRequest):
    """
    Change the currently active AI model.
    
    Args:
        model (ModelRequest): The model selection request.
        
    Returns:
        dict: Confirmation message or error.
    """
    if model.model not in SUPPORTED_MODELS:
        return {"error": "Unknown Model"}
    
    global current_model
    current_model = model.model
    
    print(f"Now using {current_model}")
    return {"message": f"now using {current_model}"}


# --- Authentication Endpoints ---


@app.post("/register")
async def register(user_data: RegisterRequest):
    """
    Register a new user.
    
    Args:
        user_data (RegisterRequest): The registration request object.
        
    Returns:
        dict: Success message or error.
    """
    return await register_user(user_data)


@app.post("/login")
async def login(login_data: LoginRequest):
    """
    Authenticate a user and return a JWT token.
    
    Args:
        login_data (LoginRequest): The login request containing email and password.
        
    Returns:
        dict: JWT token and user data or an error message.
    """
    return await login_user(login_data)


@app.get("/me")
async def get_current_user(token_data: dict = Depends(verify_token)):
    """
    Get the current authenticated user's profile.
    
    Args:
        token_data (dict): The decoded JWT token data.
    
    Returns:
        dict: User profile data.
    """
    return await get_user_profile(token_data["user_id"])


# --- User XP Endpoints ---


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
    return await add_user_xp(token_data["user_id"], xp_data.xp_amount)


# --- Code Execution Endpoints ---

@app.post("/run-code")
async def execute_code_endpoint(request: RunCodeRequest):
    """
    Execute code and return the output or error.
    
    Args:
        request (RunCodeRequest): Contains code and language.
        
    Returns:
        dict: Execution result with output or error.
    """
    return await run_code(request)


@app.post("/submit-code")
async def submit_code_endpoint(request: SubmitCodeRequest):
    """
    Execute code against test cases and return results.
    
    Args:
        request (SubmitCodeRequest): Contains code, language, and test cases.
        
    Returns:
        dict: Test results with pass/fail status for each test case.
    """
    return await submit_code(request)
