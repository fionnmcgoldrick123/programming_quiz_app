"""
Configuration module for the application.
Contains environment variables, constants, and prompt guides.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# App / email verification configuration
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME or "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}

# Set to True to require users to verify their email before logging in.
# Set to False (default) to skip email verification entirely.
REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() in {"1", "true", "yes", "on"}

# CORS Origins
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]

# Prompt Guide Files
PROMPT_GUIDE_FILE = "./prompt_guide.txt"
CODING_PROMPT_GUIDE_FILE = "./coding_prompt_guide.txt"


# Load Prompt Guides
def load_prompt_guides():
    """Load quiz format guides from files."""
    with open(PROMPT_GUIDE_FILE, "r", encoding="utf-8") as file:
        quiz_format_guide = file.read()

    with open(CODING_PROMPT_GUIDE_FILE, "r", encoding="utf-8") as file:
        coding_format_guide = file.read()

    return quiz_format_guide, coding_format_guide


QUIZ_FORMAT_GUIDE, CODING_FORMAT_GUIDE = load_prompt_guides()

# Model Configuration
DEFAULT_MODEL = "openai"
SUPPORTED_MODELS = ["openai", "llama3.1:8b"]
