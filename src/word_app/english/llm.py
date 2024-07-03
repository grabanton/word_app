from typing import Generator, Dict, Tuple
import ollama
import re
from ..config import get_llm_config, get_prompt_path

DEFAULT_OPTIONS = {'temperature': 0.5, 'max_tokens': 2048}

class Teacher:
    """A class to manage the ollama teacher assistant."""
    def __init__(self, stream: bool = True) -> None:
        self.config = get_llm_config()
        self.main_model = self.config['models']['main']
        self.translator_model = self.config['models']['translator']
        self.client = ollama.Client(host=self.config['base_url'])
        self.stream = stream

        self.system_explain = self._load_prompt('explain')
        self.system_translate = self._load_prompt('translate')
        self.system_conversation = self._load_prompt('conversation')
        self.system_riddle = self._load_prompt('riddle')
        self.system_game_intro = self._load_prompt('game_intro')
        self.system_game_qa = self._load_prompt('game_qa')
        self.system_grader = self._load_prompt('grader')

        self.explain_options = self._load_options('explain')
        self.translate_options = self._load_options('translate')
        self.conversation_options = self._load_options('conversation')
        self.riddle_options = self._load_options('riddle')
        self.game_intro_options = self._load_options('game_intro')
        self.game_qa_options = self._load_options('game_qa')
        self.grader_options = self._load_options('grader')

        self.chat_history = []

    def _load_prompt(self, prompt_name: str) -> str:
        prompt_path = get_prompt_path(prompt_name)
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
        
    def _load_options(self, prompt_name: str) -> Dict:
        generic = self.config['options']['generic']
        specific = self.config['options']['specific'][prompt_name]
        return {**generic, **specific}

    def text_gen(self, prompt: str, model: str = '', options: Dict = DEFAULT_OPTIONS, system: str = '') -> Generator[dict, None, None]:
        """Generate a text. Completion mode."""
        the_model = model if model else self.main_model
        return self.client.generate(
            model=the_model,
            system=system,
            prompt=prompt,
            options=options,
            stream=self.stream
        )
    
    def init_convrsation(self, word: str) -> None:
        """Append the initial system message to the chat history."""
        mode, count = self.get_mode(word)
        self.chat_history = [{
            'role': 'system',
            'content': self.system_conversation.format(word=word,mode=mode)
        }]

    def init_qa(self, word: str) -> None:
        """Append the initial system message to the chat history."""
        mode, count = self.get_mode(word)
        self.chat_history = [{
            'role': 'system',
            'content': self.system_game_qa.format(word=word, mode=mode)
        }]

    def append_content(self, content: str, role: str='assistant') -> None:
        """Append the assistant's response to the chat history."""
        self.chat_history.append({'role': role, 'content': content})
    
    def conversation(self, prompt: str, options: Dict=DEFAULT_OPTIONS) -> Generator[dict, None, None]:
        """Append the user's message to the chat history and generate a response. Chat mode."""
        self.chat_history.append({'role': 'user', 'content': prompt})
        return self.client.chat(
            model=self.main_model,
            messages=self.chat_history,
            options=options,
            stream=self.stream
        )

    def explainer(self, word: str) -> Generator[dict, None, None]:
        """Generate an explanation for a word. Using a main model."""
        prompt = f'Explain "{word}".'
        mode, count = self.get_mode(word)
        return self.text_gen(prompt, 
                             system=self.system_explain.format(mode=mode), 
                             options=self.explain_options)
    
    def translator(self, text: str) -> Generator[dict, None, None]:
        """Translate a text from English to a selected language. Using a translator model."""
        prompt = f'The text to translate:\n{text}'
        return self.text_gen(prompt, 
                             model=self.translator_model, 
                             system=self.system_translate, 
                             options=self.translate_options)
    
    def game_intro(self, counter: int) -> Generator[dict, None, None]:
        """Generate a game introduction message."""
        prompt = "I'm not ready"
        system = self.system_game_intro.format(N=counter)
        return self.text_gen(prompt, 
                             system=system, 
                             options=self.game_intro_options)
    
    def riddler(self, word: str) -> Tuple[Generator[dict, None, None], str]:
        """Generate a riddle based on the prompt."""
        prompt = f'The word is "{word}".'
        mode, count = self.get_mode(word)
        count_clue = "Is only one word." if mode == 'word' else f"Is a phrase of {count} words."
        system = self.system_riddle.format(mode=mode)
        return self.text_gen(prompt, 
                             system=system, 
                             options=self.riddle_options), count_clue
    
    def grader(self, word: str, answer: str) -> Generator[dict, None, None]:
        """Grade the user's answer to the riddle."""
        prompt = f'The answer is "{answer}".'
        mode, count = self.get_mode(word)
        system = self.system_grader.format(WORD=word, mode=mode)
        return self.text_gen(prompt, 
                             system=system, 
                             options=self.grader_options)
    
    def word_count(self, text: str) -> int:
        """Count the number of words in the text."""
        return len( re.findall( r"[a-zA-Z']+", text ) )
    
    def get_mode(self, word: str) -> Tuple[str, int]:
        """Determine the mode of the game."""
        count = self.word_count(word)
        mode = "word" if count == 1 else "phrase"
        return mode, count