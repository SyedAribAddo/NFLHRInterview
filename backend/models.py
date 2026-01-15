from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON
from datetime import datetime

class Interview(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    candidate_name: str
    candidate_email: str
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="started") # started, uploaded, processed, completed, failed
    
    video_url: Optional[str] = None
    transcript_text: Optional[str] = None # Full transcript
    
    # JSON Fields for structured data
    # scores: { "q1": {...}, "q2": {...}, "q3": {...}, "overall": ... }
    scores: Optional[dict] = Field(default=None, sa_type=JSON) 
    
    transcript_segments: Optional[List[dict]] = Field(default=None, sa_type=JSON)
