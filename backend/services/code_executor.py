"""
Code Execution module.
Handles execution of code in different programming languages and test case validation.
"""

import subprocess
import tempfile
import shutil
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
        return {"success": False, "output": "", "error": str(e)}


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
                    request.code, request.language, input_data, expected
                )

                test_results.append(
                    {
                        "test_number": i + 1,
                        "input": input_data,
                        "expected": expected,
                        "actual": result.get("actual"),
                        "passed": result.get("passed", False),
                        "error": result.get("error"),
                    }
                )

                if not result.get("passed", False):
                    all_passed = False

            except json_module.JSONDecodeError as e:
                test_results.append(
                    {
                        "test_number": i + 1,
                        "passed": False,
                        "error": f"Invalid test case format: {str(e)}",
                    }
                )
                all_passed = False

        return {
            "success": all_passed,
            "test_results": test_results,
            "message": "All tests passed!" if all_passed else "Some tests failed.",
        }

    except Exception as e:
        return {"success": False, "test_results": [], "error": str(e)}


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
        elif lang == "javascript":
            return await execute_javascript(code)
        elif lang == "typescript":
            return await execute_typescript(code)
        elif lang == "java":
            return await execute_java(code)
        elif lang in ["c#", "csharp"]:
            return await execute_csharp(code)
        else:
            return {
                "success": False,
                "output": "",
                "error": f"Language '{language}' is not supported yet. Supported: Python, JavaScript, TypeScript, Java, C#",
            }
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


async def execute_python(code: str):
    """
    Execute Python code.

    Args:
        code (str): The Python code to execute.

    Returns:
        dict: Execution result with success status, output, and error.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        temp_file = f.name

    try:
        result = subprocess.run(
            [sys.executable, temp_file], capture_output=True, text=True, timeout=5
        )

        success = result.returncode == 0
        output = result.stdout
        error = result.stderr

        return {"success": success, "output": output, "error": error if error else None}
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Execution timed out (5 seconds limit)",
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
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        temp_file = f.name

    try:
        result = subprocess.run(
            ["node", temp_file], capture_output=True, text=True, timeout=5
        )

        success = result.returncode == 0
        output = result.stdout
        error = result.stderr

        return {"success": success, "output": output, "error": error if error else None}
    except FileNotFoundError:
        return {
            "success": False,
            "output": "",
            "error": "Node.js is not installed or not in PATH",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Execution timed out (5 seconds limit)",
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
        elif lang == "javascript":
            return await execute_javascript_test(code, input_data, expected)
        elif lang == "typescript":
            return await execute_typescript_test(code, input_data, expected)
        elif lang == "java":
            return await execute_java_test(code, input_data, expected)
        elif lang in ["c#", "csharp"]:
            return await execute_csharp_test(code, input_data, expected)
        else:
            return {
                "passed": False,
                "error": f"Language '{language}' not supported for testing",
            }
    except Exception as e:
        return {"passed": False, "error": str(e)}


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
    func_match = re.search(r"def\s+(\w+)\s*\(", code)
    if not func_match:
        return {"passed": False, "error": "Could not find function definition in code"}

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

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(test_code)
        temp_file = f.name

    try:
        result = subprocess.run(
            [sys.executable, temp_file], capture_output=True, text=True, timeout=5
        )

        output = result.stdout

        # Parse result
        if "__RESULT__:" in output:
            result_line = [
                line for line in output.split("\n") if "__RESULT__:" in line
            ][0]
            actual_str = result_line.split("__RESULT__:")[1].strip()
            actual = json_module.loads(actual_str)
            passed = actual == expected

            return {"passed": passed, "actual": actual, "error": None}
        elif "__ERROR__:" in output:
            error_line = [line for line in output.split("\n") if "__ERROR__:" in line][
                0
            ]
            error_msg = error_line.split("__ERROR__:")[1].strip()
            return {"passed": False, "actual": None, "error": error_msg}
        else:
            return {
                "passed": False,
                "actual": None,
                "error": result.stderr if result.stderr else "No output produced",
            }

    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "actual": None,
            "error": "Execution timed out (5 seconds limit)",
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
    func_match = re.search(r"function\s+(\w+)\s*\(", code)
    if not func_match:
        return {"passed": False, "error": "Could not find function definition in code"}

    func_name = func_match.group(1)

    # Build test code
    args_str = ", ".join(json_module.dumps(v) for v in input_data.values())
    test_code = f"""{code}

