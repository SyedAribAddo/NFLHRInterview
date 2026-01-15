from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class SessionCreate(BaseModel):
    name: str
    email: str
    role: str = "Sales"

class SessionResponse(BaseModel):
    session_id: str
    candidate_name: str
    status: str

class QuestionResponse(BaseModel):
    question_id: int
    question_text: str
    is_last: bool

class AnswerResponse(BaseModel):
    transcript: Optional[str]
    score_json: Optional[Dict[str, Any]]
