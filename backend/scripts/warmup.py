import sys
import time
import requests

def warmup(api_url: str):
    """
    Sends a test request to the deployed assess API to wake up the 
    service and ensure all models are loaded into memory.
    """
    if not api_url.startswith("http"):
        api_url = f"https://{api_url}"
        
    endpoint = f"{api_url}/api/v1/assess"
    print(f"Warming up API at {endpoint}...")
    
    # Minimal viable payload for a prediction
    payload = {
        "name": "Warmup User",
        "email": "warmup@loansense.dev",
        "phone": "+919876543210",
        "pan_number": "ABCDE1234F",
        "income": 50000,
        "loan_amount": 100000,
        "loan_term_months": 24,
        "existing_emi": 5000,
        "employment_type": "Salaried"
    }
    
    start_time = time.time()
    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            print(f"SUCCESS: API warmed up in {elapsed:.2f} seconds.")
            return 0
        else:
            print(f"FAILED: API returned {response.status_code}")
            print(response.text)
            return 1
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to connect to API: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python warmup.py <api_url>")
        print("Example: python warmup.py loansense-api.up.railway.app")
        sys.exit(1)
        
    sys.exit(warmup(sys.argv[1]))
