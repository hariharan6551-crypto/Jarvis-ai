"""
J.A.R.V.I.S Windows Service Launcher
Starts the backend server silently in the background.
Run this script at Windows startup to auto-launch J.A.R.V.I.S.
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
LOG_FILE = BACKEND_DIR / "logs" / "launcher.log"

# Ensure log directory exists
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def start_backend():
    """Start the FastAPI backend server."""
    log("Starting J.A.R.V.I.S backend...")
    python_exe = sys.executable
    return subprocess.Popen(
        [python_exe, "main.py"],
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def start_frontend():
    """Start the Vite dev server for the frontend."""
    log("Starting J.A.R.V.I.S frontend...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    return subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def start_electron():
    """Start the Electron desktop app after frontend is ready."""
    log("Starting J.A.R.V.I.S Electron app...")
    time.sleep(4)  # Wait for Vite to be ready
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    return subprocess.Popen(
        [npx_cmd, "electron", "."],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "NODE_ENV": "development"},
    )


def main():
    log("=" * 50)
    log("J.A.R.V.I.S SYSTEM LAUNCHER")
    log("=" * 50)

    processes = []

    try:
        backend_proc = start_backend()
        processes.append(("Backend", backend_proc))
        time.sleep(2)

        frontend_proc = start_frontend()
        processes.append(("Frontend", frontend_proc))

        electron_proc = start_electron()
        processes.append(("Electron", electron_proc))

        log("All systems launched successfully!")
        log("Backend:  http://127.0.0.1:8765")
        log("Frontend: http://localhost:5173")

        # Keep running until Electron closes
        electron_proc.wait()
        log("Electron closed. Shutting down...")

    except KeyboardInterrupt:
        log("Shutdown requested...")
    except Exception as e:
        log(f"Launch error: {e}")
    finally:
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                log(f"{name} stopped.")
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        log("J.A.R.V.I.S shutdown complete.")


if __name__ == "__main__":
    main()
