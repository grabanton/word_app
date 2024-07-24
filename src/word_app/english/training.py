import random
from typing import Tuple, List, Dict, Generator, Optional
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
import re

from .word_manager import WordManager, Word, IrregularVerb, GrammarTheme, STATES
from .ui_manager import UIManager
from .llm import Teacher
from ..utils import Voice


ROBOT_EMOJI = "\U0001F916"
console = Console()

class BaseWordApp:
    """Base class for word application modes."""
    def __init__(self):
        self.word_manager = WordManager()
        self.ui_manager = UIManager()
        self.teacher = Teacher()
        self.voice = Voice()
        self.last_output = None
        self.auto_speak = False
        self._base_command_handlers = self._get_base_command_handlers()
        self._specific_command_handlers = self._get_specific_command_handlers()

    def run(self, prompt: str) -> None:
        """Main loop for the application."""
        self.show_help()
        while True:
            command = self.process_command(prompt)
            if command.startswith('/q'):
                break

    def _get_specific_command_handlers(self) -> Dict:
        """To be overridden by subclasses."""
        return {'specific': lambda x: None}

    def _get_base_command_handlers(self) -> Dict:
        return {
        "/h": lambda *x: self.show_help(),
        "/help": lambda *x: self.show_help(),
        "/i": lambda word, *x: self.show_word_info(word),
        "/info": lambda word, *x: self.show_word_info(word),
        "/n": lambda word, *x: self.process_word(word),
        "/new": lambda word, *x: self.process_word(word),
        "/m": lambda word, *x: self.manual_update(word),
        "/man": lambda word, *x: self.manual_update(word),
        "/ct": lambda *x: self.print_categories(),
        "/cat": lambda *x: self.print_categories(),
        "/a": lambda category, *x: self.show_all(category),
        "/all": lambda category, *x: self.show_all(category),
        "/d": lambda word, *x: self.delete_word(word),
        "/del": lambda word, *x: self.delete_word(word),
        "/c": lambda word, *x: self.chat_mode(word),
        "/conv": lambda word, *x: self.chat_mode(word),
        "/q": lambda *x: exit(),
        "/quit": lambda *x: exit(),
        "/bye": lambda *x: "bye",
        "/say": lambda text, *x: self.speak(text),
        "/voice": lambda mode, *x : self.set_speak_mode(mode),
    }

    def handle_action(self, action: str, args: List = []) -> Optional[str]:
        """Handle actions from both base and specific command handlers."""
        if action in self._specific_command_handlers:
            return self._specific_command_handlers[action](*args) if args else self._specific_command_handlers[action]()
        elif action in self._base_command_handlers:
            return self._base_command_handlers[action](*args) if args else self._base_command_handlers[action]()
        else:
            console.print(f"[red]Unknown command: {action}[/red]")

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
            if action in self._base_command_handlers:
                return self._base_command_handlers.get(action, lambda : None)(*args)
            else:
                console.print(f"[red]Unknown command: [white]{action}[/red]")
        
    def process_command(self, prompt:str, run_specific: bool = True) -> str:
        """Process a command and return the next command."""
        input_title = f"[bold green]{prompt}[white] > "
        is_command = True
        while is_command:
            command = console.input(input_title).strip()
            is_command, action, args = self.parse_command(command, None)
            if is_command:
                self.handle_specific_action(action, [args])
            elif run_specific:
                self.handle_specific_action('specific', [command])
        return command
    
    def speak_output(self) -> None:
        if self.auto_speak:
            self.speak(self.last_output)

    def process_word(self, command: str, is_update: bool=False) -> None:
        """Process a word. Or update an existing one."""
        layout: Layout = self.ui_manager.create_layout()
        self.ui_manager.update_command_panel(layout, command)
        word = self.word_manager.fetch_word(command)
        if word and not is_update:
            self.display_existing_word(layout, word)
            self.last_output = word.explanation_en
            self.speak_output()
        elif command.strip():
            self.process_new_word(layout, command, is_update)

    def process_new_word(self, layout: Layout, word: str, rewrite: bool) -> None:
        """Process a new word. Or rewrite an existing one."""
        with Live(layout, console=console, auto_refresh=False) as live:
            explanation_text, translation_text = self.generate_explanations(word, layout, live)
        self.last_output = explanation_text
        self.speak_output()
        warning = " ([red]Previous word data will be lost[white])" if rewrite else ""
        answer = self.process_command(f'Save the word?{warning} : [yellow]y [magenta]optional[white](category) or press Enter to skip', run_specific=False)
        answer = answer.lower()
        if answer.startswith("y"):
            category = answer.replace("y", "").strip()
            self.word_manager.insert_word(word, category, explanation_text, translation_text)

    def display_existing_word(self, layout: Layout, word: Word) -> None:
        """Display an existing word in the database."""
        with Live(layout, console=console, refresh_per_second=4) as live:
            self.ui_manager.display_word(layout, word)
            live.update(layout)
        self.word_manager.increment_word_counter(word.word)
        self.word_manager.process_word_state(word.word, -1)

    def show_help(self) -> None:
        """Display help information."""
        self.ui_manager.show_help(console, self.__class__.__name__.lower())

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
            self.word_manager.process_word_state(word, int(new_state))

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
            self.last_output = full_answer
            self.speak_output()
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

    def speak(self, text: str) -> None:
        """Speak the provided text."""
        phrase = text if text else self.last_output
        if phrase:
            self.voice.speak(phrase)

    def set_speak_mode(self, mode: str) -> None:
        """Set the auto-speak mode."""
        if mode == "on":
            self.auto_speak = True
        elif mode == "off":
            self.auto_speak = False
        else:
            console.print(f"[red]Unknown mode: {mode}[/red]")