// Test execution
try {{
    const result = {func_name}({args_str});
    console.log("__RESULT__:", JSON.stringify(result));
}} catch (e) {{
    console.log("__ERROR__:", e.message);
}}
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as f:
        f.write(test_code)
        temp_file = f.name

    try:
        result = subprocess.run(
            ["node", temp_file], capture_output=True, text=True, timeout=5
        )

        output = result.stdout

        # Parse result
        if "__RESULT__:" in output:
            result_line = [
                line for line in output.split("\n") if "__RESULT__:" in line
            ][0]
            actual_str = result_line.split("__RESULT__:")[1].strip()
            actual = json_module.loads(actual_str)
            passed = actual == expected

            return {"passed": passed, "actual": actual, "error": None}
        elif "__ERROR__:" in output:
            error_line = [line for line in output.split("\n") if "__ERROR__:" in line][
                0
            ]
            error_msg = error_line.split("__ERROR__:")[1].strip()
            return {"passed": False, "actual": None, "error": error_msg}
        else:
            return {
                "passed": False,
                "actual": None,
                "error": result.stderr if result.stderr else "No output produced",
            }

    except FileNotFoundError:
        return {
            "passed": False,
            "actual": None,
            "error": "Node.js is not installed or not in PATH",
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "actual": None,
            "error": "Execution timed out (5 seconds limit)",
        }
    finally:
        os.unlink(temp_file)


# ---------------------------------------------------------------------------
# TypeScript
# ---------------------------------------------------------------------------

async def execute_typescript(code: str):
    """Execute TypeScript code using Node.js --experimental-strip-types (Node 22+)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ts", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        temp_file = f.name

    try:
        result = subprocess.run(
            ["node", "--experimental-strip-types", "--no-warnings=ExperimentalWarning", temp_file],
            capture_output=True, text=True, timeout=5,
        )
        success = result.returncode == 0
        return {"success": success, "output": result.stdout, "error": result.stderr if result.stderr else None}
    except FileNotFoundError:
        return {"success": False, "output": "", "error": "Node.js is not installed or not in PATH"}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Execution timed out (5 seconds limit)"}
    finally:
        os.unlink(temp_file)


async def execute_typescript_test(code: str, input_data: dict, expected):
    """Execute TypeScript code with test inputs using Node.js --experimental-strip-types."""
    func_match = re.search(r"function\s+(\w+)\s*\(", code)
    if not func_match:
        func_match = re.search(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=])\s*=>", code)
    if not func_match:
        return {"passed": False, "error": "Could not find function definition in code"}

    func_name = func_match.group(1)
    args_str = ", ".join(json_module.dumps(v) for v in input_data.values())

    test_code = f"""{code}

