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
    
@dataclass
class IrregularVerb:
    base_form: str
    past_simple: str
    past_participle: str
    ask_counter: int
    state: int

@dataclass
class GrammarTheme:
    name: str
    description: str

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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS irregular_verbs
            (base_form TEXT PRIMARY KEY, past_simple TEXT, past_participle TEXT,
             ask_counter INTEGER, state INTEGER)
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS grammar_themes
            (name TEXT PRIMARY KEY, description TEXT)
        ''')

    def _migrate_database(self) -> None:
        self.cursor.execute("PRAGMA table_info(words)")
        columns = [column[1] for column in self.cursor.fetchall()]
        
        if "state" not in columns:
            self.cursor.execute("ALTER TABLE words ADD COLUMN state INTEGER DEFAULT 0")
        
        self.conn.commit()

    def is_category_available(self, category: str) -> bool:
        return len(self.fetch_words(category)) > 0

    def insert_word(self, word: str, category: str, explanation_en: str, explanation_ru: str) -> None:
        """Insert a new word into the database. If the word already exists, update it."""
        self.cursor.execute("SELECT * FROM words WHERE word = ?", (word,))
        existing = self.cursor.fetchone()
        if existing:
            new_category = existing[1] if not category else category
            ask_counter = existing[4]
            state = existing[5]
            query = '''
                UPDATE words 
                SET category = ?, explanation_en = ?, explanation_ru = ?, ask_counter = ?, state = ?
                WHERE word = ?
            '''
            params = (new_category, explanation_en, explanation_ru, ask_counter, state, word)
        else:
            query = '''
                INSERT INTO words 
                (word, category, explanation_en, explanation_ru, ask_counter, state) 
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            params = (word, category, explanation_en, explanation_ru, 1, 0)
        
        self.cursor.execute(query, params)
        self.conn.commit()

    def increment_word_counter(self, word: str) -> None:
        """Increment the ask counter of a word."""
        current_word = self.fetch_word(word)
        if current_word:
            new_counter = current_word.ask_counter + 1
            self.cursor.execute("UPDATE words SET ask_counter = ? WHERE word = ?", (new_counter, word))
            self.conn.commit()

    def set_word_state(self, word: str, state: int) -> None:
        self.cursor.execute("UPDATE words SET state = ? WHERE word = ?", (state, word))
        self.conn.commit()

    def set_category(self, word: str, category: str) -> None:
        self.cursor.execute("UPDATE words SET category = ? WHERE word = ?", (category, word))
        self.conn.commit()

    def process_word_state(self, word: str, offset: int) -> None:
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
        if category == 'all' or category is None:
            self.cursor.execute("SELECT * FROM words")
        elif category:
            self.cursor.execute("SELECT * FROM words WHERE category = ?", (category,))
        else:
            self.cursor.execute("SELECT * FROM words WHERE category = ''")
        
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

    def add_irregular_verb(self, verb: IrregularVerb) -> None:
        self.cursor.execute('''
            INSERT OR REPLACE INTO irregular_verbs (base_form, past_simple, past_participle, ask_counter, state)
            VALUES (?, ?, ?, ?, ?)
        ''', (verb.base_form, verb.past_simple, verb.past_participle, verb.ask_counter, verb.state))
        self.conn.commit()

    def get_all_irregular_verbs(self) -> List[IrregularVerb]:
        self.cursor.execute('SELECT * FROM irregular_verbs')
        return [IrregularVerb(*row) for row in self.cursor.fetchall()]

    def delete_irregular_verb(self, base_form: str) -> bool:
        """Delete an irregular verb from the database."""
        is_exist = self.get_irregular_verb(base_form)
        if not is_exist:
            return False
        self.cursor.execute("DELETE FROM irregular_verbs WHERE base_form = ?", (base_form,))
        self.conn.commit()
        return True
    
    def get_irregular_verb(self, base_form: str) -> Optional[IrregularVerb]:
        self.cursor.execute('SELECT * FROM irregular_verbs WHERE base_form = ?', (base_form,))
        result = self.cursor.fetchone()
        return IrregularVerb(*result) if result else None
    
    def increment_verb_counter(self, base_form: str) -> None:
        """Increment the ask counter of an irregular verb."""
        current_verb = self.get_irregular_verb(base_form)
        if current_verb:
            new_counter = current_verb.ask_counter + 1
            self.cursor.execute("UPDATE irregular_verbs SET ask_counter = ? WHERE base_form = ?", (new_counter, base_form))
            self.conn.commit()

    def process_verb_state(self, base_form: str, offset: int) -> None:
        """Process the state of an irregular verb by incrementing or decrementing it."""
        current_verb = self.get_irregular_verb(base_form)
        if current_verb:
            new_state = max(0, min(len(STATES)-1, current_verb.state + offset))
            self.cursor.execute("UPDATE irregular_verbs SET state = ? WHERE base_form = ?", (new_state, base_form))
            self.conn.commit()
    
    def add_grammar_theme(self, theme: GrammarTheme) -> None:
        self.cursor.execute('''
            INSERT OR REPLACE INTO grammar_themes (name, description)
            VALUES (?, ?)
        ''', (theme.name, theme.description))
        self.conn.commit()

    def delete_grammar_theme(self, name: str) -> bool:
        """Delete a grammar theme from the database."""
        is_exist = self.get_grammar_theme(name)
        if not is_exist:
            return False
        self.cursor.execute("DELETE FROM grammar_themes WHERE name = ?", (name,))
        self.conn.commit()
        return True

    def get_all_grammar_themes(self) -> List[GrammarTheme]:
        self.cursor.execute('SELECT * FROM grammar_themes ORDER BY name')
        return [GrammarTheme(*row) for row in self.cursor.fetchall()]

    def get_grammar_theme(self, name: str) -> Optional[GrammarTheme]:
        self.cursor.execute('SELECT * FROM grammar_themes WHERE name = ?', (name,))
        result = self.cursor.fetchone()
        return GrammarTheme(*result) if result else None