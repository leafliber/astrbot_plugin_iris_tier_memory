"""临时测试脚本"""
import subprocess
import sys

result = subprocess.run(
    [
        r"C:\Users\leaf\.workbuddy\binaries\python\versions\3.14.3\python.exe",
        "-m", "pytest",
        "tests/image/",
        "-v",
        "--tb=short"
    ],
    cwd=r"c:\Users\leaf\code\astrbot_plugin_iris_tier_memory",
    capture_output=True,
    text=True
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nExit code: {result.returncode}")

sys.exit(result.returncode)
