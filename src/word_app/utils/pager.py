import curses
from rich.console import Console
from rich.panel import Panel
from typing import List

class MyPager:
    def __init__(self, header: str, lines: List[str]):
        self.header = header
        self.lines = lines
        
        console = Console(record=True, width=120)
        header_panel = Panel(self.header, width=console.width-1)
        console.print(header_panel)
        self.rendered_header = console.export_text().strip().split('\n')

    def draw_screen(self, stdscr, start_line: int) -> None:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        for i, line in enumerate(self.rendered_header):
            stdscr.addstr(i, 0, line[:width])

        avail_height = height - len(self.rendered_header) - 1

        for idx, line in enumerate(self.lines[start_line:start_line+avail_height]):
            stdscr.addstr(len(self.rendered_header) + idx, 0, line[:width-1])

        stdscr.refresh()

    def main(self, stdscr) -> None:
        curses.curs_set(0)
        start_line = 0

        while True:
            self.draw_screen(stdscr, start_line)
            key = stdscr.getch()

            if key == ord('q'):
                return
            elif ( key == curses.KEY_UP or key == ord('k') ) and start_line > 0:
                start_line -= 1
            elif ( key == curses.KEY_DOWN or key == ord('j') ) and start_line < len(self.lines) - len(self.rendered_header) - 1:
                start_line += 1

    def run(self) -> None:
        curses.wrapper(self.main)

def format_with_dashes(word: str, length: int) -> str:
    return f"{word:<{length}}".replace(" ", "-")