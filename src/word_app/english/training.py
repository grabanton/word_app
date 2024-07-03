import random
from typing import Tuple, List, Dict, Generator, Optional
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
import re

from .word_manager import WordManager, Word, STATES
from .ui_manager import UIManager
from .llm import Teacher


ROBOT_EMOJI = "\U0001F916"
console = Console()

class BaseWordApp:
    """Base class for word application modes."""
    def __init__(self):
        self.word_manager = WordManager()
        self.ui_manager = UIManager()
        self.teacher = Teacher()
        self._base_command_handlers = self._get_base_command_handlers()
        self._specific_command_handlers = {}

    def run(self) -> None:
        """Main loop for the application."""
        self.show_help()
        prompt = 'Word' if isinstance(self, WordDictionary) else 'Category'
        if isinstance(self, WordTrainer):
            self.print_categories()
        previous_command = None
        while True:
            command = console.input(f"[green bold]{prompt}[white] > ").strip()  
            is_command, action, args = self.parse_command(command, previous_command)
            if is_command:
                self.handle_specific_action(action, [args])
            else:
                self.handle_specific_action('specific', [command])
            previous_command = action

    def _get_base_command_handlers(self) -> Dict:
        return {
            "/h": self.show_help,
            "/help": self.show_help,
            "/i" : self.show_word_info,
            "/info": self.show_word_info,
            "/m": self.manual_update,
            "/ct": self.print_categories,
            "/cat": self.print_categories,
            "/a": self.show_all,
            "/all": self.show_all,
            "/d": self.delete_word,
            "/del": self.delete_word,
            "/c": self.chat_mode,
            "/conv": self.chat_mode,
            "/q": lambda *x: exit(),
            "/quit": lambda *x: exit(),
            "/bye": lambda *x: "bye",
        }

    def parse_command(self, command: str, previous_command: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Parse the user input and return True if it's a command.(startswith "/"), command string and argument. 
           Otherwise return False, the input command string and None."""
        pattern = re.compile(r"^\s*(\/[a-zA-Z]+)\s*([a-zA-Z0-9 '_-]*)$")
        match = pattern.match(command)
        if match:
            action = match.group(1)
            argument = match.group(2).strip() if match.group(2) else None
            if argument == "":
                argument = previous_command.strip() if previous_command else None
            return True, action, argument
        else:
            return False, command, None
        
    def handle_specific_action(self, action: str, args: List = []) -> Optional[str]:
        """Handle mode-specific actions. To be overridden by subclasses."""
        if action in self._specific_command_handlers:
            return self._specific_command_handlers[action](*args)
        else:
            return self._base_command_handlers.get(action, lambda : None)(*args)
        
    def process_command(self, prompt:str) -> str:
        """Process a command and return the next command."""
        command = console.input(prompt).strip()
        is_command = True
        while is_command:
            is_command, action, args = self.parse_command(command, None)
            if is_command:
                self.handle_specific_action(action, [args])
                command = console.input(prompt).strip()
        return command

    def display_existing_word(self, layout: Layout, word: Word) -> None:
        """Display an existing word in the database."""
        with Live(layout, console=console, refresh_per_second=4) as live:
            self.ui_manager.display_word(layout, word)
            live.update(layout)
        self.word_manager.increment_counter(word.word)
        self.word_manager.process_state(word.word, -1)

    def show_help(self,*args) -> None:
        """Display help information."""
        mode = "dictionary" if isinstance(self, WordDictionary) else "trainer"
        self.ui_manager.show_help(console, mode)

    def show_word_info(self, word: str) -> None:
        """Print information about a word."""
        word = self.word_manager.fetch_word(word)
        console.print(word)
    
    def show_all(self, category: str, *args) -> None:
        """Show all words in the database."""
        self.ui_manager.show_all_words(console, self.word_manager, category)

    def manual_update(self, word: str) -> None:
        """Interactively update a word's category and state from user input."""
        new_category = console.input('[green]Category[white] (or "/" to skip) > ').strip()
        if not new_category.startswith("/"):
            self.word_manager.set_category(word, new_category)
        new_state = console.input('[green]State[white] (or "/" to skip) > ').strip()
        if not new_state.startswith("/"):
            self.word_manager.process_state(word, int(new_state))

    def delete_word(self, word: str) -> None:
        """Delete a word from the database."""
        if not word:
            console.print("You didn't provide any words to delete.")
            return
        check = console.input(f'[red]Are you sure to delete "[green bold]{word}[red]"? [white]y/n >')
        if check == "y":
            is_deleted = self.word_manager.delete_word(word)
            if is_deleted:
                console.print(f'\n"{word}" has been deleted.\n')
            else:
                console.print(f'\n"{word}" not found.\n')
        else:
            console.print("\nDeletion cancelled.\n")

    def process_word(self, command: str, is_update: bool=False) -> None:
        """Process a word. Or update an existing one."""
        layout: Layout = self.ui_manager.create_layout()
        self.ui_manager.update_command_panel(layout, command)
        word = self.word_manager.fetch_word(command)
        if word and not is_update:
            self.display_existing_word(layout, word)
        elif command.strip():
            self.process_new_word(layout, command, is_update)

    def process_new_word(self, layout: Layout, word: str, rewrite: bool) -> None:
        """Process a new word. Or rewrite an existing one."""
        with Live(layout, console=console, auto_refresh=False) as live:
            explanation_text, translation_text = self.generate_explanations(word, layout, live)
        warning = " ([red]Previous word data will be lost[white])" if rewrite else ""
        answer = self.process_command(f'Save the word?{warning} : [yellow]y [magenta]optional[white](category) or press Enter to skip > ')
        answer = answer.lower()
        if answer.startswith("y"):
            category = answer.replace("y", "").strip()
            self.word_manager.insert_word(word, category, explanation_text, translation_text)

    def generate_explanations(self, word: str, layout: Layout, live: Live) -> Tuple[str, str]:
        """Generate explanations and translations for a given word."""
        explanation_text = ""
        translation_text = ""
        
        explanation = self.teacher.explainer(word)
        for chunk in explanation:
            explanation_text += chunk['response']
            self.ui_manager.update_left_panel(layout, explanation_text)
            live.update(layout)
            live.refresh()

        translation = self.teacher.translator(explanation_text)
        for chunk in translation:
            translation_text += chunk['response']
            self.ui_manager.update_right_panel(layout, translation_text)
            live.update(layout)
            live.refresh()
        
        return explanation_text, translation_text

    def chat_mode(self, word: str, *arg) -> Optional[str]:
        """Start a chat session."""
        if not word:
            console.print("You didn't provide any words to chat with.")
            return
        
        self.teacher.init_convrsation(word)
        is_first = True
        while True:
            question = "Hello!" if is_first else self.get_multiline_input()
            is_first = False
            is_command, action, args = self.parse_command(question, None)
            if is_command:
                check = self.handle_specific_action(action, [args])
                if check == "bye":
                    break
            answer = self.teacher.conversation(question, options=self.teacher.conversation_options)
            self.display_chat_answer(answer)
        
    def draw_stream(self, stream: Generator, mode: str = 'chat') -> str:
        with Live(console=console, auto_refresh=False) as live:
            full_answer = f"{ROBOT_EMOJI} "
            for chunk in stream:
                token = chunk['message']['content'] if mode == 'chat' else chunk['response']
                full_answer += token
                self.ui_manager.update_converation_output(full_answer, live)
            return full_answer

    def get_multiline_input(self) -> str:
        """Process a multiline input from the user."""
        lines = []
        while True:
            line = console.input("[green bold]You[white] > ").strip()
            if line.endswith("\\"):
                lines.append(line[:-1])
            else:
                lines.append(line)
                break
        return " ".join(lines)

    def display_chat_answer(self, answer: Generator) -> None:
        """Live display of the chat answer."""
        full_answer = self.draw_stream(answer)
        self.teacher.append_content(full_answer)

    def print_categories(self, *args) -> None:
        self.ui_manager.show_categories(console, self.word_manager)

class WordDictionary(BaseWordApp):
    """Class for dictionary mode of the application."""
    def __init__(self):
        super().__init__()
        self._specific_command_handlers = self._get_specific_command_handlers()

    def _get_specific_command_handlers(self) -> Dict:
        return {
            "/u": lambda word, *x: self.process_word(word, True),
            "/upd": lambda word, *x: self.process_word(word, True),
            "specific": lambda word, *x: self.process_word(word),
        }

class WordTrainer(BaseWordApp):
    """Class for trainer mode of the application."""
    def __init__(self):
        super().__init__()
        self.used_words = set()
        self.category = ""
        self._specific_command_handlers = {
            'specific': lambda category, *x: self.start_training(category),
            "/l" : lambda word, *x: self.show_word(word),
            "/lookup": lambda word, *x: self.show_word(word),
            "/n" : lambda word, *x: self.process_word(word),
            "/new" : lambda word, *x: self.process_word(word),
            "/a" : lambda category, *x: self.show_current_words(category),
            "/all" : lambda category, *x: self.show_current_words(category),
            }

    def run(self) -> None:
        super().run()

    def start_training(self, category: str, *args) -> Optional[str]:
        include_mastered = False
        if category.endswith(" --full"):
            category = category[:-7].strip()
            include_mastered = True
        
        self.category = category if category else None
        available_words = self.word_manager.fetch_words(self.category)
        
        while True:
            self.print_training_stats(self.category)
            word = self.select_word(available_words, include_mastered)
            if not word:
                console.print("No more words available for training. Resetting used words.")
                self.used_words.clear()
                word = self.select_word(available_words, include_mastered)
                if not word:
                    console.print("No words available for training.")
                    break

            self.start_game()
            riddle = self.word_riddle(word)
            user_guess = ""
            while not user_guess:
                user_guess = self.process_command("[green]Your guess > ")

            user_guess = self.game_conversation(word, riddle, user_guess)
            if not user_guess:
                continue
            self.grade_guess(word, user_guess)

    def show_word(self, name: str, *args) -> None:
        """Display information about a word."""
        word = self.word_manager.fetch_word(name)
        if word:
            layout = self.ui_manager.create_layout()
            self.display_existing_word(layout, word)
        else:
            console.print(f'Word "{name}" not found.')

    def show_current_words(self,category:str,*args) -> None:
        """Show all words that are currently used in the training session."""
        cat = category if category else self.category
        self.show_all(cat)

    def add_word(self, word: str) -> None:
        """Add a new word to the database."""
        layout = self.ui_manager.create_layout()
        with Live(layout, console=console, auto_refresh=False) as live:
            self.ui_manager.update_command_panel(layout, word)
            self.process_new_word(layout, word, False)
            
    def start_game(self) -> Optional[str]:
        check = self.process_command("[green]Are you ready?[white] >")
        counter = 0
        while True:
            if check.strip().lower() in ["n", "no", "not ready", "not yet", "nope", "nah", "nay"]:
                counter += 1
                game = self.teacher.game_intro(counter)
                self.draw_stream(game, mode='generate')
                check = self.process_command("[green]Now? [white]> ")
            else:
                break

    def game_conversation(self, word: Word, riddle: str, question: str) -> str:
        if question.strip().startswith("?"):
            command = question.strip()[1:]
            self.teacher.init_qa(word.word)
            self.teacher.append_content('Hello!', role='user')
            self.teacher.append_content(riddle, role='assistant')
            while True :
                answer = self.teacher.conversation(command, options=self.teacher.game_qa_options)
                self.draw_stream(answer, mode='chat')
                check = self.process_command("[green]Your guess >")
                if not check.strip().startswith("?") :
                    return check
                else : command = check.strip()[1:]
        else:
            return question

    def select_word(self, words: List[Word], include_mastered: bool = False) -> Optional[Word]:
        if not include_mastered:
            words = [w for w in words if w.state is not None and w.state < len(STATES) - 1]
        else:
            words = [w for w in words if w.state is not None]

        available_words = [w for w in words if w.word not in self.used_words]
        
        if not available_words:
            return None

        weights = [max(1, len(STATES) - (w.state or 0)) for w in available_words]
        weights = [float(w)/sum(weights) for w in weights]
        selected_word = random.choices(available_words, weights=weights, k=1)[0]
        self.used_words.add(selected_word.word)
        return selected_word

    def word_riddle(self, word: Word) -> str:
        riddle, count_clue = self.teacher.riddler(word.word)
        console.print(f"{ROBOT_EMOJI} [blue]{count_clue}")
        with Live(console=console, auto_refresh=False) as live:
            full_riddle = f"{ROBOT_EMOJI} "
            for chunk in riddle:
                full_riddle += chunk['response']
                self.ui_manager.update_converation_output(full_riddle, live)
            return full_riddle

    def grade_guess(self, word: Word, guess: str) -> Optional[str]:
        if guess.strip().lower() == word.word.lower():
            console.print(f"{ROBOT_EMOJI} [green]Correct!\n [white]Literaly equals to the correct answer. Moving to the next word.\n")
            self.word_manager.process_state(word.word, 1)
            check = self.process_command(f"> ")
        else:
            grade = self.teacher.grader(word.word, guess)
            full_grade = f"{ROBOT_EMOJI} "
            with Live(console=console, auto_refresh=False) as live:
                for chunk in grade:
                    full_grade += chunk['response']
                    self.ui_manager.update_converation_output(full_grade, live)


            if full_grade.replace(ROBOT_EMOJI,'').strip().lower().startswith("correct"):
                console.print("Moving to the next word.\n")
                self.word_manager.process_state(word.word, 1)
            else:
                self.word_manager.process_state(word.word, -1)
                check = self.process_command("Would you like to chat about this word? (y/n): ")
                if check.lower() == "y":
                    check = self.chat_mode(word.word)

    def print_training_stats(self, category: str = None) -> None:
        self.ui_manager.show_training_stats(console, self.word_manager, category)
        