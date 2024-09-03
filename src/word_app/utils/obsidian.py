import os
import yaml
from typing import Dict, Optional

from ..config import get_obsidian_config

header_example = """---
tags:
  - english
  - words
aliases: 
  - Personal emotions
  - Relationships and social interactions
  - Daily phrases and expressions
level: intermediate 
cat: intu3
unit: 3
count: 112
status: confident
score: 7
url: https://quizlet.com/kz/556943745/outcomes-int_unit-2-feelings-flash-cards/?funnelUUID=6a7b16fa-0b23-473b-a15c-e65a2ff9e666
date: 2024-08-30
---"""

class Obsidian:
    def __init__(self):
        self.config = get_obsidian_config()
        self.english_dir = self.config['english_dir']
        self.file_path = ""
        self.yaml_data = {}


    def find_file(self, category:str) -> None:
        for file in os.listdir(self.english_dir):
            file_path = os.path.join(self.english_dir, file)
            data = self.parse_yaml_header(file_path)
            if data.get('cat','') == category:
                self.set_file_path(file_path)
                break

    def set_file_path(self, file_path: str) -> None:
        self.file_path = file_path
        self.yaml_data = self.parse_yaml_header(self.file_path)

    def _extract_yaml_content(self,filepath:str) -> Optional[str]:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        yaml_content = []
        in_yaml_block = False
        for line in lines:
            if line.strip() == "---":
                if not in_yaml_block:
                    in_yaml_block = True
                    continue
                else:
                    break
            if in_yaml_block:
                yaml_content.append(line)

        return ''.join(yaml_content) if yaml_content else None

    def _parse_yaml(self, yaml_content: str) -> Dict:
        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML: ")
            return 

    def parse_yaml_header(self,filepath:str) -> Dict:
        yaml_content = self._extract_yaml_content(filepath)
        return self._parse_yaml(yaml_content) if yaml_content else {}

    def update_state(self, score:int, status:str) -> None:
        self.yaml_data['status'] = status
        self.yaml_data['score'] = score
        self.update_yaml_header(self.yaml_data)

    def update_yaml_header(self, new_header: Dict) -> None:
        if not os.path.exists(self.file_path):
            print(f"Error: File does not exist: {self.file_path}")
            return None

        with open(self.file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Split the content into YAML header and the rest
        parts = content.split('---', 2)
        if len(parts) < 3:
            print("Error: File does not have a valid YAML header")
            return

        # Parse the existing YAML header
        yaml_data = self._parse_yaml(parts[1])
        
        # Update the YAML data with new_header
        yaml_data.update(new_header)
        
        # Convert the updated YAML data back to a string
        updated_yaml = yaml.dump(yaml_data, sort_keys=False)

        # Reconstruct the file content
        updated_content = f"---\n{updated_yaml}---\n{parts[2]}"

        # Write the updated content back to the file
        with open(self.file_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)