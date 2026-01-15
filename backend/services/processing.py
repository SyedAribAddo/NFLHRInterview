import os
import tempfile
import json
import time
from models import Interview
from services.blob_storage import BlobServiceClient
import speech_recognition as sr
from moviepy import VideoFileClip
from openai import AzureOpenAI
from dotenv import load_dotenv
from pathlib import Path
import subprocess
import imageio_ffmpeg

env_path = Path(__file__).resolve().parent.parent.parent / '.env' # services -> backend -> root
load_dotenv(dotenv_path=env_path)

# Config (Lazy load or load after dotenv)
AZURE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "interviews")

AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").split("/openai")[0] # Strip suffix
AOAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AOAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "nflinterviewOpenAI")
AOAI_VERSION = "2024-02-15-preview" # Fallback to standard version

def process_interview_background(session_id: str, db_session):
    print(f"[{session_id}] Processing Started (Real Flow)...")
    
    interview = db_session.get(Interview, session_id)
    if not interview or not interview.video_url:
        print("Interview not found or no video.")
        return

    # Update Status
    interview.status = "processing"
    db_session.add(interview)
    db_session.commit()

    temp_video_path = None
    temp_audio_path = None

    try:
        # 1. Download Video from Azure Blob
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=f"{session_id}/full_interview.webm")
        
        fd, temp_video_path = tempfile.mkstemp(suffix=".webm")
        os.close(fd)
        
        with open(temp_video_path, "wb") as my_blob:
            download_stream = blob_client.download_blob()
            data = download_stream.readall()
            my_blob.write(data)
            
        file_size = os.path.getsize(temp_video_path)
        print(f"[{session_id}] Video downloaded: {temp_video_path} ({file_size} bytes)")
        
        if file_size < 1000:
            raise ValueError(f"Downloaded video is too small ({file_size} bytes). Upload likely failed.")

        # 2. Extract Audio (Direct FFMPEG for robustness)
        temp_audio_path = temp_video_path.replace(".webm", ".wav")
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"[{session_id}] Using FFMPEG at: {ffmpeg_exe}")
            
            # -y (overwrite), -i (input), -vn (no video), -acodec pcm_s16le (wav), -ar 16000 (16khz for STT)
            command = [
                ffmpeg_exe, "-y", 
                "-i", temp_video_path,
                "-vn", 
                "-acodec", "pcm_s16le", 
                "-ar", "16000", 
                "-ac", "1", 
                temp_audio_path
            ]
            
            # Run, capturing output (or ignoring stderr if we want to be blind, but capturing is better for log)
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False) # text=False for bytes
            
            if result.returncode != 0:
                print(f"FFMPEG Error details: {result.stderr}")
                # Analyze stderr? Even if "premature", it might have created the file.
                if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 1000:
                    print(f"[{session_id}] Warning: FFMPEG returned error but file exists. Proceeding.")
                else:
                    raise Exception(f"FFMPEG Failed: {result.stderr}")
            else:
                print(f"[{session_id}] Audio extracted to {temp_audio_path}")
            
        except Exception as e:
            print(f"[{session_id}] Audio Extraction Error: {e}")
            raise e

        # 3. Transcribe (Chunked Google Web Speech for Long Audio)
        recognizer = sr.Recognizer()
        full_transcript_parts = []
        
        try:
            with sr.AudioFile(temp_audio_path) as source:
                # Log duration if possible (approximate from file size or just proceed)
                print(f"[{session_id}] Audio File Ready. Starting chunked transcription...")
                
                chunk_duration = 30 # seconds
                while True:
                    audio_data = recognizer.record(source, duration=chunk_duration)
                    if not audio_data.frame_data:
                        break
                        
                    try:
                        # Recognizing chunk... Use 'en-PK' for accent support (fallback to en-IN/en-US if needed)
                        # NOTE: "en-PK" or "en-IN" often handles South Asian accents much better than default.
                        text = recognizer.recognize_google(audio_data, language="en-PK")
                        print(f"[{session_id}] Chunk: {text[:20]}...")
                        full_transcript_parts.append(text)
                    except sr.UnknownValueError:
                        # Silence or unintelligible
                        full_transcript_parts.append("[...]") 
                    except sr.RequestError as e:
                        print(f"[{session_id}] STT Chunk Error: {e}")
                        
            full_transcript = " ".join(full_transcript_parts)
            print(f"[{session_id}] Full Transcript Length: {len(full_transcript)}")
            
        except Exception as e:
             print(f"[{session_id}] Transcription Failed: {e}")
             full_transcript = "(Transcription Failed)"

        interview.transcript_text = full_transcript
        
        # 4. Score with Azure OpenAI
        if not full_transcript or len(full_transcript) < 5:
             # Skip scoring data if empty
             pass
        else:
             client = AzureOpenAI(
                 azure_endpoint=AOAI_ENDPOINT,
                 api_key=AOAI_KEY,
                 api_version=AOAI_VERSION
             )
             
             system_prompt = """
             You are an expert HR Interviewer. Analyze the following interview transcript.
             The interview consisted of 3 questions:
             1. Sales experience.
             2. Time missed target.
             3. Why National Foods.
             
             Extract the answers (implicitly) and score them.
             Structure your response STRICTLY as JSON with the following schema:
             {
               "q1": { "score": 1-5, "reasoning": "..." },
               "q2": { "score": 1-5, "reasoning": "..." },
               "q3": { "score": 1-5, "reasoning": "..." },
               "overall": {
                   "communication_clarity": 1-5,
                   "sales_mindset_ownership": 1-5,
                   "resilience_learning": 1-5,
                   "role_motivation": 1-5,
                   "recommendation": "Strong Yes | Yes | Maybe | No",
                   "summary": "..."
               }
             }
             Do not include markdown formatting. Just the JSON.
             """
             
             response = client.chat.completions.create(
                 model=AOAI_DEPLOYMENT,
                 messages=[
                     {"role": "system", "content": system_prompt},
                     {"role": "user", "content": f"Transcript:\n{full_transcript}"}
                 ],
                 response_format={ "type": "json_object" }
             )
             
             result_json_str = response.choices[0].message.content
             scores = json.loads(result_json_str)
             interview.scores = scores
             print(f"[{session_id}] Scoring Complete.")

        interview.status = "completed"
        db_session.add(interview)
        db_session.commit()

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(f"[{session_id}] Processing Failed: {e}")
        print(err_msg)
        
        with open("processing_debug.log", "a") as f:
            f.write(f"\n[{session_id}] ERROR:\n{err_msg}\n----------------\n")
            
        interview.status = "failed"
        db_session.add(interview)
        db_session.commit()
    finally:
        # Cleanup
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
