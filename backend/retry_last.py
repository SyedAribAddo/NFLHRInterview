from sqlmodel import Session, select, create_engine
from models import Interview
from services.processing import process_interview_background
import os
from dotenv import load_dotenv
from pathlib import Path

# Load Env
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Verify Env
conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
print(f"Env Loaded. Conn Str Pre: {conn_str[:5] if conn_str else 'None'}")

# Setup DB
sqlite_url = "sqlite:///./sessions.db"
engine = create_engine(sqlite_url)

def retry_latest():
    with Session(engine) as session:
        # Get latest
        statement = select(Interview).order_by(Interview.created_at.desc()).limit(1)
        result = session.exec(statement).first()
        
        if not result:
            print("No interviews found.")
            return

        print(f"Retrying Session: {result.id} (Status: {result.status})")
        
        # Process
        try:
            process_interview_background(result.id, session)
            print("Retry script finished success.")
        except Exception as e:
            print(f"Retry script crashed: {e}")

if __name__ == "__main__":
    retry_latest()
