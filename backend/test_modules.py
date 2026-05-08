"""Quick test of all JARVIS v2.0 modules."""
import sys
sys.path.insert(0, '.')

from config.settings import settings
from ai.planner import TaskPlanner
from automation.browser import BrowserEngine
from automation.vision import VisionEngine
from memory.preferences import PreferenceEngine

print("=== JARVIS v2.0 Module Test ===")

# Browser
b = BrowserEngine()
profiles = b.detect_chrome_profiles()
print(f"Chrome profiles found: {len(profiles)}")
for p in profiles:
    print(f"  - {p['name']} ({p.get('email', 'no email')})")

# Vision
v = VisionEngine()
print(f"Vision OCR available: {v.tesseract_available}")

# Preferences
pref = PreferenceEngine()
print(f"Preferences DB: OK")

# Planner
tp = TaskPlanner()
plan = tp._quick_classify("open chrome and select Mersal Hariharan account")
print(f"Plan for 'open chrome + profile': {[s['type'] for s in plan]}")

plan2 = tp._quick_classify("search youtube for python tutorials")
print(f"Plan for 'youtube search': {[s['type'] for s in plan2]}")

plan3 = tp._quick_classify("increase volume and open spotify")
print(f"Plan for 'volume + spotify': {plan3}")  # None = needs AI

print("\nAll v2.0 modules loaded successfully!")
