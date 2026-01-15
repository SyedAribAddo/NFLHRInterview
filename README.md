# National Foods — HireVue-Style Interview Demo

This project is a functional demo of an AI-powered video interview system.

## Features
- **Digital Interviewer**: HeyGen Streaming Avatar asks questions.
- **Video Recording**: Candidate records answer via browser (WebRTC).
- **Storage**: Videos uploaded to Azure Blob Storage (private container).
- **Analysis**:
  - Transcription via ElevenLabs.
  - Scoring & Rubric via Azure OpenAI.
- **Recruiter Dashboard**: View sessions, play videos, and see AI scores.

## Prerequisites
- Docker & Docker Compose
- Environment variables (provided in `.env`)

## Project Structure
- `frontend/`: Next.js 14 (App Router), Tailwind CSS, TypeScript.
- `backend/`: FastAPI, SQLModel (SQLite), Azure/ElevenLabs/HeyGen integrations.

## Setup & Run

1. **Environment Variables**:
   Ensure the `.env` file in the root directory is populated with your API keys.

2. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

3. **Access the App**:
   - **Candidate Interface**: [http://localhost:3000](http://localhost:3000)
   - **Recruiter Dashboard**: [http://localhost:3000/review](http://localhost:3000/review)
   - **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Key Workflows
1. **Start Interview**: enter name/email on landing page.
2. **Avatar Question**: The avatar speaks the question (HeyGen).
3. **Record Answer**: Click "Start Answer", record, then "Stop".
4. **Upload & Process**: Video uploads to Azure -> Transcribed -> Scored.
5. **Review**: Go to `/review` to see the results.

## Troubleshooting
- **Microphone/Camera**: Ensure browser permissions are granted.
- **Avatar not loading**: Check `HEYGEN_API_KEY` and Console logs. The system uses a generated token flow.
- **Upload fails**: Check Azure Storage connection string.
