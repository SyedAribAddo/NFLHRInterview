import os
import speech_recognition as sr
import tempfile
from openai import AzureOpenAI
from dotenv import load_dotenv
from pathlib import Path

# Load Env
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Config
AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").split("/openai")[0]
AOAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AOAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "nflinterviewOpenAI")
AOAI_VERSION = "2024-02-15-preview"

recognizer = sr.Recognizer()

def analyze_answer_intent(audio_file_path: str, question_text: str, attempt: int):
    """
    Transcribes audio and determines if the answer is sufficient, 
    needs a nudge, or implies a lack of knowledge/understanding.
    """
    
    # 1. Transcribe
    transcript = ""
    try:
        with sr.AudioFile(audio_file_path) as source:
            # Record the data
            audio_data = recognizer.record(source)
            # Use Google Speech Recognition (free, good enough for short chunks)
            # Use 'en-US' or 'en-PK' based on preference.
            transcript = recognizer.recognize_google(audio_data)
            print(f"Transcript: {transcript}")
    except sr.UnknownValueError:
        transcript = ""
        print("Transcript: (Unintelligible/Silence)")
    except Exception as e:
        print(f"STT Error: {e}")
        return {"action": "next", "reason": "STT Failed", "transcript": ""}

    # 2. Heuristics (Fast Pass)
    word_count = len(transcript.split())
    
    # Very short silence/noise
    if word_count < 2:
        if attempt < 2:
            return {"action": "nudge", "reason": "Silence or Noise", "transcript": transcript}
        else:
            return {"action": "next", "reason": "Max Attempts (Silence)", "transcript": transcript}

    # 3. LLM Intent Analysis
    try:
        if not AOAI_KEY or not AOAI_ENDPOINT:
            raise Exception("Azure OpenAI Not Configured")

        client = AzureOpenAI(
            azure_endpoint=AOAI_ENDPOINT,
            api_key=AOAI_KEY,
            api_version=AOAI_VERSION
        )

        system_prompt = f"""
        You are an interview conductor optimization engine.
        Analyze the candidate's response to the question: "{question_text}"
        Current Attempt: {attempt} (0=First, 1=Nudge, 2=Rephrase)
        
        Determine the next best action:
        - "next": Answer is sufficient, or they explicitly said they don't know and want to move on.
        - "nudge": Answer is too vague, short, or incomplete.
        - "rephrase": Candidate is confused, asks for clarification, or says "I don't understand".

        Rules:
        - If they explicitly ask: "Could you rephrase?", "What do you mean?", "I don't understand", "Repeat that" -> ACTION: "rephrase".
        - If they say "I don't know" implies they didn't get it -> ACTION: "rephrase".
        - If they say "Skip", "Pass", "Next" -> ACTION: "next".
        - If they give a short/vague answer (e.g., "Nothing", "I did sales") -> ACTION: "nudge".
        - If they give a detailed answer -> ACTION: "next".
        
        Return JSON: {{ "action": "next" | "nudge" | "rephrase", "reason": "..." }}
        """

        response = client.chat.completions.create(
            model=AOAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            response_format={ "type": "json_object" }
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        result["transcript"] = transcript
        return result

    except Exception as e:
        print(f"LLM Analysis Failed: {e}")
        # Fallback to Word Count logic
        if word_count < 5 and attempt < 2:
             return {"action": "nudge", "reason": "Too Short (Fallback)", "transcript": transcript}
        return {"action": "next", "reason": "Fallback Default", "transcript": transcript}
