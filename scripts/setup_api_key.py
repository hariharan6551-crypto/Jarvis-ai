"""
J.A.R.V.I.S API Key Setup Helper
Run this to configure your AI provider API keys.

Usage: python scripts/setup_api_key.py
"""

import os
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

BANNER = """
================================================================
          J.A.R.V.I.S -- API Key Setup                         
================================================================

  JARVIS needs an AI API key to think and respond.             
  Without it, only basic commands work (open apps, volume).    

  [FREE] Google Gemini (recommended)                           
  Get your key: https://aistudio.google.com/apikey             

  Other options:                                               
  - OpenAI     -> https://platform.openai.com/api-keys        
  - Anthropic  -> https://console.anthropic.com/settings/keys  

================================================================
"""


def read_env():
    """Read current .env file."""
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
        return lines
    return []


def update_env_key(key, value):
    """Update a single key in the .env file."""
    lines = read_env()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_gemini_key(key):
    """Quick validation of a Gemini API key."""
    try:
        from google import genai
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say exactly: JARVIS online",
        )
        print(f"  [OK] Gemini API key is valid! Response: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"  [FAIL] Key validation failed: {e}")
        return False


def validate_openai_key(key):
    """Quick validation of an OpenAI API key."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say exactly: JARVIS online"}],
            max_tokens=10,
        )
        print(f"  [OK] OpenAI API key is valid! Response: {response.choices[0].message.content.strip()}")
        return True
    except Exception as e:
        print(f"  [FAIL] Key validation failed: {e}")
        return False


def main():
    print(BANNER)
    
    print("Which AI provider do you want to set up?")
    print()
    print("  [1] Google Gemini  (FREE -- recommended)")
    print("  [2] OpenAI GPT-4o  (paid)")
    print("  [3] Anthropic Claude (paid)")
    print("  [4] Enter key manually")
    print("  [q] Quit")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "q":
        return
    
    if choice == "1":
        print()
        print("  Step 1: Go to https://aistudio.google.com/apikey")
        print("  Step 2: Click 'Create API Key'")
        print("  Step 3: Copy the key and paste it below")
        print()
        key = input("  Paste your Gemini API key: ").strip()
        if key:
            print("\n  Validating key...")
            if validate_gemini_key(key):
                update_env_key("GEMINI_API_KEY", key)
                update_env_key("DEFAULT_AI_PROVIDER", "gemini")
                update_env_key("DEFAULT_AI_MODEL", "gemini-2.0-flash")
                print(f"\n  [OK] Saved to {ENV_FILE}")
                print("  Restart JARVIS to use the new key!")
            else:
                save = input("  Save anyway? (y/n): ").strip().lower()
                if save == "y":
                    update_env_key("GEMINI_API_KEY", key)
                    print(f"  Saved to {ENV_FILE}")
    
    elif choice == "2":
        print()
        key = input("  Paste your OpenAI API key (sk-...): ").strip()
        if key:
            print("\n  Validating key...")
            if validate_openai_key(key):
                update_env_key("OPENAI_API_KEY", key)
                update_env_key("DEFAULT_AI_PROVIDER", "openai")
                update_env_key("DEFAULT_AI_MODEL", "gpt-4o")
                print(f"\n  [OK] Saved to {ENV_FILE}")
                print("  Restart JARVIS to use the new key!")
            else:
                save = input("  Save anyway? (y/n): ").strip().lower()
                if save == "y":
                    update_env_key("OPENAI_API_KEY", key)
                    print(f"  Saved to {ENV_FILE}")
    
    elif choice == "3":
        print()
        key = input("  Paste your Anthropic API key (sk-ant-...): ").strip()
        if key:
            update_env_key("ANTHROPIC_API_KEY", key)
            update_env_key("DEFAULT_AI_PROVIDER", "anthropic")
            update_env_key("DEFAULT_AI_MODEL", "claude-sonnet-4-20250514")
            print(f"\n  [OK] Saved to {ENV_FILE}")
            print("  Restart JARVIS to use the new key!")
    
    elif choice == "4":
        print()
        print("  Enter the key name and value:")
        key_name = input("  Key name (e.g. GEMINI_API_KEY): ").strip()
        key_value = input("  Key value: ").strip()
        if key_name and key_value:
            update_env_key(key_name, key_value)
            print(f"\n  [OK] Saved {key_name} to {ENV_FILE}")


if __name__ == "__main__":
    main()
