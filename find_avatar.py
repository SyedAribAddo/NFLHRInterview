import requests
import json

KEY="sk_V2_hgu_klWh9zKfm5Q_ZVDddBItTsoIfaPnSWCYxfHJdszqmQX5"

try:
    print("Fetching avatars...")
    resp = requests.get("https://api.heygen.com/v2/avatars", headers={"X-Api-Key": KEY})
    
    if resp.status_code != 200:
        print(f"Error: {resp.status_code}")
        exit()

    data = resp.json()
    avatars = data.get("data", {}).get("avatars", [])
    
    print(f"Total Avatars: {len(avatars)}")
    
    # Filter for possible interactive ones
    interactive = []
    for a in avatars:
        # Check various flags that might indicate streaming/interactive support
        # Note: The API response format isn't fully documented here, so printing structure of first one helps.
        interactive.append(a)
        
    print("First 5 IDs and Names:")
    for a in interactive[:5]:
         print(f"ID: {a.get('avatar_id')} | Name: {a.get('avatar_name')} | Type: {a.get('avatar_type')} | Properties: {list(a.keys())}")

except Exception as e:
    print(e)
