"""
J.A.R.V.I.S Module Import & Health Test
Run: python test_modules.py
Tests every backend module for import errors and basic health.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "✓"
FAIL = "✗"
WARN = "⚠"

results = []


def test_import(name, import_fn):
    """Test a single module import."""
    try:
        start = time.time()
        import_fn()
        elapsed = (time.time() - start) * 1000
        results.append((PASS, name, f"{elapsed:.0f}ms"))
        print(f"  {PASS} {name} ({elapsed:.0f}ms)")
        return True
    except Exception as e:
        results.append((FAIL, name, str(e)))
        print(f"  {FAIL} {name}: {e}")
        return False


def main():
    print("=" * 60)
    print("J.A.R.V.I.S Module Test Suite v2.5")
    print("=" * 60)
    print()

    # ── Core Modules ──────────────────────────────────────────────
    print("── Core ──")
    test_import("config.settings", lambda: __import__("config.settings"))
    test_import("config.config", lambda: __import__("config.config"))
    test_import("core.logger", lambda: __import__("core.logger"))
    test_import("core.watchdog", lambda: __import__("core.watchdog"))
    test_import("core.health", lambda: __import__("core.health"))
    print()

    # ── AI Modules ────────────────────────────────────────────────
    print("── AI ──")
    test_import("ai.provider", lambda: __import__("ai.provider"))
    test_import("ai.intent", lambda: __import__("ai.intent"))
    test_import("ai.planner", lambda: __import__("ai.planner"))
    print()

    # ── Automation ────────────────────────────────────────────────
    print("── Automation ──")
    test_import("automation.engine", lambda: __import__("automation.engine"))
    test_import("automation.browser", lambda: __import__("automation.browser"))
    test_import("automation.vision", lambda: __import__("automation.vision"))
    test_import("automation.workflows", lambda: __import__("automation.workflows"))
    print()

    # ── Memory ────────────────────────────────────────────────────
    print("── Memory ──")
    test_import("memory.engine", lambda: __import__("memory.engine"))
    test_import("memory.preferences", lambda: __import__("memory.preferences"))
    print()

    # ── Services ──────────────────────────────────────────────────
    print("── Services ──")
    test_import("services.orchestrator", lambda: __import__("services.orchestrator"))
    test_import("services.reminder", lambda: __import__("services.reminder"))
    test_import("services.notification", lambda: __import__("services.notification"))
    test_import("services.system_monitor", lambda: __import__("services.system_monitor"))
    print()

    # ── Voice ─────────────────────────────────────────────────────
    print("── Voice ──")
    test_import("voice.engine", lambda: __import__("voice.engine"))
    print()

    # ── External Dependencies ─────────────────────────────────────
    print("── External Dependencies ──")
    deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("dotenv", "dotenv"),
        ("loguru", "loguru"),
        ("psutil", "psutil"),
        ("pyautogui", "pyautogui"),
        ("edge_tts", "edge_tts"),
        ("google.generativeai", "google.generativeai"),
    ]
    for name, module in deps:
        test_import(name, lambda m=module: __import__(m))
    print()

    # Optional dependencies
    print("── Optional Dependencies ──")
    optional = [
        ("whisper", "whisper"),
        ("openai", "openai"),
        ("anthropic", "anthropic"),
        ("ollama", "ollama"),
        ("chromadb", "chromadb"),
        ("pyttsx3", "pyttsx3"),
        ("sounddevice", "sounddevice"),
        ("pygetwindow", "pygetwindow"),
        ("screen_brightness_control", "screen_brightness_control"),
        ("vosk", "vosk"),
        ("pycaw", "pycaw"),
        ("win10toast", "win10toast"),
        ("plyer", "plyer"),
        ("playwright", "playwright"),
        ("pytesseract", "pytesseract"),
    ]
    for name, module in optional:
        try:
            __import__(module)
            results.append((PASS, f"[optional] {name}", "installed"))
            print(f"  {PASS} {name} (installed)")
        except ImportError:
            results.append((WARN, f"[optional] {name}", "not installed"))
            print(f"  {WARN} {name} (not installed — optional)")
    print()

    # ── Intent Classification Test ────────────────────────────────
    print("── Intent Classification Quick Test ──")
    try:
        from ai.intent import IntentClassifier
        ic = IntentClassifier()
        tests = [
            ("open chrome", "open_app"),
            ("search youtube for python", "search_youtube"),
            ("volume up", "volume_up"),
            ("take a screenshot", "screenshot"),
            ("what time is it", "get_time"),
            ("remind me in 5 minutes to eat", "set_reminder"),
        ]
        for text, expected in tests:
            intent, param, conf = ic.classify(text)
            status = PASS if intent == expected else FAIL
            print(f"  {status} '{text}' → {intent} (conf: {conf:.2f})")
    except Exception as e:
        print(f"  {FAIL} Intent test failed: {e}")
    print()

    # ── Summary ───────────────────────────────────────────────────
    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    warned = sum(1 for r in results if r[0] == WARN)

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {warned} optional missing")
    print("=" * 60)

    if failed > 0:
        print("\nFailed modules:")
        for status, name, detail in results:
            if status == FAIL:
                print(f"  {FAIL} {name}: {detail}")
        sys.exit(1)
    else:
        print("\nAll required modules OK!")
        sys.exit(0)


if __name__ == "__main__":
    main()
