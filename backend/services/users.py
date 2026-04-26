"""
User management module.
Handles user registration, authentication, profile management, and XP/leveling system.
"""

from datetime import datetime
from email.message import EmailMessage
import secrets
import smtplib
import ssl
from urllib.parse import quote

from fastapi import HTTPException
from db import get_connection
from core.auth import hash_password, verify_password, create_access_token
from config import (
    APP_BASE_URL,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_TLS,
    REQUIRE_EMAIL_VERIFICATION,
)
from pydantic_models import RegisterRequest, LoginRequest, SaveQuizResultRequest, FriendRequestAction, UpdateProfileRequest


async def user_exists(email: str) -> bool:
    """
    Check if a user with the given email already exists in the database.

    Args:
        email (str): The email address to check.

    Returns:
        bool: True if the user exists, False otherwise.
    """
    normalized_email = email.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM users
                WHERE email = %s
                LIMIT 1;
                """,
                (normalized_email,),
            )
            return cur.fetchone() is not None


def _build_verification_link(token: str) -> str:
    return f"{APP_BASE_URL.rstrip('/')}/verify-email?token={quote(token)}"


def _send_verification_email(email: str, full_name: str, verification_link: str) -> bool:
    if not SMTP_HOST or not SMTP_FROM or not SMTP_USERNAME or not SMTP_PASSWORD:
        return False

    message = EmailMessage()
    message["Subject"] = "Verify your CodeQuiz account"
    message["From"] = SMTP_FROM
    message["To"] = email
    message.set_content(
        f"""Hello {full_name},

Please verify your CodeQuiz account by opening this link:

{verification_link}

If you did not create this account, you can ignore this email.
"""
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_USE_TLS:
            server.starttls(context=context)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)

    return True


async def register_user(user_data: RegisterRequest):
    """
    Register a new user by inserting their data into the database.

    Args:
        user_data (RegisterRequest): The registration request object containing user details.

    Returns:
        dict: A success message or an error if the user already exists.
    """
    # Check if user already exists
    normalized_email = user_data.email.strip().lower()

    if await user_exists(normalized_email):
        return {"error": "User already exists"}

    password_hash_value = hash_password(user_data.password)
    verification_token = secrets.token_urlsafe(32)
    verification_link = _build_verification_link(verification_token)
    verification_sent_at = datetime.utcnow()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users(first_name, second_name, email, password_hash, email_verified, verification_token, verification_sent_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    user_data.first_name,
                    user_data.second_name,
                    normalized_email,
                    password_hash_value,
                    not REQUIRE_EMAIL_VERIFICATION,
                    verification_token,
                    verification_sent_at,
                ),
            )
            new_user_id = cur.fetchone()["id"]

            email_sent = False
            verification_note = "Please verify your email before logging in."
            try:
                email_sent = _send_verification_email(
                    normalized_email,
                    f"{user_data.first_name} {user_data.second_name}".strip(),
                    verification_link,
                )
            except Exception:
                email_sent = False
                verification_note = (
                    "We could not deliver the verification email automatically. "
                    "Use the verification link below, or check your email settings."
                )

            conn.commit()

            response = {
                "message": "User registered successfully. Please verify your email before logging in.",
                "user_id": new_user_id,
                "verification_email_sent": email_sent,
                "verification_link": verification_link,
                "verification_note": verification_note,
            }
            return response


async def login_user(login_data: LoginRequest):
    """
    Authenticate a user and return a JWT token.

    Args:
        login_data (LoginRequest): The login request containing email and password.

    Returns:
        dict: JWT token and user data or an error message.
    """
    normalized_email = login_data.email.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, second_name, email, password_hash, exp, level,
                       display_name, bio, avatar_url, created_at, updated_at,
                       email_verified, verified_at
                FROM users
                WHERE email = %s
                LIMIT 1;
                """,
                (normalized_email,),
            )
            user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if REQUIRE_EMAIL_VERIFICATION and not user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email address before logging in")

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
            "display_name": user["display_name"],
            "bio": user["bio"],
            "avatar_url": user["avatar_url"],
            "email_verified": user.get("email_verified", False),
            "verified_at": user["verified_at"].isoformat() if user.get("verified_at") else None,
            "created_at": (
                user["created_at"].isoformat() if user["created_at"] else None
            ),
            "updated_at": (
                user["updated_at"].isoformat() if user["updated_at"] else None
            ),
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
                  SELECT id, first_name, second_name, email, exp, level,
                      display_name, bio, avatar_url, created_at, updated_at,
                      email_verified, verified_at
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
        "display_name": user["display_name"],
        "bio": user["bio"],
        "avatar_url": user["avatar_url"],
        "email_verified": user.get("email_verified", False),
        "verified_at": user["verified_at"].isoformat() if user.get("verified_at") else None,
        "created_at": user["created_at"].isoformat() if user["created_at"] else None,
        "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None,
    }


