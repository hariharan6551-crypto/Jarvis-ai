"""
Quick TTS test - Verify text-to-speech works.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pyttsx3

print("=" * 50)
print("  JARVIS TTS Test")
print("=" * 50)

engine = pyttsx3.init()

# List available voices
print("\n[SPEAKER] Available voices:")
voices = engine.getProperty('voices')
for i, voice in enumerate(voices):
    print(f"   [{i}] {voice.name}")

# Configure
engine.setProperty('rate', 175)
engine.setProperty('volume', 1.0)

# Try to use a male voice
selected = voices[0].name
for voice in voices:
    if 'david' in voice.name.lower() or 'male' in voice.name.lower():
        engine.setProperty('voice', voice.id)
        selected = voice.name
        break

print(f"\n   Selected voice: {selected}")
print("\n[SPEAK] Speaking test phrase...")
engine.say("JARVIS online. Systems nominal. Ready to serve.")
engine.runAndWait()

print("[OK] TTS is working!")
