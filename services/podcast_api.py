import os
import httpx
from typing import List, Dict
from google.cloud import speech_v1p1beta1 as speech
from google.oauth2 import service_account

class PodcastAPI:
    def __init__(self):
        self.credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
        self.client = speech.SpeechClient(credentials=self.credentials)

    async def fetch_transcript(self, audio_url: str) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_url)
                audio_content = response.content

            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=44100,
                language_code="en-US",
                enable_automatic_punctuation=True
            )

            operation = self.client.long_running_recognize(config, audio)
            result = operation.result(timeout=120)

            transcript = " ".join([alternative.transcript for result in result.results for alternative in result.alternatives])
            return transcript

        except Exception as e:
            print(f"Podcast transcript error: {str(e)}")
            return ""
