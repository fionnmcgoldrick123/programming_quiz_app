"""
Code Execution module.
Handles execution of code in different programming languages and test case validation.
"""
import subprocess
import tempfile
import os
import sys
import json as json_module
import re
from pydantic_models import RunCodeRequest, SubmitCodeRequest


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
    """
    Execute Python code.
    
    Args:
        code (str): The Python code to execute.
        
    Returns:
        dict: Execution result with success status, output, and error.
    """
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
    """
    Execute JavaScript code using Node.js.
    
    Args:
        code (str): The JavaScript code to execute.
        
    Returns:
        dict: Execution result with success status, output, and error.
    """
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
    """
    Execute Python code with test inputs.
    
    Args:
        code (str): The Python code to test.
        input_data (dict): Test input parameters.
        expected: Expected output.
        
    Returns:
        dict: Test result with pass/fail status.
    """
    # Extract function name from code (basic implementation)
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
    result = {func_name}({', '.join(f'{k}={json_module.dumps(v)}' for k, v in input_data.items())})
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
    """
    Execute JavaScript code with test inputs.
    
    Args:
        code (str): The JavaScript code to test.
        input_data (dict): Test input parameters.
        expected: Expected output.
        
    Returns:
        dict: Test result with pass/fail status.
    """
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
