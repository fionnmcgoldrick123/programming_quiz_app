from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import os
import httpx
import subprocess
import tempfile
import json as json_module
import sys
from db import get_connection
import bcrypt
import jwt
from datetime import datetime, timedelta
import json
from pydantic_models import PromptRequest, RegisterRequest, ModelRequest, LoginRequest, UserResponse, AddXpRequest, CodingQuestionSchema, RunCodeRequest, SubmitCodeRequest
from parsers.parser_openai import openai_parser, openai_coding_parser
from parsers.parser_ollama import ollama_parser, ollama_coding_parser

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
coding_prompt_guide_file = "./coding_prompt_guide.txt"

current_model = "openai"

# Reads through 'prompt_guide.txt' and stores it inside QUIZ_FORMAT_GUIDE
with open(prompt_guide_file, "r", encoding="utf-8") as file:
    # This variable stores a string. A set of rules that is sent with the users prompt to the AI model. 
    QUIZ_FORMAT_GUIDE = file.read()

# Reads through 'coding_prompt_guide.txt' for coding quiz generation
with open(coding_prompt_guide_file, "r", encoding="utf-8") as file:
    CODING_FORMAT_GUIDE = file.read()


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
    is_coding = prompt.quiz_type == "coding"
    guide = CODING_FORMAT_GUIDE if is_coding else QUIZ_FORMAT_GUIDE
    
    prompt_request = guide + " \n"
    if prompt.num_questions:
        prompt_request += f"Generate exactly {prompt.num_questions} questions. \n"
    if is_coding and prompt.language:
        prompt_request += f"The programming language is {prompt.language}. \n"
    prompt_request += prompt.prompt
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_content = "you are a coding challenge generation assistant" if is_coding else "you are a quiz generation assistant"
    
    payload  = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt_request}
        ]
    }
    
    timeout = httpx.Timeout(120.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout = timeout) as client: 
        response = await client.post(url, headers=headers, json=payload)
        
    print(response.json())
    
    # Use the appropriate parser based on quiz type
    if is_coding:
        parsed_quiz = openai_coding_parser(response.json())
    else:
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
    is_coding = prompt.quiz_type == "coding"
    guide = CODING_FORMAT_GUIDE if is_coding else QUIZ_FORMAT_GUIDE
    
    prompt_request = guide + " \n"
    if prompt.num_questions:
        prompt_request += f"Generate exactly {prompt.num_questions} questions. \n"
    if is_coding and prompt.language:
        prompt_request += f"The programming language is {prompt.language}. \n"
    prompt_request += prompt.prompt
    
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
    if is_coding:
        parsed_quiz = ollama_coding_parser(response.json())
    else:
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
            "xp_required": xp_for_level(user["level"]),
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
        "xp_required": xp_for_level(user["level"]),
        "created_at": user["created_at"].isoformat() if user["created_at"] else None,
        "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None
    }

# --- XP Helper ---

def xp_for_level(level: int) -> int:
    """XP required to advance from the given level. Scales each level."""
    return 100 * level  # Level 1: 100, Level 2: 200, Level 3: 300 ...

# --- Add XP Endpoint ---

@app.post("/add-xp")
async def add_xp(xp_data: AddXpRequest, token_data: dict = Depends(verify_token)):
    """
    Add XP to the authenticated user's account.
    XP is tracked per-level and resets to 0 on level-up.
    
    Args:
        xp_data (AddXpRequest): The XP amount to add.
        token_data (dict): The decoded JWT token data.
        
    Returns:
        dict: Updated user data with new XP, level, and leveled_up flag.
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
            
            new_exp = current_exp + xp_to_add
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
        "xp_required": xp_for_level(updated_user["level"]),
        "created_at": updated_user["created_at"].isoformat() if updated_user["created_at"] else None,
        "updated_at": updated_user["updated_at"].isoformat() if updated_user["updated_at"] else None,
        "xp_gained": xp_to_add,
        "leveled_up": leveled_up,
        "new_level": new_level if leveled_up else None
    }


# --- Code Execution Endpoints ---

@app.post("/run-code")
async def run_code(request: RunCodeRequest):
    """
    Execute code and return the output or error.
    
    Args:
        request (RunCodeRequest): Contains code and language.
        
    Returns:
        dict: Execution result with output or error.
    """
    try:
        result = await execute_code(request.code, request.language)
        return result
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }


@app.post("/submit-code")
async def submit_code(request: SubmitCodeRequest):
    """
    Execute code against test cases and return results.
    
    Args:
        request (SubmitCodeRequest): Contains code, language, and test cases.
        
    Returns:
        dict: Test results with pass/fail status for each test case.
    """
    try:
        # Parse test cases
        test_results = []
        all_passed = True
        
        for i, test_case_str in enumerate(request.test_cases):
            try:
                # Parse the JSON test case
                test_case = json_module.loads(test_case_str)
                input_data = test_case.get("input", {})
                expected = test_case.get("expected")
                
                # Execute the code with test input
                result = await execute_code_with_test(
                    request.code, 
                    request.language, 
                    input_data, 
                    expected
                )
                
                test_results.append({
                    "test_number": i + 1,
                    "input": input_data,
                    "expected": expected,
                    "actual": result.get("actual"),
                    "passed": result.get("passed", False),
                    "error": result.get("error")
                })
                
                if not result.get("passed", False):
                    all_passed = False
                    
            except json_module.JSONDecodeError as e:
                test_results.append({
                    "test_number": i + 1,
                    "passed": False,
                    "error": f"Invalid test case format: {str(e)}"
                })
                all_passed = False
        
        return {
            "success": all_passed,
            "test_results": test_results,
            "message": "All tests passed!" if all_passed else "Some tests failed."
        }
        
    except Exception as e:
        return {
            "success": False,
            "test_results": [],
            "error": str(e)
        }


async def execute_code(code: str, language: str):
    """
    Execute code and capture output/errors.
    
    Args:
        code (str): The code to execute.
        language (str): The programming language.
        
    Returns:
        dict: Execution result.
    """
    lang = language.lower()
    
    try:
        if lang == "python":
            return await execute_python(code)
        elif lang in ["javascript", "typescript"]:
            return await execute_javascript(code)
        else:
            return {
                "success": False,
                "output": "",
                "error": f"Language '{language}' is not supported yet. Supported: Python, JavaScript"
            }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }


async def execute_python(code: str):
    """Execute Python code."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        success = result.returncode == 0
        output = result.stdout
        error = result.stderr
        
        return {
            "success": success,
            "output": output,
            "error": error if error else None
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Execution timed out (5 seconds limit)"
        }
    finally:
        os.unlink(temp_file)


