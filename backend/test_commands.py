"""Quick test for all critical JARVIS commands."""
import requests

API = "http://127.0.0.1:8766/api/command"

tests = [
    "open whatsapp",
    "open wifi settings",
    "open ms word",
    "open bluetooth",
    "open chrome",
    "open the file explorer",
    "please open notepad",
    "what is the time",
    "tell me about Japan",
    "I am bored bro",
]

print("=" * 60)
print("JARVIS COMMAND TEST SUITE")
print("=" * 60)

for cmd in tests:
    try:
        r = requests.post(API, json={"text": cmd}, timeout=30)
        data = r.json()
        status = "OK" if data.get("success") else "FAIL"
        intent = data.get("intent", "?")
        msg = (data.get("ai_response") or data.get("message", ""))[:80]
        print(f"  [{status}] '{cmd}'")
        print(f"        Intent: {intent} | Response: {msg}")
    except Exception as e:
        print(f"  [ERR] '{cmd}' -> {e}")
    print()

print("=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