// Test execution
try {{
    const result = {func_name}({args_str});
    console.log("__RESULT__:", JSON.stringify(result));
}} catch (e: unknown) {{
    console.log("__ERROR__:", (e as Error).message);
}}
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ts", delete=False, encoding="utf-8"
    ) as f:
        f.write(test_code)
        temp_file = f.name

    try:
        result = subprocess.run(
            ["node", "--experimental-strip-types", "--no-warnings=ExperimentalWarning", temp_file],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout

        if "__RESULT__:" in output:
            result_line = [l for l in output.split("\n") if "__RESULT__:" in l][0]
            actual = json_module.loads(result_line.split("__RESULT__:")[1].strip())
            return {"passed": actual == expected, "actual": actual, "error": None}
        elif "__ERROR__:" in output:
            error_line = [l for l in output.split("\n") if "__ERROR__:" in l][0]
            return {"passed": False, "actual": None, "error": error_line.split("__ERROR__:")[1].strip()}
        else:
            return {"passed": False, "actual": None, "error": result.stderr if result.stderr else "No output produced"}

    except FileNotFoundError:
        return {"passed": False, "actual": None, "error": "Node.js is not installed or not in PATH"}
    except subprocess.TimeoutExpired:
        return {"passed": False, "actual": None, "error": "Execution timed out (5 seconds limit)"}
    finally:
        os.unlink(temp_file)


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------

def _python_to_java_literal(val) -> str:
    """Convert a Python value to a Java literal string."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return repr(val) + "d"
    if isinstance(val, str):
        escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(val, list):
        if not val:
            return "new int[]{}"
        if all(isinstance(x, bool) for x in val):
            inner = ", ".join("true" if x else "false" for x in val)
            return f"new boolean[]{{{inner}}}"
        if all(isinstance(x, int) for x in val):
            inner = ", ".join(str(x) for x in val)
            return f"new int[]{{{inner}}}"
        if all(isinstance(x, float) for x in val):
            inner = ", ".join(repr(x) + "d" for x in val)
            return f"new double[]{{{inner}}}"
        if all(isinstance(x, str) for x in val):
            inner = ", ".join(f'"{x}"' for x in val)
            return f'new String[]{{{inner}}}'
        if all(isinstance(x, list) and all(isinstance(y, int) for y in x) for x in val):
            rows = ", ".join(
                "new int[]{" + ", ".join(str(y) for y in row) + "}" for row in val
            )
            return f"new int[][]{{{rows}}}"
        inner = ", ".join(_python_to_java_literal(x) for x in val)
        return f"new Object[]{{{inner}}}"
    return str(val)


_JAVA_TO_JSON_HELPER = """
    static String __toJson(Object obj) {
        if (obj == null) return "null";
        if (obj instanceof Boolean || obj instanceof Integer || obj instanceof Long
                || obj instanceof Double || obj instanceof Float) return obj.toString();
        if (obj instanceof String) {
            String s = (String) obj;
            return "\\"" + s.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"").replace("\\n", "\\\\n") + "\\"";
        }
        if (obj instanceof int[]) {
            int[] a = (int[]) obj; StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(","); sb.append(a[i]); }
            return sb.append("]").toString();
        }
        if (obj instanceof long[]) {
            long[] a = (long[]) obj; StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(","); sb.append(a[i]); }
            return sb.append("]").toString();
        }
        if (obj instanceof boolean[]) {
            boolean[] a = (boolean[]) obj; StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(","); sb.append(a[i]); }
            return sb.append("]").toString();
        }
        if (obj instanceof double[]) {
            double[] a = (double[]) obj; StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(","); sb.append(a[i]); }
            return sb.append("]").toString();
        }
        if (obj instanceof String[]) {
            String[] a = (String[]) obj; StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < a.length; i++) {
                if (i > 0) sb.append(",");
                sb.append("\\"").append(((String)a[i]).replace("\\"", "\\\\\\"")).append("\\"");
            }
            return sb.append("]").toString();
        }
        if (obj instanceof int[][]) {
            int[][] a = (int[][]) obj; StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < a.length; i++) {
                if (i > 0) sb.append(","); sb.append("[");
                for (int j = 0; j < a[i].length; j++) { if (j > 0) sb.append(","); sb.append(a[i][j]); }
                sb.append("]");
            }
            return sb.append("]").toString();
        }
        if (obj instanceof java.util.List) {
            java.util.List<?> list = (java.util.List<?>) obj; StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < list.size(); i++) { if (i > 0) sb.append(","); sb.append(__toJson(list.get(i))); }
            return sb.append("]").toString();
        }
        return "\\"" + obj.toString().replace("\\"", "\\\\\\"") + "\\"";
    }
