"""
Authentication module.
Handles JWT token creation, verification, and user authentication.
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
import bcrypt
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS

security = HTTPBearer()


def create_access_token(user_id: int, email: str) -> str:
    """
    Create a JWT access token for a user.

    Args:
        user_id (int): The user's ID.
        email (str): The user's email.

    Returns:
        str: Encoded JWT token.
    """
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify JWT token and return the payload.

    Args:
        credentials (HTTPAuthorizationCredentials): The HTTP bearer credentials.

    Returns:
        dict: Decoded token payload.

    Raises:
        HTTPException: If token is expired or invalid.
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password (str): The plain text password.

    Returns:
        str: The hashed password.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        password (str): The plain text password.
        password_hash (str): The hashed password.

    Returns:
        bool: True if password matches, False otherwise.
    """
    return bcrypt.checkpw(password.encode(), password_hash.encode())
