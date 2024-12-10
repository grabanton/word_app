@echo off
setlocal enabledelayedexpansion

REM Получаем полный путь к директории скрипта
set "SCRIPT_DIR=%~dp0"

REM Переходим в корневую директорию проекта (на уровень выше scripts)
cd /d "%SCRIPT_DIR%\.."

REM Добавляем src директорию в PYTHONPATH
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

REM Запускаем Python-скрипт через Poetry
poetry run python -m word_app.main %*

REM Возвращаемся в исходную директорию
cd /d "%SCRIPT_DIR%"