"""


async def execute_java(code: str):
    """Execute Java code by compiling and running with javac/java."""
    class_match = re.search(r"public\s+class\s+(\w+)", code)
    class_name = class_match.group(1) if class_match else "Solution"

    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, f"{class_name}.java")

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)

        compile_result = subprocess.run(
            ["javac", temp_file], capture_output=True, text=True, timeout=15
        )
        if compile_result.returncode != 0:
            return {"success": False, "output": "", "error": compile_result.stderr}

        run_result = subprocess.run(
            ["java", "-cp", temp_dir, class_name],
            capture_output=True, text=True, timeout=10,
        )
        return {
            "success": run_result.returncode == 0,
            "output": run_result.stdout,
            "error": run_result.stderr if run_result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Execution timed out (10 seconds limit)"}
    except FileNotFoundError:
        return {"success": False, "output": "", "error": "Java (javac/java) is not installed or not in PATH"}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def execute_java_test(code: str, input_data: dict, expected):
    """Execute Java code with test inputs."""
    class_match = re.search(r"public\s+class\s+(\w+)", code)
    class_name = class_match.group(1) if class_match else "Solution"

    # Find first public non-main method
    method_match = None
    for m in re.finditer(
        r"public\s+(?:static\s+)?(?!class\b)(\w[\w\[\]<>,\s]*)\s+(\w+)\s*\(([^)]*)\)",
        code,
    ):
        if m.group(2) != "main":
            method_match = m
            break

    if not method_match:
        return {"passed": False, "error": "Could not find a public method in the Java code"}

    method_name = method_match.group(2)
    is_static = bool(re.search(r"public\s+static\s+", method_match.group(0)))
    args_str = ", ".join(_python_to_java_literal(v) for v in input_data.values())
    invocation = (
        f"{class_name}.{method_name}({args_str})"
        if is_static
        else f"new {class_name}().{method_name}({args_str})"
    )

    # Make Solution class non-public so Main can be the public class in a single file
    modified_code = re.sub(r"\bpublic(\s+class\s+" + class_name + r"\b)", r"\1", code)

    test_source = f"""{modified_code}

public class Main {{
{_JAVA_TO_JSON_HELPER}
    public static void main(String[] args) {{
        try {{
            Object result = (Object) {invocation};
            System.out.println("__RESULT__: " + __toJson(result));
        }} catch (Exception e) {{
            System.out.println("__ERROR__: " + e.getMessage());
        }}
    }}
}}
"""

    temp_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(temp_dir, "Main.java"), "w", encoding="utf-8") as f:
            f.write(test_source)

        compile_result = subprocess.run(
            ["javac", os.path.join(temp_dir, "Main.java")],
            capture_output=True, text=True, timeout=15,
        )
        if compile_result.returncode != 0:
            return {"passed": False, "actual": None, "error": f"Compilation error: {compile_result.stderr}"}

        run_result = subprocess.run(
            ["java", "-cp", temp_dir, "Main"],
            capture_output=True, text=True, timeout=10,
        )
        output = run_result.stdout

        if "__RESULT__:" in output:
            result_line = [l for l in output.split("\n") if "__RESULT__:" in l][0]
            actual = json_module.loads(result_line.split("__RESULT__:")[1].strip())
            return {"passed": actual == expected, "actual": actual, "error": None}
        elif "__ERROR__:" in output:
            error_line = [l for l in output.split("\n") if "__ERROR__:" in l][0]
            return {"passed": False, "actual": None, "error": error_line.split("__ERROR__:")[1].strip()}
        else:
            return {"passed": False, "actual": None, "error": run_result.stderr if run_result.stderr else "No output produced"}

    except subprocess.TimeoutExpired:
        return {"passed": False, "actual": None, "error": "Execution timed out (10 seconds limit)"}
    except FileNotFoundError:
        return {"passed": False, "actual": None, "error": "Java (javac/java) is not installed or not in PATH"}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# C# (.NET)
# ---------------------------------------------------------------------------

_CSHARP_CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net9.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
  </PropertyGroup>
</Project>
"""


