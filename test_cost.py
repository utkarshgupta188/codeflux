import requests, json

# 1. Test GET /metrics/cost (empty state)
r = requests.get("http://localhost:8000/metrics/cost")
print("=== COST METRICS (initial) ===")
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))

# 2. Send a chat request to trigger routing
r2 = requests.post("http://localhost:8000/chat", json={"prompt": "What is 2+2?"})
print("\n=== CHAT ===")
print(f"Status: {r2.status_code}")
d = r2.json()
print(f"Provider: {d.get('provider_used')}")
print(f"Latency: {d.get('latency_ms')}ms")

# 3. Check cost metrics again
r3 = requests.get("http://localhost:8000/metrics/cost")
print("\n=== COST METRICS (after request) ===")
print(json.dumps(r3.json(), indent=2))
