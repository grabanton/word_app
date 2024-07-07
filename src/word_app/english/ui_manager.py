from typing import Callable, List
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
from .word_manager import Word, WordManager, IrregularVerb, GrammarTheme, STATES
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
    def show_help(console: Console, mode: str = "worddictionary") -> None:
        base_commands = [
            ("/h, /help", "Show this help message"),
            ("/q, /quit", "Quit the current mode"),
            ("/i, /info {word}", "Show information about a word"),
            ("/ct, /cat", "Show all used categories"),
            ("/a, /all {category}", "Show all saved words in a specified category"),
            ("/d, /del {word}", "Delete a word from the database"),
            ("/c, /conv {word}", "Start a chat about a word or phrase"),
            ("/b, /bye", "End the current chat session (chat mode only)"),
            ("/m, /man {word}", "Manually update word's category and state"),
        ]

        specific_commands = {
            "worddictionary": [
                ("/u, /upd {word}", "Update an existing word's explanation and translation"),
                ("{word}", "Look up a word or phrase"),
            ],
            "wordstutor": [
                ("/l, /lookup {word}", "Look up a specific word"),
                ("/n, /new {word}", "Explain a new word and add it to the database"),
                ("/?, /question", "Ask for more information about the current word (guess mode)"),
                ("{category}", "Start training with words from the specified category"),
            ],
            "verbstutor": [
                ("/nv, /newverb {verb}", "Add new irregular verb"),
                ("/dv, /delverb {verb}", "Delete an irregular verb"),
                ("/av, /allverbs", "List of all avalable irregular verbs"),
                ("/cv, /convverb {verb}", "Start a conversation about an irregular verb"),
                ("/g, /game", "Play a game with irregular verbs"),
                ("{verb}", "Watch an irregular verbs"),
            ],
            "grammartutor": [
                ("/nt, /newtheme {theme}", "Add a new grammar theme"),
                ("/dt, /deltheme {theme}", "Delete a grammar theme"),
                ("/at, /allthemes", "List all avalable grammar themes"),
                ("{theme}", "Start a conversation about a specific grammar theme"),
            ],
        }

        title = f"{mode.capitalize()} Mode Commands"
        table = Table(title=title, box=box.SQUARE, border_style="bold", show_header=True, header_style="bold cyan", padding=(0, 1))
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="magenta")

        for command, description in base_commands:
            table.add_row(command, description)

        table.add_row("", "")

        for command, description in specific_commands.get(mode.lower(), []):
            table.add_row(command, description)

        console.print(table)

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
    def show_words_stats(console: Console, manager: WordManager, category: str = None):
        words = manager.fetch_words(category)
        total_words = len(words)
        state_counts = {state: sum(1 for w in words if w.state == i) for i, state in enumerate(STATES)}

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
        header = f"{'Word':<80} {'Category':<20} {'State'}"
        words = manager.fetch_words(category=category)
        words.sort(key=lambda w: f"{w.state}{w.word}")
        lines = []
        for w in words:
            word =w.word
            category = w.category if w.category else "Uncategorized"
            state = STATES[w.state]
            lines.append(f"  {word:<80} {category:<20} {state}")
        rows = ['-' * console.width for w in words]
        lines = [*chain(*zip(lines, rows))]
        pager = MyPager(header, lines)
        pager.run()

    @staticmethod
    def show_all_verbs(console: Console, manager: WordManager) -> None:
        header = f"{'Base Form':<20} {'Past Simple':<20} {'Past Participle':<55} {'State'}"
        verbs = manager.get_all_irregular_verbs()
        verbs.sort(key=lambda v: f"{v.state}{v.base_form}")
        lines = []
        for v in verbs:
            base_form = v.base_form
            past_simple = v.past_simple
            past_participle = v.past_participle
            state = STATES[v.state]
            lines.append(f"  {base_form:<20} {past_simple:<20} {past_participle:<55} {state}")
        rows = ['-' * console.width for v in verbs]
        lines = [*chain(*zip(lines, rows))]
        pager = MyPager(header, lines)
        pager.run()

    @staticmethod
    def show_all_themes(console: Console, manager: WordManager) -> None:
        header = f"{'Theme':<40} {'Description'}"
        themes = manager.get_all_grammar_themes()
        lines = []
        for theme in themes:
            name = theme.name
            description = theme.description
            lines.append(f"  {name:<40} {description}")
        rows = ['-' * console.width for theme in themes]
        lines = [*chain(*zip(lines, rows))]
        pager = MyPager(header, lines)
        pager.run()

    @staticmethod
    def show_verbs_stats(console: Console, verbs: List[IrregularVerb]) -> None:
        total_verbs = len(verbs)
        state_counts = {state: sum(1 for v in verbs if v.state == i) for i, state in enumerate(STATES)}

        table = Table(title="Irregular Verbs Stats")
        table.add_column("State", style="cyan")
        table.add_column("Count", style="magenta")

        table.add_row("Total Verbs", str(total_verbs))
        table.add_row("", "")
        for state, count in state_counts.items():
            table.add_row(state, str(count))
        console.print("\n")
        console.print(table)

    @staticmethod
    def show_grammar_themes(console: Console, themes: List[GrammarTheme]) -> None:
        table = Table(
            title="Grammar Themes",
            box=box.SQUARE,
            border_style="bold",
            show_header=True,
            header_style="bold cyan",
            padding=(0, 1)
        )
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        for theme in themes:
            table.add_row(theme.name, theme.description)
        console.print(table)
