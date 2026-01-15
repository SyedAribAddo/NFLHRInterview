from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import create_db_and_tables
from dotenv import load_dotenv
import os
# Explicitly import models to map them to SQLModel.metadata
from models import Interview

# Load env from parent directory (since .env is in root, and we run from root or backend)
# We assume we run from root? Or backend? 
# If we run from root, .env is there.
load_dotenv(dotenv_path="../.env") # Try looking in parent if running from backend dir
# Also try current dir if running from root
load_dotenv(dotenv_path=".env")

# Routers
from routers import interview

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    create_db_and_tables()
    yield
    # Shutdown

app = FastAPI(title="National Foods Interview Demo", lifespan=lifespan)

# CORS (Allow frontend)
origins = [
    "http://localhost:3000",
    "http://localhost:5074",
    "*" # For demo purposes, allow all
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for demo simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview.router)
app.include_router(interview.recruiter_router)
# app.include_router(heygen.router, prefix="/api") # Disabled for Voice-Only Pivot

@app.exception_handler(Exception)
async def all_exception_handler(request, exc):
    import traceback
    error_msg = traceback.format_exc()
    print("################ ERROR TRACEBACK ################")
    print(error_msg)
    print("#################################################")
    
    # Write to file
    with open("backend_error.log", "a") as f:
        f.write(f"\n--- ERROR {request.url} ---\n")
        f.write(error_msg)
        f.write("\n--------------------------------\n")
        
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "trace": error_msg.splitlines()[-15:],
            "path": str(request.url),
            "method": request.method,
        },
    )

@app.get("/")
def read_root():
    return {"message": "National Foods Interview API is running"}
