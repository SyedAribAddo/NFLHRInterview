"""
D-ID Avatar Service
Generates lip-synced video avatars using D-ID's Talks API with ElevenLabs audio.
"""
import os
import time
import json
import httpx
from dotenv import load_dotenv
from pathlib import Path
from services.tts import generate_audio_bytes
from services.blob_storage import upload_audio_to_blob

# Load Env
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Config
DID_API_KEY = os.getenv("DID_API_KEY", "")
DID_PRESENTER_URL = os.getenv("DID_PRESENTER_URL", "https://create-images-results.d-id.com/DefaultPresetImage/Matt_m/model.png")
DID_BASE_URL = "https://api.d-id.com"

# Persistent cache file
CACHE_FILE = Path(__file__).resolve().parent.parent / "avatar_cache.json"

# In-memory cache (loaded from file on startup)
video_cache = {}

def load_cache():
    """Load video cache from JSON file."""
    global video_cache
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                video_cache = json.load(f)
            print(f"Loaded {len(video_cache)} cached avatar videos from {CACHE_FILE}")
        except Exception as e:
            print(f"Failed to load cache: {e}")
            video_cache = {}
    else:
        video_cache = {}

def save_cache():
    """Save video cache to JSON file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(video_cache, f, indent=2)
        print(f"Saved {len(video_cache)} avatar videos to cache")
    except Exception as e:
        print(f"Failed to save cache: {e}")

# Load cache on module import
load_cache()

def get_auth_header():
    """Get D-ID auth header (Basic Auth with API key)."""
    return {
        "Authorization": f"Basic {DID_API_KEY}",
        "Content-Type": "application/json"
    }

async def create_talk(audio_url: str, expression: str = "neutral") -> dict:
    """
    Create a D-ID talk video from audio URL.
    Returns the talk ID and status.
    """
    payload = {
        "source_url": DID_PRESENTER_URL,
        "script": {
            "type": "audio",
            "audio_url": audio_url
        },
        "config": {
            "stitch": True,
            "fluent": True
        }
    }
    
    # Add expression if not neutral
    if expression != "neutral":
        payload["config"]["driver_expressions"] = {
            "expressions": [{"expression": expression, "start_frame": 0}]
        }
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{DID_BASE_URL}/talks",
            headers=get_auth_header(),
            json=payload
        )
        
        if response.status_code not in [200, 201]:
            print(f"D-ID Create Talk Error: {response.status_code} - {response.text}")
            return {"error": response.text}
        
        return response.json()

async def get_talk_status(talk_id: str) -> dict:
    """Poll D-ID for talk status."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{DID_BASE_URL}/talks/{talk_id}",
            headers=get_auth_header()
        )
        return response.json()

async def wait_for_talk(talk_id: str, max_wait: int = 120) -> dict:
    """
    Poll until talk is done or failed.
    Returns the final talk object with result_url.
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        result = await get_talk_status(talk_id)
        status = result.get("status", "unknown")
        
        print(f"Talk {talk_id}: {status}")
        
        if status == "done":
            return result
        elif status in ["error", "rejected"]:
            return {"error": result.get("error", "Unknown error")}
        
        # Wait before polling again
        await asyncio_sleep(2)
    
    return {"error": "Timeout waiting for video"}

async def asyncio_sleep(seconds: float):
    """Async sleep helper."""
    import asyncio
    await asyncio.sleep(seconds)

async def generate_avatar_video(text: str, cache_key: str = None, expression: str = "neutral") -> dict:
    """
    Full pipeline: Text -> ElevenLabs Audio -> Azure Blob -> D-ID Video
    
    Args:
        text: The text to speak
        cache_key: Optional key for caching (e.g., "intro", "q1", "nudge")
        expression: Facial expression ("neutral", "happy", "serious")
    
    Returns:
        {"video_url": "...", "duration": ...} or {"error": "..."}
    """
    # Check cache first (includes persisted cache)
    if cache_key and cache_key in video_cache:
        print(f"Cache hit for {cache_key}")
        return video_cache[cache_key]
    
    try:
        # 1. Generate audio via ElevenLabs
        print(f"Generating audio for: {text[:50]}...")
        audio_bytes = generate_audio_bytes(text)
        
        if not audio_bytes:
            return {"error": "TTS generation failed"}
        
        # 2. Upload audio to Azure Blob (get public URL)
        print("Uploading audio to Azure...")
        audio_url = upload_audio_to_blob(audio_bytes, f"avatar_{cache_key or 'temp'}.mp3")
        
        if not audio_url:
            return {"error": "Audio upload failed"}
        
        print(f"Audio URL: {audio_url}")
        
        # 3. Create D-ID talk
        print("Creating D-ID talk...")
        talk_result = await create_talk(audio_url, expression)
        
        if "error" in talk_result:
            return talk_result
        
        talk_id = talk_result.get("id")
        if not talk_id:
            return {"error": "No talk ID returned"}
        
        # 4. Wait for video to be ready
        print(f"Waiting for video {talk_id}...")
        final_result = await wait_for_talk(talk_id)
        
        if "error" in final_result:
            return final_result
        
        video_url = final_result.get("result_url")
        duration = final_result.get("duration", 0)
        
        result = {
            "video_url": video_url,
            "duration": duration,
            "talk_id": talk_id
        }
        
        # Cache the result (in-memory + persist to file)
        if cache_key:
            video_cache[cache_key] = result
            save_cache()  # Persist to JSON file
        
        return result
        
    except Exception as e:
        print(f"Avatar generation error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

async def pre_generate_interview_videos() -> dict:
    """
    Pre-generate all interview videos for a session.
    Returns a dict mapping keys to video URLs.
    Skips generation for already-cached videos.
    """
    from services.tts import QUESTION_SCRIPTS
    
    videos = {}
    keys_to_generate = ["intro", "q1", "q2", "q3", "outro", "nudge", "rephrase"]
    
    # Check what's already cached
    cached = [k for k in keys_to_generate if k in video_cache]
    if cached:
        print(f"Already cached: {cached}")
        for k in cached:
            videos[k] = video_cache[k]
    
    # Generate missing videos
    missing = [k for k in keys_to_generate if k not in video_cache]
    
    if not missing:
        print("All videos already cached!")
        return videos
    
    print(f"Generating missing videos: {missing}")
    
    texts = {
        "intro": QUESTION_SCRIPTS.get("intro", "Welcome to National Foods. Let's begin your interview."),
        "q1": QUESTION_SCRIPTS.get(1, "Question 1"),
        "q2": QUESTION_SCRIPTS.get(2, "Question 2"),
        "q3": QUESTION_SCRIPTS.get(3, "Question 3"),
        "outro": QUESTION_SCRIPTS.get("outro", "Thank you for your time. We'll be in touch soon."),
        "nudge": "Could you elaborate a bit more on that? I'd love to hear more details.",
        "rephrase": "Let me rephrase that for you."
    }
    
    expressions = {
        "intro": "happy",
        "outro": "happy",
        "q1": "neutral",
        "q2": "neutral",
        "q3": "neutral",
        "nudge": "neutral",
        "rephrase": "neutral"
    }
    
    for key in missing:
        print(f"Pre-generating: {key}")
        result = await generate_avatar_video(
            texts[key],
            cache_key=key,
            expression=expressions.get(key, "neutral")
        )
        videos[key] = result
    
    return videos

def get_cached_video(key: str) -> dict:
    """Get a cached video URL by key."""
    return video_cache.get(key, {"error": "Video not cached"})

def clear_cache():
    """Clear the video cache (both memory and file)."""
    global video_cache
    video_cache = {}
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
    print("Cache cleared")

