#!/bin/bash

# Получаем полный путь к директории скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Переходим в корневую директорию проекта (на уровень выше scripts)
cd "$SCRIPT_DIR/.."

# Добавляем src директорию в PYTHONPATH
export PYTHONPATH="$PWD/src:$PYTHONPATH"

# Запускаем Python-скрипт через venv
.venv/bin/python -m word_app.main "$@"

# Возвращаемся в исходную директорию
cd "$SCRIPT_DIR"
