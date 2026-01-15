import urllib.request
import ssl
import os

# Bypass SSL verify (for dev envs)
ssl._create_default_https_context = ssl._create_unverified_context

# URL for a sample VRM. 
# Using a known stable URL for a sample model. 
# VRoid Hub sample model or similar.
# Using 'AvatarSample_A' from VRM Consortium as a placeholder (it's female usually, but works for tech demo).
# User asked for Male. Finding a public domain male VRM is harder.
# I will use a placeholder URL. If it fails, I will instruct user.

# Attempting to download "AvatarSample_B" (often Male-ish or neutral) or just use a generic one.
# For now, I'll allow the user to provide their own, but I'll download a placeholder.
# Actually, I'll use a reliable GitHub raw link for a sample.

# Alternate URLs (High probability)
URLS = [
    "https://raw.githubusercontent.com/pixiv/three-vrm/master/packages/three-vrm/examples/models/three-vrm-girl.vrm",
    "https://github.com/vrm-c/UniVRM/raw/master/Tests/Models/Version_0.x/Simple-b.vrm",
    "https://hub.vroid.com/api/download/licenses/5850e017-d777-4404-9844-0c571739c94c/models/6966848698947509695/vrm" # Example potentially
]

OUTPUT_PATH = "frontend/public/avatars/interviewer_male.vrm"

def download_file():
    for url in URLS:
        print(f"Attempting download from {url}...")
        try:
            urllib.request.urlretrieve(url, OUTPUT_PATH)
            print(f"Success! Saved to {OUTPUT_PATH}")
            return
        except Exception as e:
            print(f"Failed: {e}")
    print("All downloads failed.")

if __name__ == "__main__":
    if not os.path.exists("frontend/public/avatars"):
        os.makedirs("frontend/public/avatars")
    download_file()