class WordDictionary(BaseWordApp):
    """Class for dictionary mode of the application."""
    def __init__(self):
        super().__init__()
        self._specific_command_handlers = self._get_specific_command_handlers()

    def _get_specific_command_handlers(self) -> Dict:
        return {
            'specific': lambda word, *x: self.process_word(word),
            "/u": lambda word, *x: self.process_word(word, True),
            "/upd": lambda word, *x: self.process_word(word, True),
        }

    def run(self) -> None:
        super().run("Word")
    
class WordsTutor(BaseWordApp):
    def __init__(self):
        super().__init__()
        self.used_words = set()
        self.category = ""
        self._specific_command_handlers = self._get_specific_command_handlers()

    def _get_specific_command_handlers(self) -> Dict:
        return {
            'specific': lambda category, *x: self.start_training(category),
            "/l": lambda word, *x: self.show_word(word),
            "/lookup": lambda word, *x: self.show_word(word),
            "/a": lambda category, *x: self.show_current_words(category),
            "/all": lambda category, *x: self.show_current_words(category),
        }
    
    def run(self) -> None:
        super().run("Category")

    def show_help(self) -> None:
        super().show_help()
        self.print_categories()

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
                user_guess = self.process_command("Your guess", run_specific=False)

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
            self.last_output = word.explanation_en
            self.speak_output()
        else:
            console.print(f'Word "{name}" not found.')

    def show_current_words(self,category:str,*args) -> None:
        """Show all words that are currently used in the training session."""
        cat = category if category else self.category
        self.show_all(cat)
            
    def start_game(self) -> Optional[str]:
        check = self.process_command("Are you ready?", run_specific=False)
        counter = 0
        while True:
            if check.strip().lower() in ["n", "no", "not ready", "not yet", "nope", "nah", "nay"]:
                counter += 1
                game = self.teacher.game_intro(counter)
                self.draw_stream(game, mode='generate')
                check = self.process_command("Now?", run_specific=False)
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
                check = self.process_command("Your guess", run_specific=False)
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
            self.last_output = full_riddle
            self.speak_output()
            return full_riddle

    def grade_guess(self, word: Word, guess: str) -> Optional[str]:
        if guess.strip().lower() == word.word.lower():
            console.print(f"{ROBOT_EMOJI} [green]Correct!\n [white]Literaly equals to the correct answer. Moving to the next word.\n")
            self.word_manager.process_word_state(word.word, 1)
            check = self.process_command(f"> ", run_specific=False)
        else:
            grade = self.teacher.grader(word.word, guess)
            full_grade = f"{ROBOT_EMOJI} "
            with Live(console=console, auto_refresh=False) as live:
                for chunk in grade:
                    full_grade += chunk['response']
                    self.ui_manager.update_converation_output(full_grade, live)
            self.last_output = full_grade
            self.speak_output()

            if full_grade.replace(ROBOT_EMOJI,'').strip().lower().startswith("correct"):
                console.print("Moving to the next word.\n")
                self.word_manager.process_word_state(word.word, 1)
            else:
                self.word_manager.process_word_state(word.word, -1)
                check = self.process_command("[white]Would you like to chat about this word? (y/n):", run_specific=False)
                if check.lower() == "y":
                    check = self.chat_mode(word.word)

    def print_training_stats(self, category: str = None) -> None:
        self.ui_manager.show_words_stats(console, self.word_manager, category)


