"""
Quick microphone test - Run this FIRST to verify audio works.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import speech_recognition as sr

print("=" * 50)
print("  JARVIS Microphone Test")
print("=" * 50)

# List available microphones
print("\n[MIC] Available microphones:")
for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"   [{i}] {name}")

# Test default microphone
print("\n[MIC] Testing default microphone...")
recognizer = sr.Recognizer()

try:
    with sr.Microphone() as source:
        print("   Calibrating for ambient noise (2 seconds)...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print(f"   Energy threshold: {recognizer.energy_threshold:.0f}")
        print("\n[LISTEN] Say something (you have 5 seconds)...")
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)

    print("   Processing speech...")
    text = recognizer.recognize_google(audio)
    print(f"\n[OK] SUCCESS! Heard: '{text}'")
    print("\n[READY] Your microphone is working! You can now run jarvis_core.py")

except sr.WaitTimeoutError:
    print("\n[WARN] No speech detected within 5 seconds.")
    print("   Make sure you're speaking near the microphone.")

except sr.UnknownValueError:
    print("\n[WARN] Heard audio but couldn't understand it.")
    print("   Try speaking more clearly.")

except sr.RequestError as e:
    print(f"\n[ERROR] Speech recognition service error: {e}")
    print("   Check your internet connection (Google STT requires internet).")

except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    print("   Make sure a microphone is connected.")
