import os
import sqlite3
from dataclasses import dataclass
from typing import Optional, List
from ..config import get_database_path

STATES = (
    'new',           
    'seen',         
    'learning',     
    'familiar',     
    'understood',
    'practiced', 
    'applied',   
    'confident', 
    'mastered'   
)

@dataclass
class Word:
    word: str
    category: str
    explanation_en: str
    explanation_ru: str
    ask_counter: int
    state: int

    def __str__(self) -> str:
        return f'{self.word} : Category - "{self.category}"; Asks - {self.ask_counter}; State - "{STATES[self.state]}"'
    
    def __repr__(self) -> str:
        return self.__str__()

class WordManager:
    """A class to manage the database of words."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WordManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        db_path = get_database_path()
        self._ensure_db_directory_exists(db_path)
        self.conn: sqlite3.Connection = sqlite3.connect(db_path)
        self.cursor: sqlite3.Cursor = self.conn.cursor()
        self._create_table()
        # self._migrate_database()

    def _ensure_db_directory_exists(self, db_path: str) -> None:
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            print(f"Created directory for database: {db_dir}")

    def _create_table(self) -> None:
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS words
            (word TEXT PRIMARY KEY, category TEXT, explanation_en TEXT, 
             explanation_ru TEXT, ask_counter INTEGER, state INTEGER)
        ''')
    
    def _migrate_database(self) -> None:
        self.cursor.execute("PRAGMA table_info(words)")
        columns = [column[1] for column in self.cursor.fetchall()]
        
        if "state" not in columns:
            self.cursor.execute("ALTER TABLE words ADD COLUMN state INTEGER DEFAULT 0")
        
        self.conn.commit()

    def insert_word(self, word: str, category: str, explanation_en: str, explanation_ru: str) -> None:
        """Insert a new word into the database. If the word already exists, update it."""
        self.cursor.execute("SELECT * FROM words WHERE word = ?", (word,))
        existing = self.cursor.fetchone()
        
        if existing:
            query = '''
                UPDATE words 
                SET category = ?, explanation_en = ?, explanation_ru = ?, ask_counter = ?, state = ?
                WHERE word = ?
            '''
            params = (category, explanation_en, explanation_ru, 1, 0, word)
        else:
            query = '''
                INSERT INTO words 
                (word, category, explanation_en, explanation_ru, ask_counter, state) 
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            params = (word, category, explanation_en, explanation_ru, 1, 0)
        
        self.cursor.execute(query, params)
        self.conn.commit()

    def increment_counter(self, word: str) -> None:
        """Increment the ask counter of a word."""
        current_word = self.fetch_word(word)
        if current_word:
            new_counter = current_word.ask_counter + 1
            self.cursor.execute("UPDATE words SET ask_counter = ? WHERE word = ?", (new_counter, word))
            self.conn.commit()

    def set_state(self, word: str, state: int) -> None:
        self.cursor.execute("UPDATE words SET state = ? WHERE word = ?", (state, word))
        self.conn.commit()

    def set_category(self, word: str, category: str) -> None:
        self.cursor.execute("UPDATE words SET category = ? WHERE word = ?", (category, word))
        self.conn.commit()

    def process_state(self, word: str, offset: int) -> None:
        """Process the state of a word by incrementing or decrementing it."""
        current_word = self.fetch_word(word)
        if current_word:
            new_state = max(0, min(len(STATES)-1, current_word.state + offset))
            self.cursor.execute("UPDATE words SET state = ? WHERE word = ?", (new_state, word))
            self.conn.commit()

    def fetch_word(self, word: str) -> Optional[Word]:
        """Fetch a word from the database by its name."""
        self.cursor.execute("SELECT word, category, explanation_en, explanation_ru, ask_counter, state FROM words WHERE word = ?", (word,))
        result: Optional[tuple] = self.cursor.fetchone()
        if result:
            return Word(
                word=result[0],
                category=result[1],
                explanation_en=result[2],
                explanation_ru=result[3],
                ask_counter=result[4],
                state=result[5]
            )
        return None
    
    def fetch_words(self, category: Optional[str] = None) -> List[Word]:
        """Fetch all words by category from the database."""
        if category:
            self.cursor.execute("SELECT * FROM words WHERE category = ?", (category,))
        else:
            self.cursor.execute("SELECT * FROM words")
        
        results = self.cursor.fetchall()
        return [Word(*result) for result in results]
    
    def delete_word(self, word: str) -> bool:
        """Delete a word from the database."""
        is_exist = self.fetch_word(word)
        if not is_exist:
            return False
        self.cursor.execute("DELETE FROM words WHERE word = ?", (word,))
        self.conn.commit()
        return True
    
    def category_average(self, category: str) -> float:
        """Calculate the average state of words in a category."""
        words = self.fetch_words(category)
        if not words:
            return 0
        return sum(word.state for word in words) / len(words)