class VerbsTutor(BaseWordApp):
    """Class for irregular verb mode of the application."""
    def __init__(self):
        super().__init__()
        self._specific_command_handlers = self._get_specific_command_handlers()
        self.used_verbs = set()

    def _get_specific_command_handlers(self) -> Dict:
        return {
            'specific': lambda verb, *x: self.handle_verb_command(verb),
            "/nv": lambda verb, *x: self.add_verb(verb),
            "/newverb": lambda verb, *x: self.add_verb(verb),
            "/dv": lambda verb, *x: self.delete_verb(verb),
            "/delverb": lambda verb, *x: self.delete_verb(verb),
            "/iv": lambda verb, *x: self.show_verb_info(verb),
            "/infoverb": lambda verb, *x: self.show_verb_info(verb),
            "/av": lambda *x: self.show_all_verbs(),
            "/allverbs": lambda *x: self.show_all_verbs(),
            "/cv": lambda verb, *x: self.verb_conversation(verb),
            "/convverb": lambda verb, *x: self.verb_conversation(verb),
            "/g": lambda *x: self.practice_mode(),
            "/game": lambda *x: self.practice_mode(),
        }
    
    def run(self) -> None:
        super().run("Verb")

    def handle_verb_command(self, verb: str) -> None:
        if verb:
            word = self.word_manager.get_irregular_verb(verb)
            if word:
                console.print(word)
                self.word_manager.process_verb_state(verb, -1)
                self.word_manager.increment_verb_counter(verb)
            else:
                console.print(f"Verb '{verb}' not found.")

    def add_verb(self, verb) -> None:        
        base_form = verb
        past_simple = self.process_command("Enter past simple form", run_specific=False)
        past_participle = self.process_command("Enter past participle form", run_specific=False)
        
        verb = IrregularVerb(base_form, past_simple, past_participle, 1, 0)
        self.word_manager.add_irregular_verb(verb)
        console.print("[green]Verb added successfully![/green]")
        self.show_verbs_stats()

    def delete_verb(self, verb: str) -> None:
        check = self.process_command(f'[red]Are you sure to delete the verb "[green]{verb}[red]"? [white]y/n', run_specific=False)
        if check.strip() == "y":
            is_deleted = self.word_manager.delete_irregular_verb(verb)
            if is_deleted:
                console.print(f'\nVerb "{verb}" has been deleted.\n')
            else:
                console.print(f'\nVerb "{verb}" not found.\n')

    def show_verbs_stats(self, *args) -> None:
        verbs = self.word_manager.get_all_irregular_verbs()
        self.ui_manager.show_verbs_stats(console, verbs)

    def show_all_verbs(self) -> None:
        self.ui_manager.show_all_verbs(console, self.word_manager)

    def select_verb(self, verbs: List[IrregularVerb], include_mastered: bool = False) -> Optional[IrregularVerb]:
        if not include_mastered:
            verbs = [v for v in verbs if v.state is not None and v.state < len(STATES) - 1]
        else:
            verbs = [v for v in verbs if v.state is not None]

        available_verbs = [v for v in verbs if v.base_form not in self.used_verbs]
        
        if not available_verbs:
            return None

        weights = [max(1, len(STATES) - (v.state or 0)) for v in available_verbs]
        weights = [float(w)/sum(weights) for w in weights]
        selected_verb = random.choices(available_verbs, weights=weights, k=1)[0]
        self.used_verbs.add(selected_verb.base_form)
        return selected_verb

    def practice_mode(self,include_mastered=False, *args) -> None:
        available_verbs = self.word_manager.get_all_irregular_verbs()
        
        while True:
            self.show_verbs_stats()
            verb = self.select_verb(available_verbs, include_mastered)
            if not verb:
                console.print("No more verbs available for training. Resetting used verbs.")
                self.used_verbs.clear()
                verb = self.select_verb(available_verbs, include_mastered)
                if not verb:
                    console.print("No verbs available for training.")
                    break

            console.print(f"\n[green]Base form: [white]{verb.base_form}")
            past_simple = self.process_command("Past simple form:", run_specific=False)
            past_participle = self.process_command("Participle form:", run_specific=False)
            
            if past_simple == verb.past_simple and past_participle == verb.past_participle:
                console.print("[green]Correct![/green]")
                self.word_manager.process_verb_state(verb.base_form, 1)
            else:
                console.print(f"[red]Incorrect. The correct forms are:[/red]")
                console.print(f"[green]Past Simple: [white]{verb.past_simple}")
                console.print(f"[green]Past Participle: [white]{verb.past_participle}")

                responce = self.process_command(f'Do you whant to speak about "[white]{verb.base_form}[green]"? (y/n):', run_specific=False)
                if responce.lower() == "y":
                    self.verb_conversation(query=verb.base_form)

    def verb_conversation(self, query: str) -> None:
        if not query:
            return
        verb = self.word_manager.get_irregular_verb(query)
        if not verb :
            console.print(f"\nVerb '{verb}' not found.\n")
            return

        self.teacher.init_verbs(verb=verb)
        is_first = True
        while True:
            user_input = f"!!g Hello! let's speak about the  irregular verb {verb.base_form}" if is_first else self.get_multiline_input()
            is_first = False
            if not user_input:
                continue
            is_command, action, args = self.parse_command(user_input, None)
            if is_command:
                check = self.handle_specific_action(action, [args])
                if check == "bye":
                    break
                else:
                    continue
            answer = self.teacher.conversation(user_input, options=self.teacher.verbs_options)
            self.display_chat_answer(answer)

