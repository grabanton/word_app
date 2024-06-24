import random
from typing import Tuple, List, Generator, Optional
from rich.console import Console
from rich.layout import Layout
from rich.live import Live

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

    def run(self) -> None:
        """Main loop for the application."""
        self.show_help()
        prompt = 'Word' if isinstance(self, WordDictionary) else 'Category'
        if isinstance(self, WordTrainer):
            self.print_categories()
        previous_command: str = None
        while True:
            command: str = console.input(f"[green bold]{prompt}[white] > ").strip()
            if command.startswith("/q"):
                break
            
            command, action = self.parse_command(command, previous_command)

            if action == "help":
                self.show_help()
            elif action == "info":
                self.show_word_info(command)
            elif action == "manual":
                self.manual_update(command)
            elif action == "chat":
                check = self.chat_mode(command)
                if check == "quit":
                    break

            elif action == "show_all":
                self.show_all(command)
            elif action == "show_categories":
                self.print_categories()
            else:
                check = self.handle_specific_action(action, command)
                if check == "quit":
                    break
            
            previous_command = command

    def show_help(self) -> None:
        """Display help information."""
        mode = "dictionary" if isinstance(self, WordDictionary) else "trainer"
        self.ui_manager.show_help(console, mode)

    def parse_command(self, command: str, previous_command: str) -> Tuple[str, str]:
        """Parse the user input and return the command and the action to be performed."""
        if command.startswith("/h"):
            return "", "help"
        elif command.startswith("/info"):
            return command[5:].strip() or previous_command, "info"
        elif command.startswith("/i"):
            return command[2:].strip() or previous_command, "info"
        elif command.startswith("/all"):
            return command[4:], "show_all"
        elif command.startswith("/a"):
            return command[2:].strip(), "show_all"
        elif command.startswith("/cat"):
            return "", "show_categories"
        elif command.startswith("/ct"):
            return "", "show_categories"
        elif command.startswith("/man"):
            return command[7:].strip() or previous_command, "manual"
        elif command.startswith("/m"):
            return command[2:].strip() or previous_command, "manual"
        elif command.startswith("/conv"):
            return command[13:].strip() or previous_command, "chat"
        elif command.startswith("/c"):
            return command[2:].strip() or previous_command, "chat"
        elif command.startswith("/upd"):
            return command[7:].strip(), "update"
        elif command.startswith("/u"):
            return command[2:].strip(), "update"
        elif command.startswith("/del"):
            return command[7:].strip(), "delete"
        elif command.startswith("/d"):
            return command[2:].strip(), "delete"
        else:
            return command, "specific"

    def show_word_info(self, word: str) -> None:
        """Print information about a word."""
        word = self.word_manager.fetch_word(word)
        console.print(word)
    
    def show_all(self, category: str="") -> None:
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

    def chat_mode(self, word: str) -> Optional[str]:
        """Start a chat session."""
        if not word:
            console.print("You didn't provide any words to chat with.")
            return
        
        self.teacher.init_convrsation(word)
        is_first = True
        while True:
            question = "Hello!" if is_first else self.get_multiline_input()
            is_first = False
            if question.startswith("/b"):
                break
            elif question.startswith("/q"):
                return 'quit'
            answer = self.teacher.conversation(question)
            self.display_chat_answer(answer)
        
    def draw_stream(self, stream: Generator, mode: str = 'chat') -> str:
        with Live(console=console, refresh_per_second=20) as live:
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

    def print_categories(self) -> None:
        self.ui_manager.show_categories(console, self.word_manager)

    def handle_specific_action(self, action: str, command: str) -> None:
        """Handle mode-specific actions. To be overridden by subclasses."""
        pass

class WordDictionary(BaseWordApp):
    """Class for dictionary mode of the application."""

    def handle_specific_action(self, action: str, word: str) -> None:
        if action == "update":
            self.process_word(word, is_update=True)
        elif action == "specific":
            self.process_word(word, is_update=False)
        elif action == "delete":
            self.delete_word(word)

    def process_word(self, command: str, is_update: bool) -> None:
        """Process a word. Or update an existing one."""
        layout: Layout = self.ui_manager.create_layout()
        self.ui_manager.update_command_panel(layout, command)
        word = self.word_manager.fetch_word(command)
        if word and not is_update:
            self.display_existing_word(layout, word)
        elif command.strip():
            self.process_new_word(layout, command, is_update)

    def display_existing_word(self, layout: Layout, word: Word) -> None:
        """Display an existing word in the database."""
        with Live(layout, console=console, refresh_per_second=4) as live:
            self.ui_manager.display_word(layout, word)
            live.update(layout)
        self.word_manager.increment_counter(word.word)
        self.word_manager.process_state(word.word, -1)

    def process_new_word(self, layout: Layout, word: str, rewrite: bool) -> None:
        """Process a new word. Or rewrite an existing one."""
        with Live(layout, console=console, refresh_per_second=4) as live:
            explanation_text, translation_text = self.generate_explanations(word, layout, live)
        warning = " ([red]Previous word data will be lost[white])" if rewrite else ""
        answer: str = console.input(f'Save the word?{warning} : [yellow]y [magenta]optional[white](category) or press Enter to skip > ')
        answer = answer.strip().lower()
        if answer.startswith("y"):
            category = answer.replace("y", "").strip()
            self.word_manager.insert_word(word, category, explanation_text, translation_text)

    def generate_explanations(self, word: str, layout: Layout, live: Live) -> Tuple[str, str]:
        """Generate explanations and translations for a given word."""
        explanation_text: str = ""
        translation_text: str = ""
        
        explanation = self.teacher.explainer(word)
        for chunk in explanation:
            explanation_text += chunk['response']
            self.ui_manager.update_left_panel(layout, explanation_text)
            live.update(layout)

        translation = self.teacher.translator(explanation_text)
        for chunk in translation:
            translation_text += chunk['response']
            self.ui_manager.update_right_panel(layout, translation_text)
            live.update(layout)
        
        return explanation_text, translation_text

