import pytest
from unittest.mock import MagicMock, patch
from word_app.english.word_manager import WordManager, Word

@pytest.fixture
def word_manager():
    with patch('word_app.english.word_manager.sqlite3') as mock_sqlite3:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite3.connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Создаем словарь для хранения данных "базы данных"
        mock_db = {}
        
        def mock_execute(query, params=None):
            nonlocal mock_db
            params = params or []
            command = query.split()[0].upper()
            if command == "INSERT":
                word_key = params[0]  # для INSERT используем первый элемент как ключ
                mock_db[word_key] = tuple(params)
            elif command == "UPDATE":
                word_key = params[-1]  # для UPDATE используем последний элемент как ключ
                mock_db[word_key] = tuple(params[:-1])
            elif command == "SELECT":
                word_key = params[0]
                if word_key in mock_db:
                    mock_cursor.execute.return_value = [mock_db[word_key]]
                else:
                    mock_cursor.execute.return_value = [None]
            elif command == "DELETE":
                word_key = params[0]
                if word_key in mock_db:
                    del mock_db[word_key]
                    mock_cursor.execute.return_value = True
                else:
                    mock_cursor.execute.return_value = False
        
        mock_cursor.execute.side_effect = mock_execute
        
        def mock_fetchone():
            rows = mock_cursor.execute.return_value
            return rows[0] if rows and rows[0] else None
        
        def mock_fetchall():
            return list(mock_db.values())

        mock_cursor.fetchone.side_effect = mock_fetchone
        mock_cursor.fetchall.side_effect = mock_fetchall

        # Патчим метод get_database_path, чтобы он возвращал фиктивный путь
        with patch('word_app.english.word_manager.get_database_path', return_value=':memory:'):
            with patch('os.makedirs', MagicMock()):
                wm = WordManager()
                wm.conn = mock_connection
                wm.cursor = mock_cursor
                yield wm

def test_insert_and_fetch_word(word_manager):
    word = "test"
    category = "noun"
    explanation_en = "A trial"
    explanation_ru = "Испытание"
    
    word_manager.insert_word(word, category, explanation_en, explanation_ru)
    fetched_word = word_manager.fetch_word(word)
    
    assert fetched_word is not None
    assert fetched_word.word == word
    assert fetched_word.category == category
    assert fetched_word.explanation_en == explanation_en
    assert fetched_word.explanation_ru == explanation_ru
    assert fetched_word.ask_counter == 1
    assert fetched_word.state == 0

def test_increment_counter(word_manager):
    word = "counter_test"
    word_manager.insert_word(word, "verb", "To test", "Тестировать")
    initial_word = word_manager.fetch_word(word)
    initial_count = initial_word.ask_counter
    
    word_manager.increment_counter(word)
    updated_word = word_manager.fetch_word(word)
    assert updated_word.ask_counter == initial_count + 1

def test_process_state(word_manager):
    word = "state_test"
    word_manager.insert_word(word, "adjective", "Testable", "Тестируемый")
    initial_word = word_manager.fetch_word(word)
    initial_state = initial_word.state
    
    word_manager.process_state(word, 1)
    updated_word = word_manager.fetch_word(word)
    assert updated_word.state == initial_state + 1

def test_fetch_words_by_category(word_manager):
    word_manager.insert_word("word1", "noun", "Cat", "Кот")
    word_manager.insert_word("word2", "verb", "Run", "Бежать")
    
    nouns = word_manager.fetch_words("noun")
    assert len(nouns) == 1
    assert nouns[0].word == "word1"
    assert nouns[0].category == "noun"

def test_delete_word(word_manager):
    word = "delete_test"
    word_manager.insert_word(word, "noun", "Sample", "Образец")
    
    result = word_manager.delete_word(word)
    assert result is True
    
    deleted_word = word_manager.fetch_word(word)
    assert deleted_word is None

def test_category_average(word_manager):
    word_manager.insert_word("word1", "noun", "Cat", "Кот")
    word_manager.insert_word("word2", "noun", "Dog", "Собака")
    word_manager.insert_word("word3", "verb", "Run", "Бежать")
    
    word_manager.process_state("word1", 3)
    word_manager.process_state("word2", 2)
    
    avg = word_manager.category_average("noun")
    assert avg == (3 + 2) / 2