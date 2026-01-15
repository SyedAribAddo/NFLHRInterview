import requests
import json

KEY="sk_V2_hgu_klWh9zKfm5Q_ZVDddBItTsoIfaPnSWCYxfHJdszqmQX5"
USER_ID="3ec4e2037b5443c8a21cae1fca2a9716"

try:
    print("Fetching avatars...")
    resp = requests.get("https://api.heygen.com/v2/avatars", headers={"X-Api-Key": KEY})
    
    if resp.status_code != 200:
        print("Error fetching:", resp.text)
        exit()

    data = resp.json()
    avatars = data.get("data", {}).get("avatars", [])
    
    found = False
    for a in avatars:
        if a["avatar_id"] == USER_ID:
            print(f"FOUND USER AVATAR: {json.dumps(a, indent=2)}")
            found = True
            break
            
    if not found:
        print(f"Avatar ID {USER_ID} NOT FOUND in the list.")
        print("First 3 Avatars found:")
        for a in avatars[:3]:
            print(json.dumps(a, indent=2))
            
except Exception as e:
    print(e)
