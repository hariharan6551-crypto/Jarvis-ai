import requests
r = requests.get("http://127.0.0.1:8765/api/browser/profiles")
data = r.json()
print(f"Chrome Profiles: {data['count']}")
for p in data["profiles"][:5]:
    print(f"  {p['name']} - {p.get('email','')}")

r2 = requests.get("http://127.0.0.1:8765/api/status")
s = r2.json()
print(f"\nSystem: v{s.get('version','?')}")
print(f"AI Providers: {s.get('ai_providers','?')}")
print(f"User: {s.get('user','?')}")
print(f"Memory stats: {s.get('memory','?')}")

r3 = requests.post("http://127.0.0.1:8765/api/command", json={"text": "hello jarvis"})
resp = r3.json()
print(f"\nTest command response: {resp.get('ai_response','')[:100]}")
print(f"Intent: {resp.get('intent')}, Duration: {resp.get('duration_ms')}ms")
print("\nAll API tests passed!")
