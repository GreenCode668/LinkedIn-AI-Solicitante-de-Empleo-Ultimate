import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
import yaml

from src.telegram.telegram_error_handler import AsyncTelegramSink, load_yaml_file, save_yaml_file
from telegram.error import TelegramError


# Helper function tests
class TestYamlHelpers:
    """Tests for YAML helper functions"""

    def test_load_yaml_file_success(self, tmp_path):
        """Test successful YAML file loading"""
        test_file = tmp_path / "test.yaml"
        test_data = {"key": "value", "number": 42}
        with open(test_file, "w", encoding="UTF-8") as f:
            yaml.safe_dump(test_data, f)

        result = load_yaml_file(test_file)
        assert result == test_data

    def test_load_yaml_file_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error"""
        test_file = tmp_path / "invalid.yaml"
        test_file.write_text("invalid: yaml: content: [", encoding="UTF-8")

        with pytest.raises(yaml.YAMLError):
            load_yaml_file(test_file)

    def test_save_yaml_file_success(self, tmp_path):
        """Test successful YAML file saving"""
        test_file = tmp_path / "output.yaml"
        test_data = {"test": "data", "nested": {"key": "value"}}

        save_yaml_file(test_file, test_data)

        # Verify the file was created and contains correct data
        assert test_file.exists()
        with open(test_file, "r", encoding="UTF-8") as f:
            loaded_data = yaml.safe_load(f)
        assert loaded_data == test_data


# AsyncTelegramSink tests
class TestAsyncTelegramSink:
    """Tests for AsyncTelegramSink class"""

    @pytest.fixture
    def mock_env_and_config(self, monkeypatch, tmp_path):
        """Setup mocked environment and configuration"""
        # Mock environment variables
        monkeypatch.setenv("tg_token", "test_bot_token_123")

        # Mock dotenv.dotenv_values
        mock_dotenv = {
            "tg_token": "test_bot_token_123",
            "tg_chat_id": "test_chat_id",
            "tg_err_topic_id": 123,
            "tg_report_topic_id": 456,
        }
        monkeypatch.setattr("dotenv.dotenv_values", lambda x: mock_dotenv)

        # Mock SEARCH_CONFIG_FILE loading
        def mock_load_yaml(path):
            if "search_config" in str(path):
                return {"user_id": "test_user_123"}
            return {}

        monkeypatch.setattr("src.telegram.telegram_error_handler.load_yaml_file", mock_load_yaml)

        # Create a temporary error cache file
        error_cache_path = tmp_path / "error_cache.yaml"

        return {
            "error_cache_path": error_cache_path,
        }

    @pytest.fixture
    def telegram_sink(self, mock_env_and_config):
        """Create AsyncTelegramSink instance with mocked dependencies"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot:
            sink = AsyncTelegramSink(max_retries=3, cooldown=60)
            sink.bot = mock_bot.return_value
            # Set the error cache file to the temporary path
            sink.error_cache_file = str(mock_env_and_config["error_cache_path"])
            return sink

    def test_init(self, mock_env_and_config):
        """Test AsyncTelegramSink initialization"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot:
            sink = AsyncTelegramSink(max_retries=5, cooldown=120)

            assert sink.max_retries == 5
            assert sink.cooldown == 120
            assert sink.chat_id == "test_chat_id"
            assert sink.err_topic_id == 123
            assert sink.report_topic_id == 456
            assert sink.user_id == "test_user_123"
            mock_bot.assert_called_once_with(token="test_bot_token_123")

    @pytest.mark.asyncio
    async def test_send_with_retry_success(self, telegram_sink):
        """Test successful message sending on first attempt"""
        telegram_sink.bot.send_message = AsyncMock()
        message = "Test error message"

        result = await telegram_sink._send_with_retry(message)

        assert result is True
        telegram_sink.bot.send_message.assert_called_once()
        call_args = telegram_sink.bot.send_message.call_args
        assert call_args[1]["chat_id"] == "test_chat_id"
        assert call_args[1]["message_thread_id"] == 123
        assert "Test error message" in call_args[1]["text"]
        assert call_args[1]["parse_mode"] == "Markdown"
        assert call_args[1]["disable_web_page_preview"] is True

    @pytest.mark.asyncio
    async def test_send_with_retry_truncates_long_message(self, telegram_sink):
        """Test that very long messages are truncated"""
        telegram_sink.bot.send_message = AsyncMock()
        long_message = "A" * 5000  # Longer than 4050 char limit

        result = await telegram_sink._send_with_retry(long_message)

        assert result is True
        call_args = telegram_sink.bot.send_message.call_args
        sent_text = call_args[1]["text"]
        # Message should be truncated to 4050 chars (plus "Error:\n```" prefix and "```" suffix)
        # The actual format is: "Error:\n```{message[:4050]}```"
        assert len(sent_text) <= 4050 + 15  # Buffer for "Error:\n```" (9) + "```" (3) + some extra

    @pytest.mark.asyncio
    async def test_send_with_retry_with_retries(self, telegram_sink):
        """Test retry mechanism with exponential backoff"""
        # Fail twice, then succeed
        telegram_sink.bot.send_message = AsyncMock(
            side_effect=[TelegramError("Network error"), TelegramError("Network error"), None]
        )

        with patch("asyncio.sleep") as mock_sleep:
            result = await telegram_sink._send_with_retry("Test message")

        assert result is True
        assert telegram_sink.bot.send_message.call_count == 3
        assert mock_sleep.call_count == 2  # Two retries

    @pytest.mark.asyncio
    async def test_send_with_retry_max_retries_exceeded(self, telegram_sink):
        """Test failure after max retries exceeded"""
        telegram_sink.bot.send_message = AsyncMock(side_effect=TelegramError("Persistent error"))

        with patch("asyncio.sleep"):
            result = await telegram_sink._send_with_retry("Test message")

        assert result is False
        assert telegram_sink.bot.send_message.call_count == telegram_sink.max_retries

    def test_is_duplicate_error_no_cache_file(self, telegram_sink):
        """Test duplicate check when cache file doesn't exist"""
        result = telegram_sink._is_duplicate_error("New error message")
        assert result is False

    def test_is_duplicate_error_not_in_cache(self, telegram_sink, tmp_path):
        """Test duplicate check for error not in cache"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)

        # Create cache with different error
        cache_data = {"Different error": datetime.now().isoformat()}
        with open(cache_file, "w") as f:
            yaml.safe_dump(cache_data, f)

        result = telegram_sink._is_duplicate_error("New error message")
        assert result is False

    def test_is_duplicate_error_in_cache_within_cooldown(self, telegram_sink, tmp_path):
        """Test duplicate check for error within cooldown period"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)

        # Create cache with recent error (30 seconds ago, cooldown is 60)
        recent_time = datetime.now() - timedelta(seconds=30)
        cache_data = {"Test error": recent_time.isoformat()}
        with open(cache_file, "w") as f:
            yaml.safe_dump(cache_data, f)

        result = telegram_sink._is_duplicate_error("Test error")
        assert result is True

    def test_is_duplicate_error_in_cache_outside_cooldown(self, telegram_sink, tmp_path):
        """Test duplicate check for error outside cooldown period"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)

        # Create cache with old error (120 seconds ago, cooldown is 60)
        old_time = datetime.now() - timedelta(seconds=120)
        cache_data = {"Test error": old_time.isoformat()}
        with open(cache_file, "w") as f:
            yaml.safe_dump(cache_data, f)

        result = telegram_sink._is_duplicate_error("Test error")
        assert result is False

    def test_is_duplicate_error_invalid_cache(self, telegram_sink, tmp_path):
        """Test duplicate check with corrupted cache file"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)

        # Create invalid YAML
        cache_file.write_text("invalid: yaml: [[[")

        result = telegram_sink._is_duplicate_error("Test error")
        assert result is False  # Should handle error gracefully

    def test_update_error_cache(self, telegram_sink, tmp_path):
        """Test updating error cache"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)

        error_msg = "Test error message"
        telegram_sink._update_error_cache(error_msg)

        # Verify cache was updated
        assert cache_file.exists()
        with open(cache_file, "r") as f:
            cache_data = yaml.safe_load(f)

        assert error_msg in cache_data
        # Verify timestamp is recent (within last 5 seconds)
        error_time = datetime.fromisoformat(cache_data[error_msg])
        time_diff = (datetime.now() - error_time).total_seconds()
        assert time_diff < 5

    def test_update_error_cache_io_error(self, telegram_sink, tmp_path):
        """Test error cache update handles IO errors gracefully"""
        # Point to a directory instead of a file to cause IO error
        telegram_sink.error_cache_file = str(tmp_path)

        # Should not raise exception
        try:
            telegram_sink._update_error_cache("Test error")
        except Exception as e:
            pytest.fail(f"Should handle IO error gracefully, but raised {e}")

    @pytest.mark.asyncio
    async def test_process_message_success(self, telegram_sink, tmp_path):
        """Test successful message processing"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)
        telegram_sink.bot.send_message = AsyncMock()

        message = "Test error occurred"
        await telegram_sink._process_message(message)

        # Verify message was sent
        telegram_sink.bot.send_message.assert_called_once()

        # Verify cache was updated
        assert cache_file.exists()
        with open(cache_file, "r") as f:
            cache_data = yaml.safe_load(f)
        assert message in cache_data

    @pytest.mark.asyncio
    async def test_process_message_duplicate_suppressed(self, telegram_sink, tmp_path):
        """Test duplicate error is suppressed"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)
        telegram_sink.bot.send_message = AsyncMock()

        # Create recent cache entry
        message = "Duplicate error"
        cache_data = {message: datetime.now().isoformat()}
        with open(cache_file, "w") as f:
            yaml.safe_dump(cache_data, f)

        await telegram_sink._process_message(message)

        # Verify message was NOT sent
        telegram_sink.bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_unknown_error_caching(self, telegram_sink, tmp_path):
        """Test that 'Unknown error on the page' messages are cached without URL"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)
        telegram_sink.bot.send_message = AsyncMock()

        message = "Unknown error on the page: https://example.com/job123\nStack trace here"
        await telegram_sink._process_message(message)

        # Verify message was sent with full content
        telegram_sink.bot.send_message.assert_called_once()

        # Verify cache only stores the error without the first line (URL)
        with open(cache_file, "r") as f:
            cache_data = yaml.safe_load(f)
        cached_key = list(cache_data.keys())[0]
        assert "Stack trace here" in cached_key
        assert "Unknown error on the page" not in cached_key
        assert "https://example.com/job123" not in cached_key

    @pytest.mark.asyncio
    async def test_process_message_send_failure(self, telegram_sink, tmp_path):
        """Test message processing when send fails"""
        cache_file = tmp_path / "error_cache.yaml"
        telegram_sink.error_cache_file = str(cache_file)
        telegram_sink.bot.send_message = AsyncMock(side_effect=TelegramError("Send failed"))

        message = "Test error"

        with patch("asyncio.sleep"):
            await telegram_sink._process_message(message)

        # Verify cache was NOT updated after failure
        # (cache file might exist from setup but shouldn't have our message)
        if cache_file.exists():
            with open(cache_file, "r") as f:
                cache_data = yaml.safe_load(f) or {}
            assert message not in cache_data

    @pytest.mark.asyncio
    async def test_process_message_handles_exceptions(self, telegram_sink):
        """Test that process_message handles unexpected exceptions"""
        telegram_sink.bot.send_message = AsyncMock(side_effect=Exception("Unexpected error"))

        # Should not raise exception
        try:
            await telegram_sink._process_message("Test message")
        except Exception as e:
            pytest.fail(f"Should handle exceptions gracefully, but raised {e}")

    def test_call_with_running_loop(self, telegram_sink):
        """Test __call__ when event loop is already running"""
        message = "Test error in running loop"

        async def mock_running_loop():
            # This simulates being in an async context
            with patch.object(telegram_sink, "_process_message", return_value=None) as mock_process:
                with patch("asyncio.create_task") as mock_create_task:
                    telegram_sink(message)
                    mock_create_task.assert_called_once()

        asyncio.run(mock_running_loop())

    def test_call_without_running_loop(self, telegram_sink):
        """Test __call__ when no event loop is running"""
        message = "Test error without loop"

        with patch("asyncio.run") as mock_run:
            with patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")):
                telegram_sink(message)
                mock_run.assert_called_once()

    def test_call_handles_exceptions(self, telegram_sink):
        """Test __call__ handles exceptions gracefully"""
        message = "Test error"

        with patch("asyncio.get_running_loop", side_effect=Exception("Unexpected error")):
            # Should not raise exception
            try:
                telegram_sink(message)
            except Exception as e:
                pytest.fail(f"Should handle exceptions gracefully, but raised {e}")


