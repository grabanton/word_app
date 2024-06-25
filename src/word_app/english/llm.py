from typing import Generator
import ollama
from ..config import get_llm_config, get_prompt_path

class Teacher:
    """A class to manage the ollama teacher assistant."""
    def __init__(self, name: str = 'llama3', stream: bool = True) -> None:
        config = get_llm_config()
        self.main_model = config['models']['main']
        self.translator_model = config['models']['translator']
        self.client = ollama.Client(host=config['base_url'])
        self.stream = stream

        self.system_explain = self._load_prompt('explain')
        self.system_translate = self._load_prompt('translate')
        self.system_conversation = self._load_prompt('conversation')
        self.system_riddle = self._load_prompt('riddle')
        self.system_game_intro = self._load_prompt('game_intro')
        self.system_game_qa = self._load_prompt('game_qa')
        self.system_grader = self._load_prompt('grender')

        self.chat_history = []

    def _load_prompt(self, prompt_name: str) -> str:
        prompt_path = get_prompt_path(prompt_name)
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    def text_gen(self, prompt: str, model: str = 'llama3', temperature: float = 0.5, system: str = '') -> Generator[dict, None, None]:
        """Generate a text. Completion mode."""
        return self.client.generate(
            model=self.main_model,
            system=system,
            prompt=prompt,
            options={'temperature': temperature},
            stream=self.stream
        )
    
    def init_convrsation(self, word: str) -> None:
        """Append the initial system message to the chat history."""
        self.chat_history = [{
            'role': 'system',
            'content': self.system_conversation.format(word=word)
        }]

    def init_qa(self, word: str) -> None:
        """Append the initial system message to the chat history."""
        self.chat_history = [{
            'role': 'system',
            'content': self.system_game_qa.format(word=word)
        }]

    def append_content(self, content: str, role: str='assistant') -> None:
        """Append the assistant's response to the chat history."""
        self.chat_history.append({'role': role, 'content': content})
    
    def conversation(self, prompt: str) -> Generator[dict, None, None]:
        """Append the user's message to the chat history and generate a response. Chat mode."""
        self.chat_history.append({'role': 'user', 'content': prompt})
        return self.client.chat(
            model=self.main_model,
            messages=self.chat_history,
            options={'temperature': 0.7},
            stream=self.stream
        )

    def explainer(self, word: str) -> Generator[dict, None, None]:
        """Generate an explanation for a word. Using a main model."""
        prompt = f'Explain "{word}".'
        return self.text_gen(prompt, system=self.system_explain)
    
    def translator(self, text: str) -> Generator[dict, None, None]:
        """Translate a text from English to a selected language. Using a translator model."""
        prompt = f'The text to translate:\n{text}'
        return self.text_gen(prompt, model=self.translator_model, temperature=0.3, system=self.system_translate)
    
    def game_intro(self, counter: int) -> Generator[dict, None, None]:
        """Generate a game introduction message."""
        prompt = "I'm not ready"
        system = self.system_game_intro.format(N=counter)
        return self.text_gen(prompt, system=system, temperature=0.7)
    
    def riddler(self, word: str) -> Generator[dict, None, None]:
        """Generate a riddle based on the prompt."""
        prompt = f'The word is "{word}".'
        system = self.system_riddle
        return self.text_gen(prompt, system=system, temperature=0.7)
    
    def grader(self, word: str, answer: str) -> Generator[dict, None, None]:
        """Grade the user's answer to the riddle."""
        prompt = f'The answer is "{answer}".'
        system = self.system_grader.format(WORD=word)
        return self.text_gen(prompt, system=system, temperature=0)