class WordTrainer(BaseWordApp):
    """Class for trainer mode of the application."""
    def __init__(self):
        super().__init__()
        self.used_words = set()

    def run(self) -> None:
        super().run()

    def handle_specific_action(self, action: str, command: str) -> Optional[str]:
        return self.start_training(command)
    
    def handle_specific_action(self, action: str, word: str) -> None:
        if action == "delete":
            self.delete_word(word)
        elif action == "specific":
            check = self.start_training(word)
            if check == "quit":
                return "quit"

    def start_training(self, category: str = "") -> Optional[str]:
        include_mastered = False
        if category.endswith(" all"):
            category = category[:-4].strip()
            include_mastered = True
        
        category = category if category else None
        available_words = self.word_manager.fetch_words(category)
        
        while True:
            self.print_training_stats(category)
            word = self.select_word(available_words, include_mastered)
            if not word:
                console.print("No more words available for training. Resetting used words.")
                self.used_words.clear()
                word = self.select_word(available_words, include_mastered)
                if not word:
                    console.print("No words available for training.")
                    break
            check = self.start_game()
            if check == "quit":
                return "quit"
            
            riddle = self.word_riddle(word)
            user_guess = ""
            while not user_guess:
                user_guess = console.input("[green]Your guess > ").strip().lower()
            if not user_guess:
                continue

            user_guess = self.game_conversation(word, riddle, user_guess)
            if user_guess == "quit":
                return "quit"
            if user_guess == "/q" or user_guess == "/bye":
                return 'quit'
            
            elif user_guess.startswith("/i"):
                self.show_word_info(word.word)
                continue
            elif user_guess.startswith("/c"):
                check = self.chat_mode(word.word)
                if check == "quit":
                    return "quit"
                continue

            grade = self.grade_guess(word, user_guess)
            if grade == "quit":
                return 'quit'
            
    def start_game(self) -> Optional[str]:
        check = console.input("[green]Are you ready?[white] >")
        counter = 0
        while True:
            if check.strip().lower() in ["n", "no", "not ready", "not yet", "nope", "nah", "nay"]:
                counter += 1
                game = self.teacher.game_intro(counter)
                intro = self.draw_stream(game, mode='generate')
                check = console.input("[green]Now? [white]> ")  
            elif check.strip().lower() == "/q":
                return "quit"
            else:
                break

    def game_conversation(self, word: Word, riddle: str, question: str) -> str:
        if question.strip().startswith("?"):
            command = question.strip()[1:]
            self.teacher.init_qa(word.word)
            self.teacher.append_content('Hello!', role='user')
            self.teacher.append_content(riddle, role='assistant')
            while True :
                answer = self.teacher.conversation(command)
                full_answer = self.draw_stream(answer, mode='chat')
                check = console.input("[green]Your guess >")
                if check == "/q":
                    return "quit"
                elif not check.strip().startswith("?") :
                    return check
                else :
                    command = check[1:]
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
        selected_word = random.choices(available_words, weights=weights, k=1)[0]
        self.used_words.add(selected_word.word)
        return selected_word

    def word_riddle(self, word: Word) -> str:
        riddle = self.teacher.riddler(word.word)
        with Live(console=console, refresh_per_second=20) as live:
            full_riddle = f"{ROBOT_EMOJI} "
            for chunk in riddle:
                full_riddle += chunk['response']
                self.ui_manager.update_converation_output(full_riddle, live)
            return full_riddle

    def grade_guess(self, word: Word, guess: str) -> Optional[str]:
        if guess.strip().lower() == word.word.lower():
            console.print(f"{ROBOT_EMOJI} [green]Correct!\n [white]Literaly equals to the correct answer. Moving to the next word.\n")
            self.word_manager.process_state(word.word, 1)
            check = console.input(f"Ready to the next word? >")
            if check.strip().lower() == "/q":
                return "quit"
           
        else:
            grade = self.teacher.grader(word.word, guess)
            full_grade = f"{ROBOT_EMOJI} "
            with Live(console=console, refresh_per_second=20) as live:
                for chunk in grade:
                    full_grade += chunk['response']
                    self.ui_manager.update_converation_output(full_grade, live)
            if full_grade.replace(ROBOT_EMOJI,'').strip().lower().startswith("correct"):
                console.print("Moving to the next word.\n")
                self.word_manager.process_state(word.word, 1)
            else:
                self.word_manager.process_state(word.word, -1)
                check = console.input("Would you like to chat about this word? (y/n): ").lower().strip()
                if check == "y":
                    check = self.chat_mode(word.word)
                    if check == "quit":
                        return "quit"
                elif check == "/q":
                    return "quit"

    def print_training_stats(self, category: str = None) -> None:
        self.ui_manager.show_training_stats(console, self.word_manager, category)
        