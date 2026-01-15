import os
import json
from openai import AzureOpenAI

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
API_VERSION = "2024-02-15-preview" # or 2025-04-01-preview as in User env

client = AzureOpenAI(
    azure_endpoint=ENDPOINT,
    api_key=API_KEY,
    api_version=API_VERSION
)

def score_answer(question: str, transcript: str) -> dict:
    system_prompt = """
    You are an expert sales recruiter for National Foods. 
    Score the candidate's answer based on the following rubric.
    Return STRICT JSON only. No markdown formatting.
    Target JSON format:
    {
      "communication_clarity": 1-5,
      "sales_mindset_ownership": 1-5,
      "objection_handling": 1-5,
      "planning_execution": 1-5,
      "customer_orientation": 1-5,
      "notes": ["bullet 1","bullet 2"],
      "recommendation": "Strong Yes|Yes|Maybe|No"
    }
    """
    
    user_prompt = f"""
    Question: {question}
    Candidate Answer Transcript: "{transcript}"
    
    Evaluate the answer.
    """
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME, # In Azure, model needs to be the deployment name usually
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Scoring error: {e}")
        return {
            "error": str(e),
            "communication_clarity": 0,
            "sales_mindset_ownership": 0,
            "objection_handling": 0,
            "planning_execution": 0,
            "customer_orientation": 0,
            "notes": ["Error during scoring"],
            "recommendation": "No"
        }