async def verify_user_email(token: str):
    """Mark a user's email as verified from a verification token."""
    if not token:
        raise HTTPException(status_code=400, detail="Verification token is required")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET email_verified = TRUE,
                    verification_token = NULL,
                    verification_sent_at = NULL,
                    verified_at = NOW(),
                    updated_at = NOW()
                WHERE verification_token = %s
                  AND email_verified = FALSE
                  AND verification_sent_at > NOW() - INTERVAL '24 hours'
                RETURNING id, email;
                """,
                (token,),
            )
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=400, detail="Invalid or expired verification link")
            conn.commit()

    return {
        "message": "Email verified successfully",
        "user_id": user["id"],
        "email": user["email"],
    }


async def resend_verification_email(email: str):
    """Resend the verification email to a user who hasn't verified yet."""
    normalized_email = email.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, second_name, email, email_verified, verification_token, verification_sent_at
                FROM users
                WHERE email = %s
                LIMIT 1;
                """,
                (normalized_email,),
            )
            user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("email_verified"):
        raise HTTPException(status_code=400, detail="This email is already verified")

    # Generate a new verification token
    verification_token = secrets.token_urlsafe(32)
    verification_link = _build_verification_link(verification_token)
    verification_sent_at = datetime.utcnow()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET verification_token = %s,
                    verification_sent_at = %s,
                    updated_at = NOW()
                WHERE email = %s
                RETURNING id;
                """,
                (verification_token, verification_sent_at, normalized_email),
            )
            updated_user = cur.fetchone()
            conn.commit()

    email_sent = False
    verification_note = "Please check your email for the verification link."
    try:
        email_sent = _send_verification_email(
            normalized_email,
            f"{user['first_name']} {user['second_name']}".strip(),
            verification_link,
        )
    except Exception:
        email_sent = False
        verification_note = (
            "We could not deliver the verification email automatically. "
            "Use the verification link below, or check your email settings."
        )

    return {
        "message": "Verification email sent successfully",
        "user_id": updated_user["id"],
        "email": normalized_email,
        "verification_email_sent": email_sent,
        "verification_link": verification_link,
        "verification_note": verification_note,
    }


