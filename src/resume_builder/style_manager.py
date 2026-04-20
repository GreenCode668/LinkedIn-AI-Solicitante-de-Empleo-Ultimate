import os
from pathlib import Path
from typing import Dict, List, Tuple

from config.logger_config import logger


class StyleManager:
    """Class managing resume styles"""

    def __init__(self):
        self.styles_directory = None

    def set_styles_directory(self, styles_directory: Path):
        """Set folder where resume styles are stored"""
        self.styles_directory = styles_directory

    def get_styles(self) -> Dict[str, Tuple[str, str]]:
        """Get list of styles"""
        styles_to_files = {}
        try:
            files = os.listdir(self.styles_directory)
            for f in files:
                file_path = self.styles_directory / Path(f)
                if file_path.is_file():
                    with open(file_path, "r", encoding="utf-8") as file:
                        first_line = file.readline().strip()
                        if first_line.startswith("/*") and first_line.endswith("*/"):
                            content = first_line[2:-2].strip()
                            if "$" in content:
                                style_name, author_link = content.split("$", 1)
                                style_name = style_name.strip()
                                author_link = author_link.strip()
                                styles_to_files[style_name] = (f, author_link)
        except FileNotFoundError:
            logger.error(f"Folder {self.styles_directory} not found.")
        except PermissionError:
            logger.error(f"No permission to access folder {self.styles_directory}.")
        return styles_to_files

    def format_choices(self, styles_to_files: Dict[str, Tuple[str, str]]) -> List[str]:
        """Create list of resume styles for selection"""
        list_of_choices = [
            f"{style_name} (style author -> {author_link})"
            for style_name, (file_name, author_link) in styles_to_files.items()
        ]
        for i, choice in enumerate(list_of_choices):
            if choice.startswith("FAANGPath"):
                break
        if i > 0:
            list_of_choices = list_of_choices[:i] + list_of_choices[i + 1 :]
            list_of_choices = [choice] + list_of_choices
        return list_of_choices

    def get_style_path(self, selected_style: str) -> Path:
        """Get path to style"""
        styles = self.get_styles()
        file_name, _ = styles[selected_style]
        return self.styles_directory / file_name
