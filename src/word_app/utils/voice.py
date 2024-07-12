import re
import openai
import io
import logging
import pygame
from ..config import get_voice_config

class Voice:
    BASE_URL = "http://localhost:8000/v1"
    API_KEY = "sk-111111111"
    CHUNK_SIZE = 8192

    def __init__(self):
        config = self._get_config()
        base_url = config['base_url']
        api_key = config['api_key']
        self.voice = config['voice']
        self.model = config['model']
        self.sample_rate = config['audio']['sample_rate']
        self.buffer_size = config['audio']['buffer_size']
        self.chunk_size = config['audio']['stream_chunk_size']
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def _get_config(self):
        return get_voice_config()

    def play_audio(self, audio_data: bytes) -> None:
        pygame.mixer.init(frequency=self.sample_rate, buffer=self.buffer_size)
        sound = pygame.mixer.Sound(io.BytesIO(audio_data))
        channel = sound.play()
        while channel.get_busy():
            pygame.time.wait(100)

    def cleanup_text(self, text:str) -> str:
        """Remove all non digits and alphabets from the text"""
        clean_text = ''.join(e for e in text if e.isalnum() or e.isspace())
        clean_text = re.sub(r'\n+', '. ', clean_text)
        return clean_text

    def speak(self, text:str) -> None:
        phrase = self.cleanup_text(text)
        try:
            logging.debug("Sending text to TTS server")
            with self.client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice=self.voice,
                input=phrase
            ) as response:
                logging.debug("Received response from TTS server")
                audio_stream = response.iter_bytes(chunk_size=self.chunk_size)
                
                audio_data = b''.join(audio_stream)
                
                logging.debug(f"Audio data size: {len(audio_data)} bytes")
                
                self.play_audio(audio_data)
                
                logging.debug("Finished playing audio")
        except Exception as e:
            logging.error(f"Error occurred while processing text: {str(e)}")