class TestAsyncTelegramSinkIntegration:
    """Integration tests for AsyncTelegramSink"""

    @pytest.mark.asyncio
    async def test_full_workflow_new_error(self, tmp_path, monkeypatch):
        """Test full workflow: new error -> send -> cache"""
        # Setup
        monkeypatch.setenv("tg_token", "test_bot_token")
        mock_dotenv = {
            "tg_token": "test_bot_token",
            "tg_chat_id": "chat_123",
            "tg_err_topic_id": 100,
            "tg_report_topic_id": 200,
        }
        monkeypatch.setattr("dotenv.dotenv_values", lambda x: mock_dotenv)

        def mock_load_yaml(path):
            return {"user_id": "user_123"}

        monkeypatch.setattr("src.telegram.telegram_error_handler.load_yaml_file", mock_load_yaml)

        cache_file = tmp_path / "error_cache.yaml"

        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot:
            sink = AsyncTelegramSink(max_retries=3, cooldown=60)
            sink.error_cache_file = str(cache_file)
            sink.bot.send_message = AsyncMock()

            # Process new error
            error_message = "Critical error occurred"
            await sink._process_message(error_message)

            # Verify message was sent
            assert sink.bot.send_message.call_count == 1

            # Verify cache was created and contains error
            assert cache_file.exists()
            with open(cache_file, "r") as f:
                cache_data = yaml.safe_load(f)
            assert error_message in cache_data

    @pytest.mark.asyncio
    async def test_full_workflow_duplicate_error(self, tmp_path, monkeypatch):
        """Test full workflow: duplicate error -> suppress"""
        # Setup
        monkeypatch.setenv("tg_token", "test_bot_token")
        mock_dotenv = {
            "tg_token": "test_bot_token",
            "tg_chat_id": "chat_123",
            "tg_err_topic_id": 100,
            "tg_report_topic_id": 200,
        }
        monkeypatch.setattr("dotenv.dotenv_values", lambda x: mock_dotenv)

        def mock_load_yaml(path):
            return {"user_id": "user_123"}

        monkeypatch.setattr("src.telegram.telegram_error_handler.load_yaml_file", mock_load_yaml)

        cache_file = tmp_path / "error_cache.yaml"

        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot:
            sink = AsyncTelegramSink(max_retries=3, cooldown=60)
            sink.error_cache_file = str(cache_file)
            sink.bot.send_message = AsyncMock()

            # Process error first time
            error_message = "Repeated error"
            await sink._process_message(error_message)
            assert sink.bot.send_message.call_count == 1

            # Process same error again (within cooldown)
            sink.bot.send_message.reset_mock()
            await sink._process_message(error_message)

            # Verify message was NOT sent second time
            assert sink.bot.send_message.call_count == 0


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_empty_message(self, monkeypatch, tmp_path):
        """Test handling of empty message"""
        monkeypatch.setenv("tg_token", "test_token")
        monkeypatch.setattr(
            "dotenv.dotenv_values",
            lambda x: {
                "tg_token": "test_token",
                "tg_chat_id": "chat",
                "tg_err_topic_id": 1,
                "tg_report_topic_id": 2,
            },
        )
        monkeypatch.setattr(
            "src.telegram.telegram_error_handler.load_yaml_file", lambda x: {"user_id": "user"}
        )

        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()
            sink.bot.send_message = AsyncMock()
            # Set error cache to temp file
            cache_file = tmp_path / "error_cache.yaml"
            sink.error_cache_file = str(cache_file)

            await sink._process_message("")

            # Should still attempt to send even with empty message
            sink.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_very_long_message_truncation(self, monkeypatch):
        """Test that extremely long messages are truncated properly"""
        monkeypatch.setenv("tg_token", "test_token")
        monkeypatch.setattr(
            "dotenv.dotenv_values",
            lambda x: {
                "tg_token": "test_token",
                "tg_chat_id": "chat",
                "tg_err_topic_id": 1,
                "tg_report_topic_id": 2,
            },
        )
        monkeypatch.setattr(
            "src.telegram.telegram_error_handler.load_yaml_file", lambda x: {"user_id": "user"}
        )

        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()
            sink.bot.send_message = AsyncMock()

            # Create message longer than 4050 characters
            long_error = "X" * 10000
            result = await sink._send_with_retry(long_error)

            assert result is True
            call_args = sink.bot.send_message.call_args
            sent_message = call_args[1]["text"]
            # Message should be truncated and wrapped in markdown code block
            assert len(sent_message) <= 4096  # Telegram's limit
            assert "```" in sent_message

    def test_custom_cooldown_and_retries(self, monkeypatch):
        """Test custom cooldown and retry values"""
        monkeypatch.setenv("tg_token", "test_token")
        monkeypatch.setattr(
            "dotenv.dotenv_values",
            lambda x: {
                "tg_token": "test_token",
                "tg_chat_id": "chat",
                "tg_err_topic_id": 1,
                "tg_report_topic_id": 2,
            },
        )
        monkeypatch.setattr(
            "src.telegram.telegram_error_handler.load_yaml_file", lambda x: {"user_id": "user"}
        )

        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink(max_retries=10, cooldown=300)

            assert sink.max_retries == 10
            assert sink.cooldown == 300
