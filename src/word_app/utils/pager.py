import curses
from rich.console import Console
from rich.panel import Panel
from typing import List

class MyPager:
    def __init__(self, header: str, lines: List[str]):
        self.header = header
        self.lines = lines
        self.filtered_lines = lines.copy()
        self.filter_mode = False
        self.filter_text = ""
        self._update_header()

    def _update_header(self):
        console = Console(record=True, width=120)
        header_content = self.header + "\n"  # Add empty line after title
        if self.filter_mode:
            header_content += f"Filter: {self.filter_text}"
        header_panel = Panel(header_content, width=console.width-1)
        console.print(header_panel)
        self.rendered_header = console.export_text().strip().split('\n')

    def draw_screen(self, stdscr, start_line: int) -> None:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        for i, line in enumerate(self.rendered_header):
            stdscr.addstr(i, 0, line[:width])

        header_height = len(self.rendered_header)
        avail_height = height - header_height - 1

        for idx, line in enumerate(self.filtered_lines[start_line:start_line+avail_height]):
            stdscr.addstr(len(self.rendered_header) + idx, 0, line[:width-1])

        stdscr.refresh()

    def main(self, stdscr) -> None:
        curses.curs_set(0)
        start_line = 0

        while True:
            self.draw_screen(stdscr, start_line)
            key = stdscr.getch()

            if self.filter_mode:
                if key == 27:  # ESC key
                    self.filter_mode = False
                    self.filter_text = ""
                    self.filtered_lines = self.lines.copy()
                    self._update_header()
                    start_line = 0
                elif key == curses.KEY_BACKSPACE or key == 127:
                    self.filter_text = self.filter_text[:-1]
                    self._apply_filter()
                    self._update_header()
                    start_line = 0
                elif 32 <= key <= 126:  # Printable characters
                    self.filter_text += chr(key)
                    self._apply_filter()
                    self._update_header()
                    start_line = 0
            else:
                if key == ord('q'):
                    return
                elif key == ord('f'):
                    self.filter_mode = True
                    self._update_header()
                    start_line = 0
                elif ( key == curses.KEY_UP or key == ord('k') ) and start_line > 0:
                    start_line -= 1
                elif ( key == curses.KEY_DOWN or key == ord('j') ) and start_line < len(self.filtered_lines) - len(self.rendered_header) - 1:
                    start_line += 1

    def run(self) -> None:
        curses.wrapper(self.main)

    def _apply_filter(self) -> None:
        if not self.filter_text:
            self.filtered_lines = self.lines.copy()
        else:
            # Keep track of separator lines and their positions
            filtered = []
            for i, line in enumerate(self.lines):
                if line.strip().startswith('---'):  # It's a separator
                    # Add separator if previous line was included
                    if filtered and i > 0 and any(self.filter_text.lower() in l.lower() for l in [self.lines[i-1], self.lines[i+1] if i+1 < len(self.lines) else '']):
                        filtered.append(line)
                elif self.filter_text.lower() in line.lower():
                    filtered.append(line)
            self.filtered_lines = filtered

def format_with_dashes(word: str, length: int) -> str:
    return f"{word:<{length}}".replace(" ", "-")
