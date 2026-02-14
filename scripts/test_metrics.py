import requests
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000"

def generate_traffic(n=5):
    print(f"Generating {n} requests to populate metrics...")
    
    def send_req(i):
        # Alternate prompts to vary latency naturally if possible, strictly we just want hits
        is_even = i % 2 == 0
        prompt = f"Test request {i} - {'short' if is_even else 'long explanation'}"
        try:
            requests.post(f"{BASE_URL}/chat", json={
                "prompt": prompt,
                "task_type": "test",
                "preferred_model": "llama-3.3-70b-versatile" # Use valid model
            })
        except:
            pass

    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(send_req, range(n))
    
    # Allow DB background tasks to finish
    time.sleep(2)

def check_metrics():
    print("Fetching Metrics...")
    try:
        response = requests.get(f"{BASE_URL}/metrics/summary?range=last_1h")
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
            
            # Simple assertions
            assert "total_requests" in data
            assert "p95_latency_ms" in data
            assert isinstance(data["provider_split"], list)
            print("✅ Metrics Structure Verified")
        else:
            print(f"❌ Failed to get metrics: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_traffic(5)
    check_metrics()
