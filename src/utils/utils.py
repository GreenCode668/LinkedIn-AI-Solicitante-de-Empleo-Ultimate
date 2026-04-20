import asyncio
import os
import random
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from config.constants import APP_CONFIG_FILE

# Import browser configuration
from config.logger_config import logger


class ConfigError(Exception):
    pass


chromeProfilePath = os.path.join(os.getcwd(), "chrome_profile", "linkedin_profile")


def load_yaml_file(yaml_path: Path) -> dict:
    """Load settings from YAML configuration file"""
    try:
        with open(yaml_path, "r", encoding="UTF-8") as stream:
            return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise yaml.YAMLError(f"Error in reading file {yaml_path}: {exc}")
    except FileNotFoundError:
        raise ConfigError(f"File not found: {yaml_path}")


def load_app_config() -> dict:
    """Загрузить конфигурацию приложения из YAML файла"""
    try:
        config = load_yaml_file(APP_CONFIG_FILE)
        return config or {}
    except Exception as e:
        # Fallback logging to stderr since we can't use logger here
        print(f"Ошибка при загрузке конфигурации приложения: {e}", file=sys.stderr)
        return {}


def save_yaml_file(yaml_path: Path, data: dict, sort_keys: bool = True) -> None:
    """Load settings from YAML configuration file"""
    with open(yaml_path, "w", encoding="UTF-8") as stream:
        yaml.safe_dump(
            data, stream, allow_unicode=True, default_flow_style=False, sort_keys=sort_keys
        )


