import requests
import json
import os

# Hardcoded for direct test
KEY="sk_V2_hgu_klWh9zKfm5Q_ZVDddBItTsoIfaPnSWCYxfHJdszqmQX5"
AVATAR="Pedro_ProfessionalLook_public"
# VOICE="cjVigY5qzO86Huf0OWal"

url = "https://api.heygen.com/v1/streaming.new"
headers = {
    "X-Api-Key": KEY,
    "Content-Type": "application/json"
}

# Test 1: Minimal Payload (No Voice)
payload_minimal = {
    "quality": "medium",
    "avatar_name": AVATAR
}

results = []

print(f"Testing Payload 1 (No Voice): {json.dumps(payload_minimal)}")
resp = requests.post(url, headers=headers, json=payload_minimal)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
results.append(f"Payload 1 (No Voice): Status {resp.status_code}\nResponse: {resp.text}\n")

# Test 2: With Eric Voice
payload_voice = {
    "quality": "medium",
    "avatar_name": AVATAR,
    "voice": { "voice_id": "cjVigY5qzO86Huf0OWal" }
}

print(f"\nTesting Payload 2 (With Voice - Eric): {json.dumps(payload_voice)}")
resp = requests.post(url, headers=headers, json=payload_voice)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
results.append(f"Payload 2 (With Voice): Status {resp.status_code}\nResponse: {resp.text}\n")

# Test 3: With Pedro Default Voice
# "default_voice": "fbc81b179407457688c45c0f250ec3ce"
payload_default = {
    "quality": "medium",
    "avatar_name": AVATAR,
    "voice": { "voice_id": "fbc81b179407457688c45c0f250ec3ce" }
}

print(f"\nTesting Payload 3 (Default Voice): {json.dumps(payload_default)}")
resp = requests.post(url, headers=headers, json=payload_default)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
results.append(f"Payload 3 (Default Voice): Status {resp.status_code}\nResponse: {resp.text}\n")

with open("debug_results.txt", "w") as f:
    f.writelines(results)
