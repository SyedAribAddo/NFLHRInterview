from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Form
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from database import get_session
from models import Interview
from services.blob_storage import upload_video_to_blob
from services.processing import process_interview_background
from services.tts import get_question_audio_stream
import uuid

router = APIRouter(prefix="/api/interview", tags=["interview"])
recruiter_router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])

@router.get("/audio/{key}")
def get_audio(key: str):
    """Stream audio for a specific question/prompt."""
    # Convert key to int if digit, else keep string (intro/outro)
    lookup_key = int(key) if key.isdigit() else key
    audio_stream = get_question_audio_stream(lookup_key)
    
    if not audio_stream:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    # Explicit CORS headers for Web Audio API analysis
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": "Content-Length, Content-Type",
    }
    return StreamingResponse(audio_stream, media_type="audio/mpeg", headers=headers)

from services.tts import generate_audio_stream
from pydantic import BaseModel

class SynthesizeRequest(BaseModel):
    text: str

@router.post("/synthesize")
def synthesize(req: SynthesizeRequest):
    """Generate audio for arbitrary text (Nudges/Rephrases)."""
    audio_stream = generate_audio_stream(req.text)
    if not audio_stream:
        raise HTTPException(status_code=500, detail="TTS generation failed")
    return StreamingResponse(audio_stream, media_type="audio/mpeg")


    return StreamingResponse(audio_stream, media_type="audio/mpeg")

from fastapi import Request

@router.post("/analyze")
async def analyze_response(request: Request):
    """
    Analyze the uploaded audio chunk to decide the next orchestration step.
    Uses raw Request parsing to avoid Pydantic 422 Coercion errors.
    """
    import shutil
    import tempfile
    import os
    from services.analysis import analyze_answer_intent
    
    # 1. Manual Form Parsing (Fail-Safe)
    try:
        form = await request.form()
        file = form.get("file")
        question_text = form.get("question_text", "")
        attempt_str = form.get("attempt", "0")
        
        # Safe Cast
        try:
            attempt_int = int(attempt_str)
        except:
            attempt_int = 0
            
        print(f"Analyzing: File={file.filename if file else 'None'}, Q='{question_text}', Attempt={attempt_int}")
        
        if not file:
            print("No file received. Defaulting to Next.")
            return {"action": "next", "reason": "No Audio File", "transcript": ""}

    except Exception as e:
        print(f"Form Parse Error: {e}")
        return {"action": "next", "reason": "Form Parse Error", "transcript": ""}

    # Save Temp Audio
    fd, temp_path = tempfile.mkstemp(suffix=".webm")
    os.close(fd)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(temp_path)
        print(f"Saved audio file: {file_size} bytes")
        
        # Convert WebM to WAV
        wav_path = temp_path + ".wav"
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", temp_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            # Try to continue anyway, maybe the wav was created
        
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
            print("WAV conversion failed or file too small")
            return {"action": "nudge", "reason": "Audio conversion failed", "transcript": ""}
        
        print(f"WAV file created: {os.path.getsize(wav_path)} bytes")
        
        result = analyze_answer_intent(wav_path, str(question_text), attempt_int)
        print(f"Analysis result: {result}")
        return result
        
    except Exception as e:
        print(f"Analysis Error: {e}")
        import traceback
        traceback.print_exc()
        return {"action": "next", "reason": f"Error: {str(e)}", "transcript": ""}
    finally:
        # Cleanup
        if os.path.exists(temp_path): os.remove(temp_path)
        if os.path.exists(temp_path + ".wav"): os.remove(temp_path + ".wav")

@router.post("/start")
def start_interview(data: dict, db: Session = Depends(get_session)):
    """Start a new interview session."""
    session_id = str(uuid.uuid4())
    interview = Interview(
        id=session_id,
        candidate_name=data.get("name"),
        candidate_email=data.get("email")
    )
    db.add(interview)
    db.commit()
    return {"sessionId": session_id}

@router.post("/{session_id}/complete")
@router.post("/{session_id}/complete")
async def complete_interview(
    session_id: str, 
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_session)
):
    """Upload video and trigger processing (Robust parsing)."""
    interview = db.get(Interview, session_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
        
    print(f"Uploading video for {session_id}...")
    
    try:
        form = await request.form()
        file = form.get("file")
        if not file:
             raise HTTPException(status_code=422, detail="No file uploaded")
             
        content = await file.read()
        
        # Upload to Azure
        video_url = upload_video_to_blob(content, session_id)
        interview.video_url = video_url
        interview.status = "uploaded"
        db.add(interview)
        db.commit()
        
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(f"UPLOAD FAILED for {session_id}: {e}")
        with open("upload_error.log", "a") as f:
            f.write(f"[{session_id}] {err_msg}\n")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        
    # Trigger Background Processing
    background_tasks.add_task(process_interview_background, session_id, db)
    
    return {"status": "processing", "video_url": video_url}

@recruiter_router.get("/interviews")
def list_interviews(db: Session = Depends(get_session)):
    interviews = db.exec(select(Interview)).all()
    return interviews

from services.blob_storage import upload_video_to_blob, generate_sas_url

# ...

@recruiter_router.get("/interviews/{session_id}")
def get_interview(session_id: str, db: Session = Depends(get_session)):
    interview = db.get(Interview, session_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Generate SAS Token for secure playback
    if interview.video_url:
        interview.video_url = generate_sas_url(interview.video_url)
        
    return interview
