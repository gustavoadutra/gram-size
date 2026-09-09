import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
API = os.getenv("TELEGRAM_API_KEY")

client = OpenAI()

audio_file = open("/home/aki/Desktop/gram-size/openai_utils/teste.mp3", "rb")

transcription = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file
)

print(transcription.text)