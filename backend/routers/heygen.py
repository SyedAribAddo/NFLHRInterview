from fastapi import APIRouter, HTTPException, Body
import requests
import os
import uuid

router = APIRouter(prefix="/heygen", tags=["heygen"])

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID") # e.g. "Anna_public_3_20240108"
# Note: streaming avatar might need a specific avatar ID or voice ID. 
# The user provided HEYGEN_AVATAR_ID.

@router.post("/token")
def get_token():
    """Generate a temporary access token for the HeyGen Streaming SDK."""
    url = "https://api.heygen.com/v1/streaming.create_token"
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(url, headers=headers)
        if resp.status_code != 200:
             print(f"HEYGEN ERROR: {resp.status_code} - {resp.text}")
             raise HTTPException(status_code=500, detail=f"HeyGen Token Failed: {resp.text}")
        
        data = resp.json()
        return data["data"] # Returns { "token": "..." }
    except Exception as e:
        print(f"HEYGEN EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session")
def create_session():
    """Create a new Streaming Session server-side (Preferred Architecture)."""
    url = "https://api.heygen.com/v1/streaming.new"
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Minimal Safe Payload (User Step 5 + Eric Voice)
    # Removing video_encoding to use server defaults (less chance of error)
    payload = {
        "quality": "medium",
        "avatar_name": HEYGEN_AVATAR_ID,
        "voice": { 
            "voice_id": "cjVigY5qzO86Huf0OWal" 
        }
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
             print(f"HEYGEN SESSION ERROR: {resp.status_code} - {resp.text}")
             raise HTTPException(status_code=500, detail=f"HeyGen Session Failed: {resp.text}")
        
        data = resp.json()
        # Returns { "data": { "session_id": "...", "access_token": "...", "url": "...", "ice_servers": [...] } }
        return data["data"]
    except Exception as e:
        print(f"HEYGEN SESSION EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Keep /session for server-side init if needed, but SDK usually prefers token.
# We can deprecate /session or keep it as alternative.

@router.post("/speak")
def speak(session_id: str = Body(...), text: str = Body(...)):
    """Make the avatar speak."""
    url = "https://api.heygen.com/v1/streaming.task"
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "session_id": session_id,
        "text": text,
        "task_type": "test" # or 'speak'? V1 API uses 'test' for speak?
        # Actually newer API is /v1/streaming.task with task_type="repeat" or similar?
        # Let's use the standard "talk" or "speak" task.
        # Depending on version: /v1/streaming.task
        # { session_id, text, task_type: "repeat" }
    }
    
    # Official docs often use task_type="repeat" to just say text.
    payload["task_type"] = "repeat" 
    
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"HeyGen Speak Failed: {resp.text}")
    
    return {"status": "success"}

@router.post("/stop")
def stop_session(session_id: str = Body(...)):
    url = "https://api.heygen.com/v1/streaming.stop"
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    requests.post(url, json={"session_id": session_id}, headers=headers)
    return {"status": "stopped"}