def _python_to_csharp_literal(val) -> str:
    """Convert a Python value to a C# literal string."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return repr(val) + "d"
    if isinstance(val, str):
        escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(val, list):
        if not val:
            return "new int[]{}"
        if all(isinstance(x, bool) for x in val):
            inner = ", ".join("true" if x else "false" for x in val)
            return f"new bool[]{{{inner}}}"
        if all(isinstance(x, int) for x in val):
            inner = ", ".join(str(x) for x in val)
            return f"new int[]{{{inner}}}"
        if all(isinstance(x, float) for x in val):
            inner = ", ".join(repr(x) + "d" for x in val)
            return f"new double[]{{{inner}}}"
        if all(isinstance(x, str) for x in val):
            inner = ", ".join(f'"{x}"' for x in val)
            return f'new string[]{{{inner}}}'
        if all(isinstance(x, list) and all(isinstance(y, int) for y in x) for x in val):
            rows = ", ".join(
                "new int[]{" + ", ".join(str(y) for y in row) + "}" for row in val
            )
            return f"new int[][]{{{rows}}}"
        inner = ", ".join(_python_to_csharp_literal(x) for x in val)
        return f"new object[]{{{inner}}}"
    return str(val)


async def execute_csharp(code: str):
    """Execute C# code by creating a temp dotnet project and running it."""
    temp_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(temp_dir, "Program.csproj"), "w", encoding="utf-8") as f:
            f.write(_CSHARP_CSPROJ)
        with open(os.path.join(temp_dir, "Program.cs"), "w", encoding="utf-8") as f:
            f.write(code)

        result = subprocess.run(
            ["dotnet", "run", "--project", temp_dir, "--nologo"],
            capture_output=True, text=True, timeout=60,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Execution timed out (60 seconds limit)"}
    except FileNotFoundError:
        return {"success": False, "output": "", "error": "dotnet is not installed or not in PATH"}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def execute_csharp_test(code: str, input_data: dict, expected):
    """Execute C# code with test inputs."""
    class_match = re.search(r"(?:public\s+)?class\s+(\w+)", code)
    class_name = class_match.group(1) if class_match else "Solution"

    method_match = None
    for m in re.finditer(
        r"public\s+(?:static\s+)?(?!class\b)(\w[\w\[\]<>,?\s]*)\s+(\w+)\s*\(([^)]*)\)",
        code,
    ):
        if m.group(2) != "Main":
            method_match = m
            break

    if not method_match:
        return {"passed": False, "error": "Could not find a public method in the C# code"}

    method_name = method_match.group(2)
    is_static = bool(re.search(r"public\s+static\s+", method_match.group(0)))
    args_str = ", ".join(_python_to_csharp_literal(v) for v in input_data.values())
    invocation = (
        f"{class_name}.{method_name}({args_str})"
        if is_static
        else f"new {class_name}().{method_name}({args_str})"
    )

    # Strip using directives from user code (ImplicitUsings covers common ones)
    stripped_code = re.sub(r"^\s*using\s+[\w.]+;\s*\n?", "", code, flags=re.MULTILINE)

    test_source = f"""{stripped_code}

class __TestRunner {{
    static void Main() {{
        try {{
            var result = {invocation};
            Console.WriteLine("__RESULT__: " + System.Text.Json.JsonSerializer.Serialize(result));
        }} catch (Exception e) {{
            Console.WriteLine("__ERROR__: " + e.Message);
        }}
    }}
}}
"""

    temp_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(temp_dir, "Program.csproj"), "w", encoding="utf-8") as f:
            f.write(_CSHARP_CSPROJ)
        with open(os.path.join(temp_dir, "Program.cs"), "w", encoding="utf-8") as f:
            f.write(test_source)

        result = subprocess.run(
            ["dotnet", "run", "--project", temp_dir, "--nologo"],
            capture_output=True, text=True, timeout=60,
        )
        output = result.stdout

        if "__RESULT__:" in output:
            result_line = [l for l in output.split("\n") if "__RESULT__:" in l][0]
            actual = json_module.loads(result_line.split("__RESULT__:")[1].strip())
            return {"passed": actual == expected, "actual": actual, "error": None}
        elif "__ERROR__:" in output:
            error_line = [l for l in output.split("\n") if "__ERROR__:" in l][0]
            return {"passed": False, "actual": None, "error": error_line.split("__ERROR__:")[1].strip()}
        else:
            return {"passed": False, "actual": None, "error": result.stderr if result.stderr else "No output produced"}

    except subprocess.TimeoutExpired:
        return {"passed": False, "actual": None, "error": "Execution timed out (60 seconds limit)"}
    except FileNotFoundError:
        return {"passed": False, "actual": None, "error": "dotnet is not installed or not in PATH"}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
