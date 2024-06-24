#!/bin/bash

# Получаем полный путь к директории скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Переходим в корневую директорию проекта (на уровень выше scripts)
cd "$SCRIPT_DIR/.."

# Запускаем Python-скрипт через Poetry
poetry run python -m src.word_app.main "$@"

# Возвращаемся в исходную директорию
cd "$SCRIPT_DIR"