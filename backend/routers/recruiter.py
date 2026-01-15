from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Session as SessionModel, Answer
from schemas import SessionResponse, AnswerResponse # Need to extend AnswerDetail
from services.blob_service import generate_sas_url
from typing import List, Optional
import json

router = APIRouter(prefix="/recruiter", tags=["recruiter"])

# Extended schemas for recruiter
from pydantic import BaseModel

class AnswerDetail(BaseModel):
    question_id: int
    video_url: str
    transcript: Optional[str]
    score: Optional[dict]

class SessionDetail(BaseModel):
    session_id: str
    candidate_name: str
    candidate_email: str
    role: str
    created_at: str
    status: str
    answers: List[AnswerDetail]

@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(db: Session = Depends(get_session)):
    stmt = select(SessionModel).order_by(SessionModel.created_at.desc())
    sessions = db.exec(stmt).all()
    return [SessionResponse(session_id=s.session_id, candidate_name=s.candidate_name, status=s.status) for s in sessions]

@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session_detail(session_id: str, db: Session = Depends(get_session)):
    stmt = select(SessionModel).where(SessionModel.session_id == session_id)
    session = db.exec(stmt).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    stmt_ans = select(Answer).where(Answer.session_id == session_id).order_by(Answer.question_id)
    answers = db.exec(stmt_ans).all()
    
    ans_details = []
    for a in answers:
        score_dict = None
        if a.score_json:
            try:
                score_dict = json.loads(a.score_json) # Actually it's stored as str in DB models? Yes. "score_json: Optional[str]"
                # Wait, earlier I wrote "score_json = str(score_data)". 
                # Wait, if scoring service returns dict, str(dict) valid python string but maybe not valid JSON if single quotes used.
                # I should double check logic in interview.py.
                # It used str(score_data). Python dict string representation uses single quotes often, which is NOT valid JSON.
                # I MUST FIX interview.py to use json.dumps()!
                # I'll fix this in interview.py shortly or handle ast.literal_eval here.
                # Best to use json.dumps there.
            except:
                pass
        
        # Generate SAS for playback
        video_url = generate_sas_url(a.video_blob_url)
        
        ans_details.append(AnswerDetail(
            question_id=a.question_id,
            video_url=video_url,
            transcript=a.transcript,
            score=score_dict
        ))
        
    return SessionDetail(
        session_id=session.session_id,
        candidate_name=session.candidate_name,
        candidate_email=session.candidate_email,
        role=session.role,
        created_at=session.created_at.isoformat(),
        status=session.status,
        answers=ans_details
    )
