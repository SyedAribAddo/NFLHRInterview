import os
from elevenlabs.client import ElevenLabs

API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "WoB1yCV3pS7cFlDlu8ZU")

client = ElevenLabs(api_key=API_KEY)

QUESTIONS = {
    1: "Walk me through your sales experience and the types of products you’ve sold.",
    2: "Describe a time you missed target — what did you change afterward?",
    3: "Why National Foods, and why this sales role?",
    "intro": "Hi, my name is Salman. I’ll be conducting your interview today. I'm going to ask you three questions. Please answer naturally. Let's begin.",
    "outro": "Thank you. This concludes the interview. We will be in touch soon."
}

def generate_audio_stream(text: str):
    """Generates audio stream for arbitrary text."""
    if not text: return None
    return client.text_to_speech.convert(
        voice_id=VOICE_ID,
        output_format="mp3_44100_128",
        text=text,
        model_id="eleven_turbo_v2_5"
    )

def get_question_audio_stream(key):
    """Generates audio for the given key (1, 2, 3, 'intro', 'outro')."""
    text = QUESTIONS.get(key)
    if not text:
        return None
    return generate_audio_stream(text)
