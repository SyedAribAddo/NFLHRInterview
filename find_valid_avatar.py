import requests
import json

KEY="sk_V2_hgu_klWh9zKfm5Q_ZVDddBItTsoIfaPnSWCYxfHJdszqmQX5"

try:
    print("Fetching avatars...")
    resp = requests.get("https://api.heygen.com/v2/avatars", headers={"X-Api-Key": KEY})
    
    data = resp.json()
    avatars = data.get("data", {}).get("avatars", [])
    
    print(f"Total: {len(avatars)}")
    
    # Trusted Interactive IDs often used in docs
    trusted_names = ["Angela", "Tyler", "Joshua", "Kristin"]
    
    found_count = 0
    for a in avatars:
        name = a.get('avatar_name', '')
        # Only print if name matches trusted interactive list or seems relevant
        if any(t in name for t in trusted_names):
             print(f"ID: {a.get('avatar_id')} | Name: {name} | Preview: {a.get('preview_image_url')}")
             found_count += 1
             if found_count > 5: break
             
    # Also print the User's ID again carefully to see if it exists
    USER_ID="3ec4e2037b5443c8a21cae1fca2a9716"
    for a in avatars:
        if a['avatar_id'] == USER_ID:
            print(f"\nUSER ID FOUND: {a}")

except Exception as e:
    print(e)