async def execute_javascript(code: str):
    """Execute JavaScript code using Node.js."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            ['node', temp_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        success = result.returncode == 0
        output = result.stdout
        error = result.stderr
        
        return {
            "success": success,
            "output": output,
            "error": error if error else None
        }
    except FileNotFoundError:
        return {
            "success": False,
            "output": "",
            "error": "Node.js is not installed or not in PATH"
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Execution timed out (5 seconds limit)"
        }
    finally:
        os.unlink(temp_file)


async def execute_code_with_test(code: str, language: str, input_data: dict, expected):
    """
    Execute code with specific test inputs and compare with expected output.
    
    Args:
        code (str): The user's code.
        language (str): Programming language.
        input_data (dict): Dictionary of parameter names to values.
        expected: Expected return value.
        
    Returns:
        dict: Test result with actual output and pass/fail status.
    """
    lang = language.lower()
    
    try:
        if lang == "python":
            return await execute_python_test(code, input_data, expected)
        elif lang in ["javascript", "typescript"]:
            return await execute_javascript_test(code, input_data, expected)
        else:
            return {
                "passed": False,
                "error": f"Language '{language}' not supported for testing"
            }
    except Exception as e:
        return {
            "passed": False,
            "error": str(e)
        }


async def execute_python_test(code: str, input_data: dict, expected):
    """Execute Python code with test inputs."""
    # Extract function name from code (basic implementation)
    import re
    func_match = re.search(r'def\s+(\w+)\s*\(', code)
    if not func_match:
        return {
            "passed": False,
            "error": "Could not find function definition in code"
        }
    
    func_name = func_match.group(1)
    
    # Build test code
    test_code = f"""{code}

# Test execution
import json
try:
    result = {func_name}({', '.join(f'{k}={json.dumps(v)}' for k, v in input_data.items())})
    print("__RESULT__:", json.dumps(result))
except Exception as e:
    print("__ERROR__:", str(e))
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(test_code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout
        
        # Parse result
        if "__RESULT__:" in output:
            result_line = [line for line in output.split('\n') if "__RESULT__:" in line][0]
            actual_str = result_line.split("__RESULT__:")[1].strip()
            actual = json_module.loads(actual_str)
            passed = actual == expected
            
            return {
                "passed": passed,
                "actual": actual,
                "error": None
            }
        elif "__ERROR__:" in output:
            error_line = [line for line in output.split('\n') if "__ERROR__:" in line][0]
            error_msg = error_line.split("__ERROR__:")[1].strip()
            return {
                "passed": False,
                "actual": None,
                "error": error_msg
            }
        else:
            return {
                "passed": False,
                "actual": None,
                "error": result.stderr if result.stderr else "No output produced"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "actual": None,
            "error": "Execution timed out (5 seconds limit)"
        }
    finally:
        os.unlink(temp_file)


async def execute_javascript_test(code: str, input_data: dict, expected):
    """Execute JavaScript code with test inputs."""
    import re
    func_match = re.search(r'function\s+(\w+)\s*\(', code)
    if not func_match:
        return {
            "passed": False,
            "error": "Could not find function definition in code"
        }
    
    func_name = func_match.group(1)
    
    # Build test code
    args_str = ', '.join(json_module.dumps(v) for v in input_data.values())
    test_code = f"""{code}

// Test execution
try {{
    const result = {func_name}({args_str});
    console.log("__RESULT__:", JSON.stringify(result));
}} catch (e) {{
    console.log("__ERROR__:", e.message);
}}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(test_code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            ['node', temp_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout
        
        # Parse result
        if "__RESULT__:" in output:
            result_line = [line for line in output.split('\n') if "__RESULT__:" in line][0]
            actual_str = result_line.split("__RESULT__:")[1].strip()
            actual = json_module.loads(actual_str)
            passed = actual == expected
            
            return {
                "passed": passed,
                "actual": actual,
                "error": None
            }
        elif "__ERROR__:" in output:
            error_line = [line for line in output.split('\n') if "__ERROR__:" in line][0]
            error_msg = error_line.split("__ERROR__:")[1].strip()
            return {
                "passed": False,
                "actual": None,
                "error": error_msg
            }
        else:
            return {
                "passed": False,
                "actual": None,
                "error": result.stderr if result.stderr else "No output produced"
            }
            
    except FileNotFoundError:
        return {
            "passed": False,
            "actual": None,
            "error": "Node.js is not installed or not in PATH"
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "actual": None,
            "error": "Execution timed out (5 seconds limit)"
        }
    finally:
        os.unlink(temp_file)