async def update_user_profile(user_id: int, data: UpdateProfileRequest):
    """Update a user's display name, bio, and/or avatar."""
    fields = []
    values = []

    if data.display_name is not None:
        fields.append("display_name = %s")
        values.append(data.display_name)
    if data.bio is not None:
        fields.append("bio = %s")
        values.append(data.bio)
    if data.avatar_url is not None:
        fields.append("avatar_url = %s")
        values.append(data.avatar_url)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    fields.append("updated_at = NOW()")
    values.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE users
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id, first_name, second_name, email, exp, level,
                          display_name, bio, avatar_url, created_at, updated_at;
                """,
                values,
            )
            updated = cur.fetchone()
            if not updated:
                raise HTTPException(status_code=404, detail="User not found")
            conn.commit()

    return {
        "id": updated["id"],
        "first_name": updated["first_name"],
        "second_name": updated["second_name"],
        "email": updated["email"],
        "exp": updated["exp"],
        "level": updated["level"],
        "xp_required": xp_for_level(updated["level"]),
        "display_name": updated["display_name"],
        "bio": updated["bio"],
        "avatar_url": updated["avatar_url"],
        "created_at": updated["created_at"].isoformat() if updated["created_at"] else None,
        "updated_at": updated["updated_at"].isoformat() if updated["updated_at"] else None,
    }


def xp_for_level(level: int) -> int:
    """Calculate XP required to advance from the given level."""
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
            # Retrieve current XP and level
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

            # Persist updated XP and level
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
        "created_at": (
            updated_user["created_at"].isoformat()
            if updated_user["created_at"]
            else None
        ),
        "updated_at": (
            updated_user["updated_at"].isoformat()
            if updated_user["updated_at"]
            else None
        ),
        "xp_gained": xp_amount,
        "leveled_up": leveled_up,
        "new_level": new_level if leveled_up else None,
    }


def _ensure_users_table():
    """Create the users table if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    first_name VARCHAR(100) NOT NULL,
                    second_name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    exp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    display_name VARCHAR(30) DEFAULT NULL,
                    bio VARCHAR(300) DEFAULT NULL,
                    avatar_url TEXT DEFAULT NULL,
                    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    verification_token TEXT DEFAULT NULL,
                    verification_sent_at TIMESTAMP DEFAULT NULL,
                    verified_at TIMESTAMP DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
            # Migrations for existing tables that pre-date these columns
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(30) DEFAULT NULL;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio VARCHAR(300) DEFAULT NULL;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT DEFAULT NULL;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token TEXT DEFAULT NULL;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_sent_at TIMESTAMP DEFAULT NULL;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP DEFAULT NULL;")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token);")
            conn.commit()


def _ensure_quiz_results_table():
    """Create the quiz_results table if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_results (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    quiz_type VARCHAR(10) NOT NULL,
                    total_questions INTEGER NOT NULL,
                    correct_answers INTEGER NOT NULL DEFAULT 0,
                    tags TEXT[] DEFAULT '{}',
                    language VARCHAR(50),
                    prompt TEXT,
                    completed_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
            cur.execute(
                "ALTER TABLE quiz_results ADD COLUMN IF NOT EXISTS prompt TEXT;"
            )
            conn.commit()


def _ensure_friendships_table():
    """Create the friendships table if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS friendships (
                    id SERIAL PRIMARY KEY,
                    requester_id INTEGER NOT NULL REFERENCES users(id),
                    addressee_id INTEGER NOT NULL REFERENCES users(id),
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(requester_id, addressee_id),
                    CHECK (requester_id != addressee_id)
                );
                """
            )
            conn.commit()


def _ensure_quiz_sessions_table():
    """Create the quiz_sessions table if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    topic VARCHAR(255) NOT NULL,
                    language VARCHAR(50),
                    quiz_type VARCHAR(20) NOT NULL,
                    questions JSONB NOT NULL,
                    score INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
            conn.commit()


def init_db():
    """Initialise all database tables in dependency order."""
    _ensure_users_table()
    _ensure_quiz_results_table()
    _ensure_friendships_table()
    _ensure_quiz_sessions_table()


async def save_quiz_session(user_id: int, topic: str, language: str, quiz_type: str, questions: list, score: int):
    """
    Save a completed quiz session for the user.
    
    Args:
        user_id (int): The user's ID.
        topic (str): The quiz topic.
        language (str): Programming language (for coding quizzes).
        quiz_type (str): Type of quiz ('mcq' or 'coding').
        questions (list): List of questions in the session (stored as JSONB).
        score (int): User's score (number of correct answers).
    
    Returns:
        dict: Confirmation message with session ID.
    """
    import json
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO quiz_sessions (user_id, topic, language, quiz_type, questions, score)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    user_id,
                    topic,
                    language,
                    quiz_type,
                    json.dumps(questions),
                    score,
                ),
            )
            result = cur.fetchone()
            conn.commit()
    return {"message": "Quiz session saved", "session_id": result["id"]}


