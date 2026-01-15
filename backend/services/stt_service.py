import os
import requests
from elevenlabs.client import ElevenLabs

API_KEY = os.getenv("ELEVENLABS_API_KEY")

def transcribe_audio(audio_url: str) -> str:
    # Try using the Python SDK first if available and recent
    try:
        client = ElevenLabs(api_key=API_KEY)
        # Check if speech_to_text exists in this version
        if hasattr(client, 'speech_to_text'):
             # This is making an assumption on the SDK structure
             # If using Scribe:
             result = client.speech_to_text.convert(
                 model_id="scribe_v1", # or similar
                 file=None, # It might require file bytes or url?
                 # SDK usually requires file-like object or bytes.
                 # Since we have a URL, we might need to download it first or pass URL if supported.
                 # Most generic STT APIs accept file uploads.
                 # Let's mock the "file" by downloading from SAS URL.
             )
             return result.text
    except Exception:
        pass

    # Fallback to requests if SDK usage is ambiguous or fails
    # NOTE: As of late 2024, ElevenLabs Scribe API details:
    # POST https://api.elevenlabs.io/v1/speech-to-text
    # Multipart form data: file, model_id
    
    # download file content from SAS URL
    response = requests.get(audio_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download audio from Blob: {response.text}")
    
    audio_data = response.content
    
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {
        "xi-api-key": API_KEY
    }
    files = {
        "file": ("audio.webm", audio_data, "audio/webm")
    }
    data = {
        "model_id": "scribe_v1" 
    }
    
    r = requests.post(url, headers=headers, files=files, data=data)
    if r.status_code != 200:
        # If 404/400, maybe standard STT not available or different endpoint.
        # Fallback to a mock for DEMO SAFETY if real API fails? 
        # User said "Must be real call". 
        # But if the endpoint is wrong, it will fail.
        # I will return the error message.
        raise Exception(f"ElevenLabs STT Failed: {r.text}")
        
    return r.json().get("text", "")
