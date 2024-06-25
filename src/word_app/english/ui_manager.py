from typing import Callable
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live
from rich.console import Console, Group
from rich.padding import Padding
from rich import box
from math import floor
from itertools import chain
from .word_manager import Word, WordManager, STATES
from ..utils import MyPager

# Constants for appearance
STYLE_LEFT = "rgb(200,180,120)"
STYLE_RIGHT = "rgb(100,120,180)"
STYLE_COMMAND = "green"
ROBOT_EMOJI = "\U0001F916"

class UIManager:
    """Class to manage the user interface."""
    @staticmethod
    def create_layout() -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="body", ratio=1),
        )
        layout["header"].split_column(
            Layout(name="title", ratio=2),
            Layout(name="command", ratio=3),
        )
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        
        UIManager._update_panel(layout=layout, panel_name="title", text="", box_style=box.MINIMAL)
        UIManager._update_panel(layout=layout, panel_name="command", text="", box_style=box.HORIZONTALS, color=STYLE_COMMAND)
        UIManager._update_panel(layout=layout, panel_name="left", text="", box_style=box.MARKDOWN, color=STYLE_LEFT)
        UIManager._update_panel(layout=layout, panel_name="right", text="", box_style=box.MARKDOWN, color=STYLE_RIGHT)
        
        return layout

    @staticmethod
    def display_word(layout: Layout, word: Word) -> None:
        UIManager._update_panel(layout=layout, panel_name="command", text=word.word, box_style=box.HORIZONTALS, color=STYLE_COMMAND, renderable_class=Text)
        UIManager._update_panel(layout=layout, panel_name="left", text=word.explanation_en, box_style=box.MARKDOWN, color=STYLE_LEFT, renderable_class=Markdown)
        UIManager._update_panel(layout=layout, panel_name="right", text=word.explanation_ru, box_style=box.MARKDOWN, color=STYLE_RIGHT, renderable_class=Markdown)

    @staticmethod
    def update_left_panel(layout: Layout, text: str) -> None:
        UIManager._update_panel(layout=layout, panel_name="left", text=text, box_style=box.MARKDOWN, color=STYLE_LEFT, renderable_class=Markdown)

    @staticmethod
    def update_right_panel(layout: Layout, text: str) -> None:
        UIManager._update_panel(layout=layout, panel_name="right", text=text, box_style=box.MARKDOWN, color=STYLE_RIGHT, renderable_class=Markdown)

    @staticmethod
    def update_command_panel(layout: Layout, text: str) -> None:
        UIManager._update_panel(layout=layout, panel_name="command", text=text, box_style=box.HORIZONTALS, color=STYLE_COMMAND, renderable_class=Text)

    @staticmethod
    def update_converation_output(answer: str, live: Live) -> None:
        markdown = Markdown(answer, style="blue")
        padded_markdown = Padding(markdown, (1,0))
        live.update(Group(padded_markdown))
        live.refresh()

    @staticmethod
    def _update_panel(
        layout: Layout, 
        panel_name: str, 
        text: str, 
        box_style: box, 
        color: str = "white", 
        renderable_class: Callable = Text
    ) -> None:
        content = renderable_class(text, justify="center") if renderable_class == Text else renderable_class(text)
        layout[panel_name].update(Panel(content, style=color, box=box_style))
    
    @staticmethod
    def show_help(console: Console, mode: str = "dictionary") -> None:
        if mode == "dictionary":
            UIManager._show_dictionary_help(console)
        elif mode == "trainer":
            UIManager._show_trainer_help(console)
        else:
            console.print(f"[bold red]Unknown mode: {mode}[/bold red]")

    @staticmethod
    def _show_dictionary_help(console: Console) -> None:
        table = Table(
            title="Dictionary Mode Commands", 
            box=box.SQUARE, 
            border_style="bold", 
            show_header=True, 
            header_style="bold cyan",
            padding=(0, 1)
        )
        
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="magenta")

        states = "\nState is a numeric value:\n\n" + "\n".join([f"  {i} <- {state}" for i, state in enumerate(STATES)])
        
        rows = [
            ("{word or phrase}", "Look up a word or phrase."),
            ("/h, /help", "Show this help message"),
            ("/q, /quit", "Quit the program"),
            ("/u, /upd {word}", "Update an existing word's explanation and translation."),
            ("/i, /info {word or phrase}", ("Show information about a word. If word is not provided, show previous word's information."
                                            "The state is a numeric value, but for simplicity, it's shown as a string. More info below.")),
            ("/ct, /cat", "Show all used categories."),
            ("/a, /all {category}" , "Show all saved words in a specified category. \nIf no category is provided, show all Uncotegorized words. \nUse 'all' to show all words."),
            ("/d, /del {word or phrase}", "Delete a word from the database. For this operation particular word is required."),
            ("/c, /conv {word or phrase}", f"Start a chat about a word or phrase. Uses the previous word if none provided."),
            (f"/b, /bye (chat {ROBOT_EMOJI} mode only)", f"End the current chat session and return to word lookup mode."),
            ("/m, /man {word or phrase}", f"Manually update word's category and state.{states}"),
        ]

        for i, (command, description) in enumerate(rows):
            table.add_row(command, description)
            if i < len(rows) - 1:
                table.add_row("", "")

        console.print(table)
        
        console.print("\n[bold]Usage Tips:[/bold]")
        console.print("• When adding a new word, you can specify its category after typing 'y' when prompted to save.")
        console.print(f"• In chat {ROBOT_EMOJI} mode, end your input with '\\' to continue on a new line.\n\n")

    @staticmethod
    def _show_trainer_help(console: Console) -> None:
        table = Table(
            title="Trainer Mode Commands", 
            box=box.SQUARE, 
            border_style="bold", 
            show_header=True, 
            header_style="bold cyan",
            padding=(0, 1)
        )
        
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="magenta")

        rows = [
            ("/h, /help", "Show this help message."),
            ("/q, /quit", "Quit the training session."),
            ("/i, /info", "Show information about the current word."),
            ("/l, /lookup {word}", "Look up a specific word."),
            ("/ct, /cat", "Show all used categories."),
            ("/a, /all {category}" , "Show all saved words in a specified category. \nIf no category is provided, show all Uncotegorized words. \nUse 'all' to show all words."),
            ("/d, /del {word or phrase}", "Delete a word from the database. For this operation particular word is required."),
            ("/c, /conv", f"Start a chat {ROBOT_EMOJI} about the current word."),
            (f"/b, /bye (chat {ROBOT_EMOJI} mode only)", f"End the current chat session and return to training."),
            ("? {question}", "Ask for more information about the current word (In a guess mode)."),
            ("{guess}", "Make a guess for the current word."),
        ]

        for i, (command, description) in enumerate(rows):
            table.add_row(command, description)
            if i < len(rows) - 1:
                table.add_row("", "")

        console.print(table)
        
        console.print("\n[bold]Training Tips:[/bold]")
        console.print("• The trainer will provide an explanation of a word without mentioning it.")
        console.print("• Try to guess the word based on the explanation.")
        console.print("• If your guess is correct, the word's state will improve.")
        console.print("• If your guess is incorrect, you'll have the option to chat about the word.")
        console.print("• Words in the 'mastered' state won't appear unless you choose to include all words.")
        console.print(f"• You can start a chat {ROBOT_EMOJI} about any word to learn more about it.")
        console.print("• Use /i to see the current state of the word.\n\n")

    @staticmethod
    def show_categories(console: Console, manager: WordManager) -> None:
        words = manager.fetch_words(category='all')
        total_words = len(words)
        category_counts = {}
        for word in words:
            category_counts[word.category] = category_counts.get(word.category, 0) + 1

        table = Table(title="[green]Select a Category.\nOr skip to train all words.")
        table.add_column("Category Name", style="cyan")
        table.add_column("Average State", style="yellow")
        table.add_column("Count", style="magenta")

        table.add_row("Total Words", '', str(total_words))
        table.add_row("", "", "")
        for cat, count in category_counts.items():
            state = STATES[floor(manager.category_average(cat))]
            name = cat if cat else "Uncategorized"
            table.add_row(name, str(state), str(count))

        console.print(table)

    @staticmethod
    def show_training_stats(console: Console, manager: WordManager, category: str = None):
        words = manager.fetch_words(category)
        total_words = len(words)
        state_counts = {state: sum(1 for w in words if w.state == i) for i, state in enumerate(STATES)}
        # state_counts['None'] = sum(1 for w in words if w.state is None)

        table = Table(title="Training Stats")
        table.add_column("State", style="cyan")
        table.add_column("Count", style="magenta")

        table.add_row("Total Words", str(total_words))
        table.add_row("", "")
        for state, count in state_counts.items():
            table.add_row(state, str(count))
        console.print("\n")
        console.print(table)

    @staticmethod
    def show_all_words(console: Console, manager: WordManager, category:str = None) -> None:
        header = f"{'Word':<80} {'Category':<15} {'State'}"
        words = manager.fetch_words(category=category)
        words.sort(key=lambda w: f"{w.state}{w.word}")
        lines = []
        for w in words:
            word =w.word
            category = w.category if w.category else "Uncategorized"
            state = STATES[w.state]
            lines.append(f"{word:<80} {category:<15} {state}")
        rows = ['-' * console.width for w in words]
        lines = [*chain(*zip(lines, rows))]
        pager = MyPager(header, lines)
        pager.run()