import os
import time
import hashlib
import requests

from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("GROWW_API_KEY")
api_secret = os.getenv("GROWW_API_SECRET")

if not api_key or not api_secret:
    raise RuntimeError(
        "GROWW_API_KEY or GROWW_API_SECRET is missing from .env"
    )


# Generate current timestamp
timestamp = str(int(time.time()))

# Groww checksum = SHA256(api_secret + timestamp)
checksum_input = api_secret + timestamp
checksum = hashlib.sha256(
    checksum_input.encode("utf-8")
).hexdigest()


# Request an access token
url = "https://api.groww.in/v1/token/api/access"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

payload = {
    "key_type": "approval",
    "checksum": checksum,
    "timestamp": timestamp,
}

response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=10,
)

print("HTTP status:", response.status_code)
print("Groww response:", response.text)

response.raise_for_status()

data = response.json()

if data.get("status") == "FAILURE":
    raise RuntimeError(f"Groww authentication failed: {data}")

access_token = data["token"]

print("Groww authentication successful.")
print("Access token received:", bool(access_token))
print("Token length:", len(access_token))
print("API key loaded:", bool(api_key))
print("API secret loaded:", bool(api_secret))
print("API key length:", len(api_key))
print("API secret length:", len(api_secret))
print("API key starts with:", api_key[:4])
print("API key ends with:", api_key[-4:])