async def get_quiz_history(user_id: int):
    """
    Get the last 20 quiz sessions for a user.
    
    Args:
        user_id (int): The user's ID.
    
    Returns:
        list: List of quiz sessions with their details.
    """
    import json
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, topic, language, quiz_type, questions, score, created_at
                FROM quiz_sessions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 20;
                """,
                (user_id,),
            )
            sessions = cur.fetchall()
    
    return [
        {
            "id": s["id"],
            "topic": s["topic"],
            "language": s["language"],
            "quiz_type": s["quiz_type"],
            "questions": s["questions"] if isinstance(s["questions"], list) else json.loads(s["questions"]),
            "score": s["score"],
            "created_at": s["created_at"].isoformat() if s["created_at"] else None,
        }
        for s in sessions
    ]


async def save_quiz_result(user_id: int, data: SaveQuizResultRequest):
    """Save a completed quiz result for the user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO quiz_results (user_id, quiz_type, total_questions, correct_answers, tags, language, prompt)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    user_id,
                    data.quiz_type,
                    data.total_questions,
                    data.correct_answers,
                    data.tags,
                    data.language,
                    data.prompt,
                ),
            )
            result = cur.fetchone()
            conn.commit()
    return {"message": "Quiz result saved", "id": result["id"]}


async def get_user_stats(user_id: int):
    """Return aggregated statistics for a user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Overview counts
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_quizzes,
                    COALESCE(SUM(total_questions), 0) AS total_questions,
                    COALESCE(SUM(correct_answers), 0) AS total_correct,
                    COALESCE(SUM(total_questions) - SUM(correct_answers), 0) AS total_wrong,
                    COUNT(*) FILTER (WHERE quiz_type = 'mcq') AS mcq_quizzes,
                    COUNT(*) FILTER (WHERE quiz_type = 'coding') AS coding_quizzes
                FROM quiz_results
                WHERE user_id = %s;
                """,
                (user_id,),
            )
            overview = cur.fetchone()

            # Tag breakdown – unnest the tags array and count
            cur.execute(
                """
                SELECT tag, COUNT(*) AS count
                FROM (
                    SELECT unnest(tags) AS tag
                    FROM quiz_results
                    WHERE user_id = %s
                ) t
                GROUP BY tag
                ORDER BY count DESC
                LIMIT 15;
                """,
                (user_id,),
            )
            tag_rows = cur.fetchall()

            # Language breakdown (coding quizzes only)
            cur.execute(
                """
                SELECT language, COUNT(*) AS count
                FROM quiz_results
                WHERE user_id = %s AND quiz_type = 'coding' AND language IS NOT NULL
                GROUP BY language
                ORDER BY count DESC;
                """,
                (user_id,),
            )
            lang_rows = cur.fetchall()

            # Recent activity – last 10 quizzes
            cur.execute(
                """
                SELECT quiz_type, total_questions, correct_answers, tags, language, prompt, completed_at
                FROM quiz_results
                WHERE user_id = %s
                ORDER BY completed_at DESC
                LIMIT 10;
                """,
                (user_id,),
            )
            recent_rows = cur.fetchall()

    recent = []
    for r in recent_rows:
        recent.append(
            {
                "quiz_type": r["quiz_type"],
                "total_questions": r["total_questions"],
                "correct_answers": r["correct_answers"],
                "tags": r["tags"] or [],
                "language": r["language"],
                "prompt": r["prompt"],
                "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            }
        )

    return {
        "total_quizzes": overview["total_quizzes"],
        "total_questions": overview["total_questions"],
        "total_correct": overview["total_correct"],
        "total_wrong": overview["total_wrong"],
        "mcq_quizzes": overview["mcq_quizzes"],
        "coding_quizzes": overview["coding_quizzes"],
        "accuracy": round(overview["total_correct"] / overview["total_questions"] * 100, 1) if overview["total_questions"] else 0,
        "tags": [{"name": r["tag"], "count": r["count"]} for r in tag_rows],
        "languages": [{"name": r["language"], "count": r["count"]} for r in lang_rows],
        "recent": recent,
    }


async def search_users(query: str, current_user_id: int):
    """Search users by name or email, excluding the current user."""
    search_term = f"%{query}%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, second_name, email, level, exp,
                       display_name, avatar_url, created_at
                FROM users
                WHERE id != %s
                  AND (
                    LOWER(first_name) LIKE LOWER(%s)
                    OR LOWER(second_name) LIKE LOWER(%s)
                    OR LOWER(email) LIKE LOWER(%s)
                    OR LOWER(first_name || ' ' || second_name) LIKE LOWER(%s)
                  )
                ORDER BY first_name, second_name
                LIMIT 20;
                """,
                (current_user_id, search_term, search_term, search_term, search_term),
            )
            users = cur.fetchall()

    return [
        {
            "id": u["id"],
            "first_name": u["first_name"],
            "second_name": u["second_name"],
            "email": u["email"],
            "level": u["level"],
            "exp": u["exp"],
            "display_name": u["display_name"],
            "avatar_url": u["avatar_url"],
            "created_at": u["created_at"].isoformat() if u["created_at"] else None,
        }
        for u in users
    ]


async def get_public_profile(target_user_id: int, current_user_id: int):
    """Get a user's public profile with friendship status."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, second_name, email, level, exp,
                       display_name, bio, avatar_url, created_at
                FROM users
                WHERE id = %s;
                """,
                (target_user_id,),
            )
            user = cur.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Check friendship status between current user and target
            cur.execute(
                """
                SELECT id, requester_id, addressee_id, status
                FROM friendships
                WHERE (requester_id = %s AND addressee_id = %s)
                   OR (requester_id = %s AND addressee_id = %s)
                LIMIT 1;
                """,
                (current_user_id, target_user_id, target_user_id, current_user_id),
            )
            friendship = cur.fetchone()

            # Count friends for the target user
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM friendships
                WHERE status = 'accepted'
                  AND (requester_id = %s OR addressee_id = %s);
                """,
                (target_user_id, target_user_id),
            )
            friend_count = cur.fetchone()["count"]

    friendship_status = "none"
    if friendship:
        if friendship["status"] == "accepted":
            friendship_status = "friends"
        elif friendship["status"] == "pending":
            if friendship["requester_id"] == current_user_id:
                friendship_status = "request_sent"
            else:
                friendship_status = "request_received"

    return {
        "id": user["id"],
        "first_name": user["first_name"],
        "second_name": user["second_name"],
        "email": user["email"],
        "level": user["level"],
        "exp": user["exp"],
        "xp_required": xp_for_level(user["level"]),
        "display_name": user["display_name"],
        "bio": user["bio"],
        "avatar_url": user["avatar_url"],
        "created_at": user["created_at"].isoformat() if user["created_at"] else None,
        "friendship_status": friendship_status,
        "friend_count": friend_count,
    }


