from sqlmodel import Session, select, create_engine
from models import Interview
import json

sqlite_url = "sqlite:///./sessions.db"
engine = create_engine(sqlite_url)

def inspect_latest():
    with Session(engine) as session:
        statement = select(Interview).order_by(Interview.created_at.desc()).limit(1)
        result = session.exec(statement).first()
        
        if not result:
            print("No interviews found.")
            return

        print(f"Session ID: {result.id}")
        print(f"Status: {result.status}")
        print(f"Transcript (Length): {len(result.transcript_text) if result.transcript_text else 0}")
        print(f"Scoring Data: {result.scores}")

if __name__ == "__main__":
    inspect_latest()
