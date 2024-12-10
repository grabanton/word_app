import sqlite3

def reset_grammar_themes():
    db_path = "E:\learning\english\word_app\.data\words_database.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Удаляем таблицу grammar_themes, если она существует
        cursor.execute("DROP TABLE IF EXISTS irregular_verbs")
        print("Таблица irregular_verbs успешно удалена.")

        # Сохраняем изменения
        conn.commit()
    except sqlite3.Error as e:
        print(f"Произошла ошибка при удалении таблицы: {e}")
    finally:
        # Закрываем соединение
        conn.close()

if __name__ == "__main__":
    reset_grammar_themes()
    print("Скрипт завершен. При следующем запуске приложения будет создана новая таблица irregular_verbs.")