async def send_friend_request(requester_id: int, addressee_id: int):
    """Send a friend request from requester to addressee."""
    if requester_id == addressee_id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check if target user exists
            cur.execute("SELECT id FROM users WHERE id = %s;", (addressee_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found")

            # Check for existing friendship/request in either direction
            cur.execute(
                """
                SELECT id, status, requester_id
                FROM friendships
                WHERE (requester_id = %s AND addressee_id = %s)
                   OR (requester_id = %s AND addressee_id = %s);
                """,
                (requester_id, addressee_id, addressee_id, requester_id),
            )
            existing = cur.fetchone()

            if existing:
                if existing["status"] == "accepted":
                    raise HTTPException(status_code=400, detail="Already friends")
                if existing["status"] == "pending":
                    if existing["requester_id"] == requester_id:
                        raise HTTPException(status_code=400, detail="Friend request already sent")
                    # The other person already sent us a request — auto-accept
                    cur.execute(
                        """
                        UPDATE friendships
                        SET status = 'accepted', updated_at = NOW()
                        WHERE id = %s;
                        """,
                        (existing["id"],),
                    )
                    conn.commit()
                    return {"message": "Friend request accepted (they had already requested you)"}

            cur.execute(
                """
                INSERT INTO friendships (requester_id, addressee_id, status)
                VALUES (%s, %s, 'pending');
                """,
                (requester_id, addressee_id),
            )
            conn.commit()

    return {"message": "Friend request sent"}


async def respond_to_friend_request(user_id: int, data: FriendRequestAction):
    """Accept or reject a pending friend request."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, requester_id, addressee_id, status
                FROM friendships
                WHERE id = %s AND addressee_id = %s AND status = 'pending';
                """,
                (data.friendship_id, user_id),
            )
            friendship = cur.fetchone()

            if not friendship:
                raise HTTPException(status_code=404, detail="Friend request not found")

            if data.action == "accept":
                cur.execute(
                    "UPDATE friendships SET status = 'accepted', updated_at = NOW() WHERE id = %s;",
                    (friendship["id"],),
                )
                conn.commit()
                return {"message": "Friend request accepted"}
            elif data.action == "reject":
                cur.execute("DELETE FROM friendships WHERE id = %s;", (friendship["id"],))
                conn.commit()
                return {"message": "Friend request rejected"}
            else:
                raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'")


async def get_friend_requests(user_id: int):
    """Get pending friend requests received by the user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.id AS friendship_id, f.created_at,
                       u.id AS user_id, u.first_name, u.second_name, u.email, u.level, u.exp
                FROM friendships f
                JOIN users u ON u.id = f.requester_id
                WHERE f.addressee_id = %s AND f.status = 'pending'
                ORDER BY f.created_at DESC;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    return [
        {
            "friendship_id": r["friendship_id"],
            "user_id": r["user_id"],
            "first_name": r["first_name"],
            "second_name": r["second_name"],
            "email": r["email"],
            "level": r["level"],
            "exp": r["exp"],
            "sent_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def get_friends_list(user_id: int):
    """Get all accepted friends for a user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.first_name, u.second_name, u.email, u.level, u.exp, u.created_at,
                       f.created_at AS friends_since
                FROM friendships f
                JOIN users u ON (
                    CASE WHEN f.requester_id = %s THEN u.id = f.addressee_id
                         ELSE u.id = f.requester_id END
                )
                WHERE f.status = 'accepted'
                  AND (f.requester_id = %s OR f.addressee_id = %s)
                ORDER BY u.first_name, u.second_name;
                """,
                (user_id, user_id, user_id),
            )
            rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "first_name": r["first_name"],
            "second_name": r["second_name"],
            "email": r["email"],
            "level": r["level"],
            "exp": r["exp"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "friends_since": r["friends_since"].isoformat() if r["friends_since"] else None,
        }
        for r in rows
    ]


async def remove_friend(user_id: int, friend_id: int):
    """Remove a friendship between two users."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM friendships
                WHERE status = 'accepted'
                  AND ((requester_id = %s AND addressee_id = %s)
                    OR (requester_id = %s AND addressee_id = %s));
                """,
                (user_id, friend_id, friend_id, user_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Friendship not found")
            conn.commit()

    return {"message": "Friend removed"}


async def get_friend_count(user_id: int):
    """Get the number of accepted friends for a user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM friendships
                WHERE status = 'accepted'
                  AND (requester_id = %s OR addressee_id = %s);
                """,
                (user_id, user_id),
            )
            return {"friend_count": cur.fetchone()["count"]}


async def get_pending_request_count(user_id: int):
    """Get the number of pending friend requests for the user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM friendships
                WHERE addressee_id = %s AND status = 'pending';
                """,
                (user_id,),
            )
            return {"pending_count": cur.fetchone()["count"]}


async def get_user_stats_public(user_id: int, current_user_id: int):
    """Return stats for a user — only accessible by accepted friends."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found")

            cur.execute(
                """
                SELECT 1 FROM friendships
                WHERE status = 'accepted'
                  AND ((requester_id = %s AND addressee_id = %s)
                    OR (requester_id = %s AND addressee_id = %s));
                """,
                (current_user_id, user_id, user_id, current_user_id),
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=403,
                    detail="You must be friends to view this user's statistics",
                )

    return await get_user_stats(user_id)
