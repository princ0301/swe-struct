"""Quick environment check. Run: uv run python scripts/check_env.py"""
import os
import platform
import shutil
import subprocess
import sys

def line(label: str, ok: bool, detail: str = "") -> None:
    print(f"[{'OK' if ok else '!!'}] {label} {detail}".rstrip())

def run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"

def main() -> None:
    line("python", sys.version_info >= (3, 11), sys.version.split()[0])
    line("platform", True, platform.platform())
    line("git", shutil.which("git") is not None, run(["git", "--version"]))
    line("uv", shutil.which("uv") is not None, run(["uv", "--version"]))
    line("ollama binary", shutil.which("ollama") is not None, run(["ollama", "--version"]))
    line("HF_TOKEN set (optional for now)", bool(os.environ.get("HF_TOKEN")))

    try:
        import httpx

        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        names = [m["name"] for m in r.json().get("models", [])]
        line("ollama server reachable", r.status_code == 200, f"models: {names}")
    except Exception as e:  # noqa: BLE001
        line("ollama server reachable", False, f"({type(e).__name__}) start it with: ollama serve")

    try:
        import swe_struct

        line("swe_struct importable", True, swe_struct.__version__)
    except Exception as e:  # noqa: BLE001
        line("swe_struct importable", False, repr(e))

if __name__ == "__main__":
    main()