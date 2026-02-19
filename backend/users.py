"""
User management module.
Handles user registration, authentication, profile management, and XP/leveling system.
"""

from fastapi import HTTPException
from db import get_connection
from auth import hash_password, verify_password, create_access_token
from pydantic_models import RegisterRequest, LoginRequest


async def user_exists(email: str) -> bool:
    """
    Check if a user with the given email already exists in the database.

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
                (email,),
            )
            return cur.fetchone() is not None


async def register_user(user_data: RegisterRequest):
    """
    Register a new user by inserting their data into the database.

    Args:
        user_data (RegisterRequest): The registration request object containing user details.

    Returns:
        dict: A success message or an error if the user already exists.
    """
    # Check if user already exists
    if await user_exists(user_data.email):
        return {"error": "User already exists"}

    # Hash the user's password using bcrypt before storing it
    password_hash_value = hash_password(user_data.password)

    # Connect to the database and use a cursor to execute the insert statement
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users(first_name, second_name, email, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (user_data.first_name, user_data.second_name, user_data.email, password_hash_value),
            )
            new_user_id = cur.fetchone()["id"]
            print(f"New user registered with ID: {new_user_id}")
            return {"message": "User registered successfully", "user_id": new_user_id}


async def login_user(login_data: LoginRequest):
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
                (login_data.email,),
            )
            user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
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
            "xp_required": xp_for_level(user["level"]),
            "created_at": user["created_at"].isoformat() if user["created_at"] else None,
            "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None,
        },
    }


async def get_user_profile(user_id: int):
    """
    Get a user's profile data.

    Args:
        user_id (int): The user's ID.

    Returns:
        dict: User profile data.

    Raises:
        HTTPException: If user not found.
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
                (user_id,),
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
        "xp_required": xp_for_level(user["level"]),
        "created_at": user["created_at"].isoformat() if user["created_at"] else None,
        "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None,
    }


def xp_for_level(level: int) -> int:
    """
    Calculate XP required to advance from the given level.

    Args:
        level (int): The current level.

    Returns:
        int: XP required to reach the next level.
    """
    return 100 * level  # Level 1: 100, Level 2: 200, Level 3: 300 ...


async def add_user_xp(user_id: int, xp_amount: int):
    """
    Add XP to the user's account. XP is tracked per-level and resets to 0 on level-up.

    Args:
        user_id (int): The user's ID.
        xp_amount (int): The amount of XP to add.

    Returns:
        dict: Updated user data with new XP, level, and leveled_up flag.

    Raises:
        HTTPException: If user not found.
    """
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
                (user_id,),
            )
            user = cur.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            current_exp = user["exp"] or 0
            current_level = user["level"] or 1

            new_exp = current_exp + xp_amount
            new_level = current_level
            leveled_up = False

            # Level up: check if XP exceeds the threshold for current level
            xp_needed = xp_for_level(new_level)
            while new_exp >= xp_needed:
                new_exp -= xp_needed
                new_level += 1
                leveled_up = True
                xp_needed = xp_for_level(new_level)

            # Update user's XP and level in the database
            cur.execute(
                """
                UPDATE users
                SET exp = %s, level = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, first_name, second_name, email, exp, level, created_at, updated_at;
                """,
                (new_exp, new_level, user_id),
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
        "xp_required": xp_for_level(updated_user["level"]),
        "created_at": updated_user["created_at"].isoformat() if updated_user["created_at"] else None,
        "updated_at": updated_user["updated_at"].isoformat() if updated_user["updated_at"] else None,
        "xp_gained": xp_amount,
        "leveled_up": leveled_up,
        "new_level": new_level if leveled_up else None,
    }
