"""
Main FastAPI application.
Routes requests to appropriate modules for handling.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, DEFAULT_MODEL, SUPPORTED_MODELS
from core.auth import verify_token
from pydantic_models import (
    PromptRequest,
    RegisterRequest,
    ModelRequest,
    LoginRequest,
    EmailRequest,
    AddXpRequest,
    RunCodeRequest,
    SubmitCodeRequest,
    McqHintRequest,
    SaveQuizResultRequest,
    FriendRequestAction,
    UpdateProfileRequest,
)

from services.users import (
    register_user, login_user, get_user_profile, add_user_xp,
    save_quiz_result, get_user_stats, init_db,
    search_users, get_public_profile, send_friend_request,
    respond_to_friend_request, get_friend_requests, get_friends_list,
    remove_friend, get_friend_count, get_pending_request_count,
    get_user_stats_public, update_user_profile, verify_user_email,
    resend_verification_email, save_quiz_session, get_quiz_history,
)
from services.ai_models import send_prompt_to_model
from services.code_executor import run_code, submit_code


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

current_model = DEFAULT_MODEL

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


@app.get("/verify-email")
async def verify_email(token: str):
    """Verify a user's email address using the token sent by email."""
    return await verify_user_email(token)


@app.post("/resend-verification")
async def resend_verification(request: EmailRequest):
    """Resend a verification email to a user who hasn't verified their email yet."""
    return await resend_verification_email(request.email)


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


@app.patch("/me/profile")
async def update_profile(data: UpdateProfileRequest, token_data: dict = Depends(verify_token)):
    """Update the authenticated user's display name, bio, and/or avatar."""
    try:
        return await update_user_profile(token_data["user_id"], data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


# --- Quiz Stats Endpoints ---


@app.post("/save-quiz-result")
async def save_result(data: SaveQuizResultRequest, token_data: dict = Depends(verify_token)):
    """Save a completed quiz result for the authenticated user."""
    return await save_quiz_result(token_data["user_id"], data)


@app.get("/user-stats")
async def user_stats(token_data: dict = Depends(verify_token)):
    """Get aggregated statistics for the authenticated user."""
    return await get_user_stats(token_data["user_id"])


@app.get("/quiz-history")
async def quiz_history(token_data: dict = Depends(verify_token)):
    """Get the authenticated user's last 20 quiz sessions."""
    return await get_quiz_history(token_data["user_id"])


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


# --- Social / Friends Endpoints ---


@app.get("/users/search")
async def search_users_endpoint(q: str, token_data: dict = Depends(verify_token)):
    """Search for users by name or email."""
    return await search_users(q, token_data["user_id"])


@app.get("/users/{user_id}/profile")
async def get_user_public_profile(user_id: int, token_data: dict = Depends(verify_token)):
    """Get another user's public profile with friendship status."""
    return await get_public_profile(user_id, token_data["user_id"])


@app.get("/users/{user_id}/stats")
async def get_user_public_stats(user_id: int, token_data: dict = Depends(verify_token)):
    """Get another user's quiz statistics (friends only)."""
    return await get_user_stats_public(user_id, token_data["user_id"])


@app.post("/friends/request/{addressee_id}")
async def send_friend_request_endpoint(addressee_id: int, token_data: dict = Depends(verify_token)):
    """Send a friend request to another user."""
    return await send_friend_request(token_data["user_id"], addressee_id)


@app.post("/friends/respond")
async def respond_friend_request_endpoint(data: FriendRequestAction, token_data: dict = Depends(verify_token)):
    """Accept or reject a pending friend request."""
    return await respond_to_friend_request(token_data["user_id"], data)


@app.get("/friends/requests")
async def get_friend_requests_endpoint(token_data: dict = Depends(verify_token)):
    """Get all pending friend requests for the authenticated user."""
    return await get_friend_requests(token_data["user_id"])


@app.get("/friends")
async def get_friends_endpoint(token_data: dict = Depends(verify_token)):
    """Get the authenticated user's friends list."""
    return await get_friends_list(token_data["user_id"])


@app.delete("/friends/{friend_id}")
async def remove_friend_endpoint(friend_id: int, token_data: dict = Depends(verify_token)):
    """Remove a friend."""
    return await remove_friend(token_data["user_id"], friend_id)


@app.get("/friends/count")
async def friend_count_endpoint(token_data: dict = Depends(verify_token)):
    """Get the authenticated user's friend count."""
    return await get_friend_count(token_data["user_id"])


@app.get("/friends/requests/count")
async def pending_request_count_endpoint(token_data: dict = Depends(verify_token)):
    """Get the count of pending friend requests."""
    return await get_pending_request_count(token_data["user_id"])
