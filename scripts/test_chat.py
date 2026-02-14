import requests
import json
import sys

def test_chat():
    url = "http://localhost:8000/chat"
    payload = {
        "prompt": "Explain the concept of recursion.",
        "task_type": "explanation",
        "preferred_model": "llama-3.3-70b-versatile"
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        
        try:
            data = response.json()
            print("Response Body:")
            print(json.dumps(data, indent=2))
        except:
            print("Raw Response:", response.text)

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_chat()
