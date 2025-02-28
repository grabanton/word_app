from typing import Generator, Dict, Tuple
import ollama
import openai
from ..config import get_llm_config, get_prompt_path
from ..utils import Utils

DEFAULT_OPTIONS = {'temperature': 0.5, 'max_tokens': 2048}

class Teacher:
    """A class to manage the ollama teacher assistant."""
    def __init__(self, stream: bool = True) -> None:
        self.config = get_llm_config()
        self.main_model = self.config['models']['main']
        self.translator_model = self.config['models']['translator']
        self.use_openai = self.config.get('use_openai', False)
        if self.use_openai:
            self.client = openai.OpenAI(api_key=self.config.get('openai_api_key'))
        else:
            self.client = ollama.Client(host=self.config['base_url'])
        self.stream = stream

        self.system_explain = self._load_prompt('explain')
        self.system_translate = self._load_prompt('translate')
        self.system_conversation = self._load_prompt('conversation')
        self.system_riddle = self._load_prompt('riddle')
        self.system_game_intro = self._load_prompt('game_intro')
        self.system_game_qa = self._load_prompt('game_qa')
        self.system_grader = self._load_prompt('grader')
        self.system_grammar = self._load_prompt('grammar')
        self.system_verbs = self._load_prompt('verbs')

        self.explain_options = self._load_options('explain')
        self.translate_options = self._load_options('translate')
        self.conversation_options = self._load_options('conversation')
        self.riddle_options = self._load_options('riddle')
        self.game_intro_options = self._load_options('game_intro')
        self.game_qa_options = self._load_options('game_qa')
        self.grader_options = self._load_options('grader')
        self.grammar_options = self._load_options('grammar')
        self.verbs_options = self._load_options('verbs')

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
        
        if self.use_openai:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
            response = self.client.chat.completions.create(
                model=the_model,
                messages=messages,
                stream=self.stream,
                **options
            )
            if self.stream:
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield {"response": chunk.choices[0].delta.content}
            else:
                yield {"response": response.choices[0].message.content}
        else:
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

    def init_verbs(self, verb: str) -> None:
        """Append the initial system message to the chat history."""
        self.chat_history = [{
            'role': 'system',
            'content': self.system_verbs.format(verb=verb)
        }]

    def init_grammar(self, topic: str, description: str) -> None:
        """Append the initial system message to the chat history."""
        self.chat_history = [{
            'role': 'system',
            'content': self.system_grammar.format(topic=topic, description=description)
        }]

    def append_content(self, content: str, role: str='assistant') -> None:
        """Append the assistant's response to the chat history."""
        self.chat_history.append({'role': role, 'content': content})
    
    def conversation(self, prompt: str, options: Dict=DEFAULT_OPTIONS) -> Generator[dict, None, None]:
        """Append the user's message to the chat history and generate a response. Chat mode."""
        self.chat_history.append({'role': 'user', 'content': prompt})
        
        if self.use_openai:
            response = self.client.chat.completions.create(
                model=self.main_model,
                messages=self.chat_history,
                stream=self.stream,
                **options
            )
            if self.stream:
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield {"response": chunk.choices[0].delta.content}
            else:
                yield {"response": response.choices[0].message.content}
        else:
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
        # print(self.translator_model)
        # print(self.translate_options)
        # print(self.system_translate)
        # print(prompt)

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
                             options=self.riddle_options), count_clue, count
       
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
        return Utils.count_words(text)
    
    def get_mode(self, word: str) -> Tuple[str, int]:
        """Determine the mode of the game."""
        count = self.word_count(word)
        mode = "word" if count == 1 else "phrase"
        return mode, count
