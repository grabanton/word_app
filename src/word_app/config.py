import os
import yaml
from pathlib import Path
from typing import Dict
import logging

class Config:
    def __init__(self) -> None:
        self.config_path = self._find_config_file()
        self.config = self._load_config()

    def _find_config_file(self) -> Path:
        possible_paths = [
            Path("config/config.yaml"),
            Path("../config/config.yaml"),
            Path("../../config/config.yaml"),
        ]
        for path in possible_paths:
            if path.exists():
                return path
        raise FileNotFoundError("Config file not found")

    def _load_config(self) -> Dict:
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)

    def _resolve_path(self, path):
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(os.path.dirname(self.config_path), path))
        if not os.path.exists(path):
            logging.info(f'Database not found. It will be initialized as {path}')
        return path

    def get_llm_config(self) -> Dict:
        return self.config['llm']
    
    def get_voice_config(self) -> Dict:
        return self.config['voice']

    def get_database_path(self):
        return self._resolve_path(self.config['database']['path'])

    def get_obsidian_config(self):
        return self.config['obsidian']

    def get_streak_threshold(self) -> int:
        return self.config['app']['streak_threshold']

    def get_prompt_path(self, prompt_name):
        base_path = self.config['llm']['prompts']['system']['base_path']
        file_name = self.config['llm']['prompts']['system']['files'].get(prompt_name)
        if file_name:
            full_path = self._resolve_path(os.path.join(base_path, file_name))
            return full_path
        raise ValueError(f"Prompt '{prompt_name}' not found in config")

config = Config()

def get_llm_config() -> Dict:
    return config.get_llm_config()

def get_database_path() -> str:
    return config.get_database_path()

def get_prompt_path(prompt_name) -> str:
    return config.get_prompt_path(prompt_name)

def get_voice_config() -> Dict:
    return config.get_voice_config()

def get_obsidian_config() -> Dict:
    return config.get_obsidian_config()

def get_streak_threshold() -> int:
    return config.get_streak_threshold()