def append_yaml_file(yaml_path: Path, data: dict) -> None:
    """Append data to YAML file"""
    # Append the log entry to the call log file
    try:
        if yaml_path.exists():
            # Read existing data
            with yaml_path.open("a", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
                f.write("\n")  # Add empty line after data
        else:
            # Create new file and write the first entry
            with yaml_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
                f.write("\n")  # Add empty line after data
        logger.info(f"Data appended to {yaml_path}")
    except yaml.YAMLError as exc:
        raise yaml.YAMLError(f"Error in reading file {yaml_path}: {exc}")


def pause(low: int = 0.5, high: int = 1) -> None:
    """
    Hold a random pause in the range from
    low seconds to high seconds.
    Used to simulate user behavior.
    """
    pause = round(random.uniform(low, high), 1)
    time.sleep(pause)


async def async_pause(low: float = 0.5, high: float = 1) -> None:
    """
    Hold a random pause without blocking the asyncio event loop.
    """
    pause_time = round(random.uniform(low, high), 1)
    await asyncio.sleep(pause_time)


def sleep(sleep_interval: Tuple[int, int]) -> None:
    """Analog of _pause, but waiting can be interrupted"""
    low, high = sleep_interval
    sleep_time = random.randint(low, high)
    time_to_wait = f"{sleep_time // 60} minutes, {sleep_time % 60} seconds"
    time.sleep(sleep_time)
    logger.info(f"Waiting lasted {time_to_wait}.")


def sanitize_text(text: str) -> str:
    """Clean the text of the question/answer"""
    sanitized_text = text.lower().strip().replace('"', "").replace("\\", "")
    sanitized_text = (
        re.sub(r"[\x00-\x1F\x7F]", "", sanitized_text)
        .replace("\n", " ")
        .replace("\r", "")
        .rstrip(",")
    )
    sanitized_text = re.sub(r"\s+", " ", sanitized_text)
    return sanitized_text


def get_first_pdf_file(resume_dir: Path) -> Path:
    """Get the first PDF file found in the resume directory, or default to resume.pdf"""
    pdf_files = list(resume_dir.glob("*.pdf"))
    if len(pdf_files) > 1:
        logger.warning(
            f"Multiple PDF files found in {resume_dir}. Selecting the first one: {pdf_files[0].name}"
        )
    return pdf_files[0] if pdf_files else resume_dir / "resume.pdf"


def validate_structured_resume_fields(structured_resume: Dict[str, Any]) -> List[str]:
    """
    Validate structured resume and return list of missing or placeholder fields.

    Args:
        structured_resume: Dictionary containing structured resume data

    Returns:
        List of missing field paths (e.g., ['personal_information.name', 'experience_details.0.position'])
    """
    missing_fields = []

    def check_field(value: Any, field_path: str) -> None:
        """Recursively check if field contains placeholder or is missing"""
        if isinstance(value, dict):
            for key, val in value.items():
                current_path = f"{field_path}.{key}" if field_path else key
                check_field(val, current_path)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                current_path = f"{field_path}.{i + 1}" if field_path else str(i + 1)
                check_field(item, current_path)
        elif isinstance(value, str):
            # Check for placeholder patterns
            if (value.startswith("[") and value.endswith("]")) or value in ["No info", ""]:
                missing_fields.append(field_path)
        elif value is None:
            missing_fields.append(field_path)

    check_field(structured_resume, "")
    return missing_fields


def format_missing_fields_display(missing_fields: List[str]) -> str:
    """
    Format missing fields for user-friendly display.

    Args:
        missing_fields: List of missing field paths

    Returns:
        Formatted string showing missing fields grouped by section
    """
    if not missing_fields:
        return "All fields are properly filled!"

    # Group fields by main section
    sections = {}
    for field in missing_fields:
        parts = field.split(".")
        if len(parts) >= 1:
            section = parts[0]
            if section not in sections:
                sections[section] = []
            sections[section].append(".".join(parts[1:]) if len(parts) > 1 else "")

    display_text = "Missing or placeholder fields found:\n\n"
    for section, fields in sections.items():
        display_text += f"📋 {section.replace('_', ' ').title()}:\n"
        for field in fields:
            if field:
                display_text += f"   • {field.replace('_', ' ').title()}\n"
        display_text += "\n"

    return display_text


def get_user_choice_with_timeout(timeout_seconds: int = 30) -> str:
    """
    Get user input with timeout. If no input within timeout, returns 'continue'.

    Args:
        timeout_seconds: Timeout in seconds

    Returns:
        User choice or 'continue' if timeout
    """
    result = {"choice": "continue"}

    def get_input():
        try:
            choice = input("Enter your choice (y/n): ").strip()
            result["choice"] = choice
        except (EOFError, KeyboardInterrupt):
            result["choice"] = "continue"

    input_thread = threading.Thread(target=get_input)
    input_thread.daemon = True
    input_thread.start()
    input_thread.join(timeout_seconds)

    return result["choice"]


def validate_and_prompt_resume_completion(
    structured_resume: Dict[str, Any], structured_resume_file: Path, resume_text_file: Path
) -> bool:
    """
    Validate structured resume fields and prompt user to complete missing information.

    Args:
        structured_resume: Dictionary containing structured resume data
        structured_resume_file: Path to structured resume YAML file
        resume_text_file: Path to resume text file

    Returns:
        True if user chooses to continue, False if user chooses to exit
    """
    logger.info("Validating structured resume fields...")

    missing_fields = validate_structured_resume_fields(structured_resume)

    if not missing_fields:
        logger.info("✅ All structured resume fields are properly filled!")
        return True

    logger.warning(f"Found {len(missing_fields)} missing or placeholder fields")

    # Display missing fields
    missing_display = format_missing_fields_display(missing_fields)
    print("\n" + "=" * 80)
    print("⚠️  STRUCTURED RESUME VALIDATION WARNING")
    print("=" * 80)
    print(missing_display)
    print("=" * 80)
    print("\nThe program may not be able to answer questions correctly with missing information.")
    print(
        f"\nWe recommend you to stop the program, fill missing information in {resume_text_file} and {structured_resume_file}, then restart."
    )
    print(
        f"""\nFilling missing fields in {structured_resume_file} is not necessary, you can delete this file, fill only text information in {resume_text_file} and restart the program - structured resumefile will be generated automatically from your text resume."""
    )
    print(
        f"\nIf you want to fill missing fields in {structured_resume_file} manually - use 'data/resume/structured_resume_template.yaml' as a reference for the structure of the resume."
    )
    print(
        "\nWould you like to continue anyway? If you make no choice in 30 seconds - the program will continue automatically."
    )
    print("\n" + "=" * 80)

    # Get user choice with timeout
    choice = get_user_choice_with_timeout(30)

    if choice == "y" or choice == "continue":
        print("\n⏰ Continuing program execution...")
        logger.info("User chose to continue or timeout reached")
        return True
    else:  # choice != 'y'
        print("\n📝 Please edit the following file to fill missing fields:")
        print(f"   {structured_resume_file}")
        print("\nThen run the program again.")
        logger.info("User chose to exit and edit structured resume file")
        return False


def debug_page_elements(page) -> None:
    """Debug function to log available elements on the page"""
    logger.debug("=== DEBUGGING PAGE ELEMENTS ===")
    try:
        # Log current URL
        try:
            logger.debug(f"Current URL: {page.url}")
        except Exception:
            pass

        # Look for any modal-related elements
        modal_elements = page.find_elements("css selector", "[class*='modal']")
        logger.debug(f"Found {len(modal_elements)} modal-related elements")
        for i, elem in enumerate(modal_elements[:5]):  # Log first 5
            try:
                class_name = elem.get_attribute("class")
                logger.debug(f"Modal element {i + 1}: class='{class_name}'")
            except Exception:
                pass

        # Look for any easy-apply related elements
        easy_apply_elements = page.find_elements("css selector", "[class*='easy-apply']")
        logger.debug(f"Found {len(easy_apply_elements)} easy-apply-related elements")
        for i, elem in enumerate(easy_apply_elements[:5]):  # Log first 5
            try:
                class_name = elem.get_attribute("class")
                logger.debug(f"Easy Apply element {i + 1}: class='{class_name}'")
            except Exception:
                pass

        # Look for any form-related elements
        form_elements = page.find_elements("css selector", "[class*='form']")
        logger.debug(f"Found {len(form_elements)} form-related elements")
        for i, elem in enumerate(form_elements[:5]):  # Log first 5
            try:
                class_name = elem.get_attribute("class")
                logger.debug(f"Form element {i + 1}: class='{class_name}'")
            except Exception:
                pass

    except Exception as e:
        logger.debug(f"Error during page debugging: {e}")
    logger.debug("=== END DEBUGGING ===")


def clean_structured_resume(structured_resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove items from structured resume that have placeholder values ('No info', None, '').

    Args:
        structured_resume: Dictionary containing structured resume data

    Returns:
        Cleaned structured resume with placeholder values removed
    """

    def clean_value(value: Any) -> Any:
        """Recursively clean values and remove placeholder entries"""
        if isinstance(value, dict):
            # Clean dictionary values and remove empty keys
            cleaned_dict = {}
            for key, val in value.items():
                cleaned_val = clean_value(val)
                if cleaned_val is not None:
                    cleaned_dict[key] = cleaned_val
            return cleaned_dict if cleaned_dict else None

        elif isinstance(value, list):
            # Clean list items and remove empty entries
            cleaned_list = []
            for item in value:
                cleaned_item = clean_value(item)
                if cleaned_item is not None:
                    cleaned_list.append(cleaned_item)
            return cleaned_list if cleaned_list else None

        elif isinstance(value, str):
            # Remove placeholder strings
            if value.strip() in ["No info", ""]:
                return None
            return value.strip() if value.strip() else None

        elif value is None:
            return None

        else:
            return value

    cleaned_resume = clean_value(structured_resume)
    return cleaned_resume if cleaned_resume is not None else {}