class GrammarTutor(BaseWordApp):
    """Class for grammar rules mode of the application."""
    def __init__(self):
        super().__init__()
        self._specific_command_handlers = self._get_specific_command_handlers()

    def _get_specific_command_handlers(self) -> Dict:
        return {
            'specific': lambda theme, *x: self.start_theme_conversation(theme),
            "/nt": lambda theme, *x: self.add_theme(theme),
            "/newtheme": lambda theme, *x: self.add_theme(theme),
            "/dt": lambda theme, *x: self.delete_theme(theme),
            "/deltheme": lambda theme, *x: self.delete_theme(theme),
            "/at": lambda *x: self.show_all_themes(),
            "/allthemes": lambda *x: self.show_all_themes(),
        }

    def run(self) -> None:
        super().run("Select theme")

    def add_theme(self, theme: str) -> None:
        name = self.process_command("Enter theme name", run_specific=False)
        description = self.process_command("Enter theme description", run_specific=False)
        self.word_manager.add_grammar_theme(GrammarTheme(name, description))
        console.print("[green]Theme added successfully![/green]")
        self.list_themes()

    def delete_theme(self, theme: str) -> None:
        check = self.process_command(f'[red]Are you sure to delete the theme "[green]{theme}[red]"? [white]y/n', run_specific=False)
        if check.strip() == "y":
            is_deleted = self.word_manager.delete_grammar_theme(theme)
            if is_deleted:
                console.print(f'\nTheme "{theme}" has been deleted.\n')
            else:
                console.print(f'\nTheme "{theme}" not found.\n')

    def list_themes(self) -> None:
        themes = self.word_manager.get_all_grammar_themes()
        self.ui_manager.show_grammar_themes(console, themes)

    def show_all_themes(self) -> None:
        self.ui_manager.show_all_themes(console, self.word_manager)

    def start_theme_conversation(self, query: str) -> None:
        if not query:
            return
        theme = self.word_manager.get_grammar_theme(query)
        if not theme :
            console.print(f"\nTheme '{query}' not found.\n")
            return

        self.teacher.init_grammar(topic=theme.name, description=theme.description)
        is_first = True
        while True:
            user_input = "Hello!" if is_first else self.get_multiline_input()
            is_first = False
            if not user_input:
                continue
            is_command, action, args = self.parse_command(user_input, None)
            if is_command:
                check = self.handle_specific_action(action, [args])
                if check == "bye":
                    break
                else:
                    continue
            elif not action:
                continue
            answer = self.teacher.conversation(user_input, options=self.teacher.grammar_options)
            self.display_chat_answer(answer)