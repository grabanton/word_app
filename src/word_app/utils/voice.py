import re
import openai
import io
import logging
import pygame
import threading
import random
from ..config import get_voice_config

class Voice:
    BASE_URL = "http://localhost:8000/v1"
    API_KEY = "sk-111111111"
    CHUNK_SIZE = 8192

    def __init__(self):
        config = self._get_config()
        base_url = config['base_url']
        api_key = config['api_key']
        self.voice_list = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        self.voice_mode = config['voice']
        self.voice = ''
        self.model = config['model']
        self.sample_rate = config['audio']['sample_rate']
        self.buffer_size = config['audio']['buffer_size']
        self.chunk_size = config['audio']['stream_chunk_size']
        self.stop_playback = False
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def _get_config(self):
        return get_voice_config()

    def pick_voice(self) -> str:
        if ( self.voice_mode == 'random_word' ):
            self.voice = random.choice(self.voice_list)
        elif self.voice_mode == 'random_session' and not self.voice :
            self.voice = random.choice(self.voice_list)
        elif not self.voice:
            self.voice = self.voice_mode

    def play_audio(self, audio_data: bytes) -> None:
        pygame.mixer.init(frequency=self.sample_rate, buffer=self.buffer_size)
        sound = pygame.mixer.Sound(io.BytesIO(audio_data))
        channel = sound.play()
        while channel.get_busy() and not self.stop_playback:
            pygame.time.wait(1000)
        channel.stop()

    def cleanup_text(self, text):
        # Заменяем переносы строк на пробелы, добавляя точку, если перед переносом не было точки
        text = re.sub(r'([^.\n])\n', r'\1. ', text)
        text = re.sub(r'\n', ' ', text)
        
        # Заменяем слеш на запятую
        text = text.replace('/', ',')
        
        # Оставляем только буквы, цифры, знаки препинания, кавычки и пробелы
        text = re.sub(r'[^a-zA-Zа-яА-Я0-9\s.,!?:;()\-"\'«»]', '', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def speak(self, text:str) -> None:
        self.stop_playback = False
        phrase = self.cleanup_text(text)
        voice = threading.Thread(target=self._speak,args=(phrase,))
        voice.start()
    
    def stop_speaking(self):
        self.stop_playback = True

    def _speak(self, text:str) -> None:
        try:
            logging.debug("Sending text to TTS server")
            self.pick_voice()
            with self.client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice=self.voice,
                input=text
            ) as response:
                logging.debug("Received response from TTS server")
                audio_stream = response.iter_bytes(chunk_size=self.chunk_size)
                
                audio_data = b''.join(audio_stream)
                
                logging.debug(f"Audio data size: {len(audio_data)} bytes")
                
                if not self.stop_playback:
                    self.play_audio(audio_data)
                
                logging.debug("Finished playing audio")
        except Exception as e:
            logging.error(f"Error occurred while processing text: {str(e)}")
