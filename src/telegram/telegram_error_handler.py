import asyncio
import logging
import os
import random
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict

import dotenv
import yaml

from config.constants import LOG_DIR, SEARCH_CONFIG_FILE
from telegram import Bot
from telegram.error import InvalidToken, TelegramError

# Configure standard logging for internal errors
logging.basicConfig(level=logging.WARNING)
internal_logger = logging.getLogger("AsyncTelegramSink")
os.makedirs(LOG_DIR, exist_ok=True)
log_file_path = os.path.join(Path(LOG_DIR), "internal_logger.log")  # Path to the log file
file_handler = logging.FileHandler(log_file_path, mode="a")  # Append mode
file_handler.setLevel(logging.WARNING)  # Set the logging level for the file handler
# Create a formatter for the log messages
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)
# Add the file handler to the internal_logger
internal_logger.addHandler(file_handler)


def load_yaml_file(yaml_path: Path) -> dict:
    """Load settings from YAML configuration file"""
    try:
        with open(yaml_path, "r", encoding="UTF-8") as stream:
            return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        internal_logger.error(f"Error in reading file {yaml_path}: {exc}")
        raise yaml.YAMLError(f"Error in reading file {yaml_path}: {exc}")


def save_yaml_file(yaml_path: Path, data: dict) -> None:
    """Load settings from YAML configuration file"""
    with open(yaml_path, "w", encoding="UTF-8") as stream:
        yaml.safe_dump(data, stream, allow_unicode=True, default_flow_style=False)


class AsyncTelegramSink:
    """
    Class for sending error messages through Telegram.
    If there is an error in the sending process, we wait and send again.
    """

    def __init__(
        self,
        max_retries: int = 6,
        cooldown: int = 60,
    ):
        telegram_bot_token = dotenv.dotenv_values(".env").get("tg_token")
        try:
            self.bot = Bot(token=telegram_bot_token)
        except InvalidToken:
            self.bot = None
        self.chat_id = dotenv.dotenv_values(".env").get("tg_chat_id")
        self.err_topic_id = dotenv.dotenv_values(".env").get("tg_err_topic_id")
        self.report_topic_id = dotenv.dotenv_values(".env").get("tg_report_topic_id")
        self.user_id = load_yaml_file(SEARCH_CONFIG_FILE).get("user_id", "-1")
        self.max_retries = max_retries
        self.cooldown = cooldown  # Seconds between identical error notifications
        self.error_cache_file = "src/telegram/error_cache.yaml"

    async def _send_with_retry(self, message: str) -> bool:
        """Try to send a message. In case of an error, we wait exponentially longer."""
        base_delay = 1
        # ограничиваем максимальную длину сообщения, чтобы избежать ошибки Telegram
        message_ = f"Error:\n```{message[:4050]}```"
        for attempt in range(self.max_retries):
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    message_thread_id=self.err_topic_id,
                    text=message_,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return True
            except TelegramError as e:
                if "Chat not found" in str(e):
                    internal_logger.error(
                        f"Telegram Chat not found. Please check TG_CHAT_ID in .env: {e}"
                    )
                    return False

                if attempt == self.max_retries - 1:
                    internal_logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    return False

                delay = base_delay * (2**attempt) + random.uniform(0, 1)
                internal_logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        return False

    def _is_duplicate_error(self, new_error: str) -> bool:
        """Check that similar errors are not sent"""
        try:
            with open(self.error_cache_file, "r") as f:
                cache: Dict[str, str] = yaml.safe_load(f) or {}

            if new_error in cache:
                last_sent = datetime.fromisoformat(cache[new_error])
                return (datetime.now() - last_sent).total_seconds() < self.cooldown

        except FileNotFoundError:
            internal_logger.info("Cache file not found")

        except yaml.YAMLError as e:
            internal_logger.warning(f"Error reading cache: {e}")

        return False

    def _update_error_cache(self, error: str) -> None:
        """Update error timestamp in cache"""
        cache = {}
        cache[error] = datetime.now().isoformat()
        try:
            save_yaml_file(self.error_cache_file, cache)
        except (IOError, yaml.YAMLError) as e:
            internal_logger.error(f"Failed to update error cache: {e}")

    async def _process_message(self, message: str) -> None:
        """Main message processing logic"""
        try:
            # Extract error content and check for duplicates
            error_content = message.strip()
            # if the message starts with "Unknown error on the page", remove the first line,
            # so that there are no changing elements in the message like URL
            if error_content.startswith("Unknown error on the page"):
                error_cache = error_content.split("\n")[1:]
                error_cache = "\n".join(error_cache)
            else:
                error_cache = error_content

            if self._is_duplicate_error(error_cache):
                internal_logger.info("Duplicate error suppressed")
                return

            # Attempt to send with retries
            success = await self._send_with_retry(error_content)

            if success:
                self._update_error_cache(error_cache)
            else:
                internal_logger.error("All retry attempts failed")

        except Exception:
            tb_str = traceback.format_exc()
            internal_logger.error(f"Critical error in message processing: {tb_str}")

    def __call__(self, message: str) -> None:
        """Loguru sink entry point"""
        if not self.bot:
            internal_logger.info(
                "Telegram bot token wasn't set, so the Telegram error messaging is disabled."
            )
            return
        try:
            # Check if there's already a running event loop
            try:
                asyncio.get_running_loop()
                # If we're in an async context, schedule the coroutine as a task
                asyncio.create_task(self._process_message(message))
            except RuntimeError:
                # No running loop, create one with asyncio.run
                asyncio.run(self._process_message(message))
        except Exception:
            tb_str = traceback.format_exc()
            internal_logger.error(f"Failed to schedule Telegram message: {tb_str}")
