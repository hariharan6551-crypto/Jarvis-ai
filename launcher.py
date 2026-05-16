"""
J.A.R.V.I.S Pre-Launch Validator & Launcher
Checks Python version, .env keys, port availability, mic detection, and dependencies
before starting the backend and frontend servers.
"""

import os
import sys
import socket
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ENV_FILE = PROJECT_ROOT / ".env"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def banner():
    print(f"""
{CYAN}╔══════════════════════════════════════════════════╗
║        J.A.R.V.I.S v2.5 — Pre-Launch Check       ║
║     Just A Rather Very Intelligent System         ║
╚══════════════════════════════════════════════════╝{RESET}
""")


def check_python_version() -> bool:
    """Ensure Python 3.10+ is installed."""
    ver = sys.version_info
    if ver.major >= 3 and ver.minor >= 10:
        print(f"  {GREEN}✓{RESET} Python {ver.major}.{ver.minor}.{ver.micro}")
        return True
    else:
        print(f"  {RED}✗{RESET} Python {ver.major}.{ver.minor} (need 3.10+)")
        return False


def check_env_file() -> bool:
    """Check .env file exists and has valid API keys."""
    if not ENV_FILE.exists():
        print(f"  {RED}✗{RESET} .env file not found at {ENV_FILE}")
        return False

    print(f"  {GREEN}✓{RESET} .env file found")

    # Check for at least one valid API key
    placeholders = {"your_key_here", "changeme", "xxx", "todo", ""}
    has_key = False
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if key in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
                if val.lower() not in placeholders:
                    has_key = True
                    print(f"  {GREEN}✓{RESET} {key} configured")

    if not has_key:
        print(f"  {YELLOW}⚠{RESET} No AI API key configured (only Ollama/local models available)")

    return True


def check_port_available(port: int = 8765) -> bool:
    """Check if the backend port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            if result == 0:
                print(f"  {YELLOW}⚠{RESET} Port {port} already in use (backend may already be running)")
                return True  # Not fatal, might be a previous instance
            else:
                print(f"  {GREEN}✓{RESET} Port {port} available")
                return True
    except Exception as e:
        print(f"  {YELLOW}⚠{RESET} Port check failed: {e}")
        return True


def check_mic() -> bool:
    """Check if a microphone is available."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
        if input_devices:
            default = sd.default.device[0]
            name = devices[default]["name"] if default is not None and default >= 0 else input_devices[0]["name"]
            print(f"  {GREEN}✓{RESET} Microphone: {name}")
            return True
        else:
            print(f"  {YELLOW}⚠{RESET} No microphone detected (voice control will be limited)")
            return True  # Not fatal
    except ImportError:
        print(f"  {YELLOW}⚠{RESET} sounddevice not installed (mic detection unavailable)")
        return True
    except Exception as e:
        print(f"  {YELLOW}⚠{RESET} Mic check failed: {e}")
        return True


def check_node() -> bool:
    """Check Node.js is available."""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ver = result.stdout.strip()
            print(f"  {GREEN}✓{RESET} Node.js {ver}")
            return True
    except Exception:
        pass
    print(f"  {RED}✗{RESET} Node.js not found (needed for frontend)")
    return False


def check_npm_installed() -> bool:
    """Check if frontend npm packages are installed."""
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        print(f"  {GREEN}✓{RESET} Frontend dependencies installed")
        return True
    else:
        print(f"  {YELLOW}⚠{RESET} Frontend node_modules not found — running 'npm install'...")
        try:
            subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), timeout=120)
            return True
        except Exception as e:
            print(f"  {RED}✗{RESET} npm install failed: {e}")
            return False


def check_backend_deps() -> bool:
    """Check critical Python packages."""
    required = ["fastapi", "uvicorn", "pydantic", "loguru", "psutil", "edge_tts"]
    voice_deps = ["speech_recognition", "sounddevice"]
    missing = []
    missing_voice = []

    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    for pkg in voice_deps:
        try:
            __import__(pkg)
        except ImportError:
            missing_voice.append(pkg)

    if missing:
        print(f"  {RED}✗{RESET} Missing packages: {', '.join(missing)}")
        print(f"      Run: pip install -r backend/requirements.txt")
        return False
    else:
        print(f"  {GREEN}✓{RESET} All required Python packages installed")

    if missing_voice:
        print(f"  {YELLOW}⚠{RESET} Missing voice packages: {', '.join(missing_voice)}")
        print(f"      Voice commands may not work. Run: pip install SpeechRecognition sounddevice")

    return True


def launch():
    """Launch backend and frontend."""
    print(f"\n{CYAN}{'='*50}")
    print(f"  Launching J.A.R.V.I.S...")
    print(f"{'='*50}{RESET}\n")

    # Start backend
    print(f"  Starting backend server...")
    backend_proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(BACKEND_DIR),
    )

    # Wait for backend to start
    time.sleep(3)

    # Start frontend
    print(f"  Starting frontend...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(FRONTEND_DIR),
        shell=True,
    )

    time.sleep(2)

    print(f"""
{GREEN}{'='*50}
  J.A.R.V.I.S is running!
{'='*50}{RESET}

  Backend:  {CYAN}http://127.0.0.1:8765{RESET}
  Frontend: {CYAN}http://localhost:5173{RESET}
  API Docs: {CYAN}http://127.0.0.1:8765/docs{RESET}

  Voice:    Say "Hey JARVIS" or "JARVIS" + command
  Clap:     Single clap to activate

  Press Ctrl+C to stop.
""")

    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Stopping J.A.R.V.I.S...{RESET}")
        backend_proc.terminate()
        frontend_proc.terminate()
        print(f"{GREEN}Goodbye!{RESET}")


def main():
    banner()

    print(f"{BOLD}Pre-Launch Checks:{RESET}")
    print()

    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Backend Port", check_port_available),
        ("Microphone", check_mic),
        ("Node.js", check_node),
        ("Python Packages", check_backend_deps),
        ("Frontend Deps", check_npm_installed),
    ]

    all_ok = True
    for name, fn in checks:
        try:
            result = fn()
            if not result:
                all_ok = False
        except Exception as e:
            print(f"  {RED}✗{RESET} {name} check failed: {e}")
            all_ok = False

    print()

    if not all_ok:
        print(f"{RED}Some checks failed. Please fix the issues above and try again.{RESET}")
        sys.exit(1)

    print(f"{GREEN}All checks passed!{RESET}")
    launch()


if __name__ == "__main__":
    main()
