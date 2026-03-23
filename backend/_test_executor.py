"""Quick smoke test for code executors."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.code_executor import execute_java, execute_java_test, execute_csharp, execute_csharp_test, execute_typescript


async def test():
    print("=== Java basic run ===")
    java_code = (
        "public class Solution {\n"
        "    public static void main(String[] args) {\n"
        "        System.out.println(\"Hello from Java!\");\n"
        "    }\n"
        "}\n"
    )
    r = await execute_java(java_code)
    print(r)

    print("\n=== Java test harness ===")
    java_sol = (
        "public class Solution {\n"
        "    public int add(int a, int b) { return a + b; }\n"
        "}\n"
    )
    r2 = await execute_java_test(java_sol, {"a": 3, "b": 5}, 8)
    print(r2)

    print("\n=== Java test harness (array) ===")
    java_sol2 = (
        "public class Solution {\n"
        "    public int[] twoSum(int[] nums, int target) {\n"
        "        for (int i = 0; i < nums.length; i++)\n"
        "            for (int j = i+1; j < nums.length; j++)\n"
        "                if (nums[i]+nums[j] == target) return new int[]{i,j};\n"
        "        return new int[]{};\n"
        "    }\n"
        "}\n"
    )
    r3 = await execute_java_test(java_sol2, {"nums": [2, 7, 11, 15], "target": 9}, [0, 1])
    print(r3)

    print("\n=== C# basic run ===")
    cs_code = (
        "Console.WriteLine(\"Hello from C#!\");\n"
    )
    r4 = await execute_csharp(cs_code)
    print(r4)

    print("\n=== C# test harness ===")
    cs_sol = (
        "public class Solution {\n"
        "    public int Add(int a, int b) { return a + b; }\n"
        "}\n"
    )
    r5 = await execute_csharp_test(cs_sol, {"a": 3, "b": 5}, 8)
    print(r5)

    print("\n=== TypeScript basic run ===")
    ts_code = (
        "const x: number = 42;\n"
        "console.log('Hello from TypeScript! Value:', x);\n"
    )
    r6 = await execute_typescript(ts_code)
    print(r6)


asyncio.run(test())
