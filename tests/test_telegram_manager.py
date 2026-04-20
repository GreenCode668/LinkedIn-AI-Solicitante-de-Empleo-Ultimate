"""Test suite for src/telegram/ module"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
import yaml

from src.telegram.telegram_error_handler import AsyncTelegramSink
from src.telegram.telegram_manager import (
    TelegramReportSender,
    process_captcha,
    receive_messages,
    send_captcha,
)


class TestSendCaptcha:
    """Tests for send_captcha function"""

    @pytest.mark.asyncio
    async def test_send_captcha_success(self):
        """Test send_captcha successfully sends a photo"""
        bot_token = "test_token"
        chat_id = "123456"
        topic_id = "789"
        img_path = "/path/to/image.png"
        message = "Please solve this captcha"

        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_open_file = mock_open(read_data=b"fake_image_data")

            with patch("builtins.open", mock_open_file):
                await send_captcha(bot_token, chat_id, topic_id, img_path, message)

                # Verify Bot was initialized with correct token
                mock_bot_class.assert_called_once_with(token=bot_token)

                # Verify send_photo was called with correct parameters
                mock_bot.send_photo.assert_called_once()
                call_args = mock_bot.send_photo.call_args
                assert call_args.kwargs["chat_id"] == chat_id
                assert call_args.kwargs["message_thread_id"] == topic_id
                assert call_args.kwargs["caption"] == message

    @pytest.mark.asyncio
    async def test_send_captcha_file_not_found(self):
        """Test send_captcha when image file doesn't exist"""
        bot_token = "test_token"
        chat_id = "123456"
        topic_id = "789"
        img_path = "/nonexistent/image.png"
        message = "Please solve this captcha"

        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
                with pytest.raises(FileNotFoundError):
                    await send_captcha(bot_token, chat_id, topic_id, img_path, message)


class TestReceiveMessages:
    """Tests for receive_messages function"""

    @pytest.mark.asyncio
    async def test_receive_messages_finds_matching_reply(self):
        """Test receive_messages finds a matching reply to the message"""
        api_id = "12345"
        api_hash = "test_hash"
        chat_id = "123456"
        topic_id = "789"
        message = "Original message"

        # Create mock messages
        mock_reply_message = MagicMock()
        mock_reply_message.text = message
        mock_reply_message.message_id = 100

        mock_user_message = MagicMock()
        mock_user_message.reply_to_msg_id = 100
        mock_user_message.text = "User's answer"

        with patch("src.telegram.telegram_manager.TelegramClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get_messages = AsyncMock(
                side_effect=[
                    [mock_user_message],  # First call returns user messages
                    mock_reply_message,  # Second call returns the original message
                ]
            )
            mock_client_class.return_value = mock_client

            result = await receive_messages(api_id, api_hash, chat_id, topic_id, message)

            assert result == "User's answer"
            assert mock_client.get_messages.call_count == 2

    @pytest.mark.asyncio
    async def test_receive_messages_no_matching_reply(self):
        """Test receive_messages when no matching reply is found"""
        api_id = "12345"
        api_hash = "test_hash"
        chat_id = "123456"
        topic_id = "789"
        message = "Original message"

        # Create mock messages
        mock_user_message = MagicMock()
        mock_user_message.reply_to_msg_id = None

        with patch("src.telegram.telegram_manager.TelegramClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get_messages = AsyncMock(return_value=[mock_user_message])
            mock_client_class.return_value = mock_client

            result = await receive_messages(api_id, api_hash, chat_id, topic_id, message)

            assert result is None

    @pytest.mark.asyncio
    async def test_receive_messages_no_messages(self):
        """Test receive_messages when no messages are found"""
        api_id = "12345"
        api_hash = "test_hash"
        chat_id = "123456"
        topic_id = "789"
        message = "Original message"

        with patch("src.telegram.telegram_manager.TelegramClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get_messages = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client

            result = await receive_messages(api_id, api_hash, chat_id, topic_id, message)

            assert result is None


class TestProcessCaptcha:
    """Tests for process_captcha function"""

    @pytest.mark.asyncio
    async def test_process_captcha_send_mode(self):
        """Test process_captcha in send mode"""
        tg_token = "test_token"
        tg_api_id = "12345"
        tg_api_hash = "test_hash"
        chat_id = "123456"
        topic_id = "789"
        img_path = "/path/to/image.png"
        message = "Solve captcha"

        with patch(
            "src.telegram.telegram_manager.send_captcha", new_callable=AsyncMock
        ) as mock_send:
            result = await process_captcha(
                tg_token, tg_api_id, tg_api_hash, chat_id, topic_id, img_path, message, listen=False
            )

            mock_send.assert_called_once_with(tg_token, chat_id, topic_id, img_path, message)
            assert result is None

    @pytest.mark.asyncio
    async def test_process_captcha_listen_mode(self):
        """Test process_captcha in listen mode"""
        tg_token = "test_token"
        tg_api_id = "12345"
        tg_api_hash = "test_hash"
        chat_id = "123456"
        topic_id = "789"
        img_path = "/path/to/image.png"
        message = "Solve captcha"

        with patch(
            "src.telegram.telegram_manager.receive_messages", new_callable=AsyncMock
        ) as mock_receive:
            mock_receive.return_value = "captcha_solution"

            result = await process_captcha(
                tg_token, tg_api_id, tg_api_hash, chat_id, topic_id, img_path, message, listen=True
            )

            mock_receive.assert_called_once_with(tg_api_id, tg_api_hash, chat_id, topic_id, message)
            assert result == "captcha_solution"


class TestTelegramReportSender:
    """Tests for TelegramReportSender class"""

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables"""
        with patch("src.telegram.telegram_manager.dotenv.dotenv_values") as mock_dotenv:
            mock_dotenv.return_value = {
                "tg_token": "test_token",
                "tg_chat_id": "123456",
                "tg_report_topic_id": "789",
            }
            yield mock_dotenv

    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        # No longer need to patch module constants as they are loaded from env
        yield

    def test_init(self, mock_env, mock_config):
        """Test TelegramReportSender initialization"""
        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            sender = TelegramReportSender()

            assert sender.chat_id == "123456"
            assert sender.report_topic_id == "789"
            assert sender.message == ""
            mock_bot_class.assert_called_once_with(token="test_token")

    @pytest.mark.asyncio
    async def test_send_telegram_report_basic(self, mock_env, mock_config):
        """Test send_telegram_report with basic information"""
        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sender = TelegramReportSender()

            # Mock resume component
            mock_resume_component = MagicMock()
            mock_resume_component.deanonymize_text = MagicMock(side_effect=lambda x: x)

            resume = {
                "personal_information": {
                    "email": "test@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                }
            }

            await sender.send_telegram_report(
                login="test@example.com",
                resume=resume,
                success_applies_num="5",
                jobs_no_info="",
                skill_stat="",
                resume_recommendations="",
                resume_component=mock_resume_component,
            )

            # Verify message was constructed
            assert "Client email: test@example.com" in sender.message
            assert "Client name: John Doe" in sender.message
            assert (
                "Total number of vacancies to which the application responded: 5" in sender.message
            )

            # Verify bot.send_message was called
            mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_telegram_report_with_failed_jobs(self, mock_env, mock_config):
        """Test send_telegram_report with failed jobs information"""
        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sender = TelegramReportSender()

            mock_resume_component = MagicMock()
            mock_resume_component.deanonymize_text = MagicMock(side_effect=lambda x: x)

            resume = {
                "personal_information": {
                    "email": "test@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                }
            }

            jobs_no_info = [
                {
                    "job_title": "Software Engineer",
                    "link": "https://example.com/job1",
                    "reason": "Form too complex",
                },
                {
                    "job_title": "Data Scientist",
                    "link": "https://example.com/job2",
                    "reason": "Rate limited",
                },
            ]

            await sender.send_telegram_report(
                login="test@example.com",
                resume=resume,
                success_applies_num="3",
                jobs_no_info=jobs_no_info,
                skill_stat="",
                resume_recommendations="",
                resume_component=mock_resume_component,
            )

            # Verify failed jobs are in message
            assert "Software Engineer" in sender.message
            assert "https://example.com/job1" in sender.message
            assert "Form too complex" in sender.message
            assert "Data Scientist" in sender.message

    @pytest.mark.asyncio
    async def test_send_telegram_report_with_skill_stats(self, mock_env, mock_config):
        """Test send_telegram_report with skill statistics"""
        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sender = TelegramReportSender()

            mock_resume_component = MagicMock()
            mock_resume_component.deanonymize_text = MagicMock(side_effect=lambda x: x)

            resume = {
                "personal_information": {
                    "email": "test@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                }
            }

            skill_stat = {"Python": 15, "JavaScript": 10, "Docker": 8, "AWS": 12}

            await sender.send_telegram_report(
                login="test@example.com",
                resume=resume,
                success_applies_num="3",
                jobs_no_info="",
                skill_stat=skill_stat,
                resume_recommendations="",
                resume_component=mock_resume_component,
            )

            # Verify skills are sorted by count and in message
            assert "Python: 15" in sender.message
            assert "AWS: 12" in sender.message
            assert "JavaScript: 10" in sender.message

    @pytest.mark.asyncio
    async def test_send_telegram_report_with_recommendations(self, mock_env, mock_config):
        """Test send_telegram_report with resume recommendations"""
        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sender = TelegramReportSender()

            mock_resume_component = MagicMock()
            mock_resume_component.deanonymize_text = MagicMock(side_effect=lambda x: x)

            resume = {
                "personal_information": {
                    "email": "test@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                }
            }

            recommendations = "Add more project details. Highlight leadership experience."

            await sender.send_telegram_report(
                login="test@example.com",
                resume=resume,
                success_applies_num="3",
                jobs_no_info="",
                skill_stat="",
                resume_recommendations=recommendations,
                resume_component=mock_resume_component,
            )

            # Verify recommendations are in message
            assert "recommendations for improving your resume" in sender.message
            assert recommendations in sender.message

    @pytest.mark.asyncio
    async def test_send_chunked_messages_single_chunk(self, mock_env, mock_config):
        """Test _send_chunked_messages with a message under 4096 characters"""
        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sender = TelegramReportSender()
            header = "Report Header\n"
            message = header + "This is a short message"

            await sender._send_chunked_messages(message, header)

            # Should send only one message
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert call_args.kwargs["chat_id"] == "123456"
            assert call_args.kwargs["message_thread_id"] == "789"
            assert call_args.kwargs["text"] == message

    @pytest.mark.asyncio
    async def test_send_chunked_messages_multiple_chunks(self, mock_env, mock_config):
        """Test _send_chunked_messages with a message over 4096 characters"""
        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sender = TelegramReportSender()
            header = "Header\n"
            # Create a message longer than 4096 characters
            long_message = header + "A" * 5000

            await sender._send_chunked_messages(long_message, header)

            # Should send multiple messages
            assert mock_bot.send_message.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_chunked_messages_telegram_error(self, mock_env, mock_config):
        """Test _send_chunked_messages handles TelegramError gracefully"""
        with patch("src.telegram.telegram_manager.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            from telegram.error import TelegramError

            mock_bot.send_message.side_effect = TelegramError("API error")
            mock_bot_class.return_value = mock_bot

            sender = TelegramReportSender()
            message = "Test message"
            header = "Header\n"

            with patch("src.telegram.telegram_manager.logger") as mock_logger:
                # Should not raise exception
                await sender._send_chunked_messages(message, header)

                # Should log error
                mock_logger.error.assert_called()

    def test_format_jobs_no_info(self, mock_env, mock_config):
        """Test _format_jobs_no_info formats job information correctly"""
        with patch("src.telegram.telegram_manager.Bot"):
            sender = TelegramReportSender()

            jobs_no_info = [
                {
                    "job_title": "Backend Developer",
                    "link": "https://example.com/job1",
                    "reason": "Missing required fields",
                },
                {
                    "job_title": "Frontend Developer",
                    "link": "https://example.com/job2",
                    "reason": "Rate limited",
                },
            ]

            result = sender._format_jobs_no_info(jobs_no_info)

            assert "**Vacancy name:** Backend Developer" in result
            assert "**Vacancy link:** https://example.com/job1" in result
            assert "**Reason:** Missing required fields" in result
            assert "**Vacancy name:** Frontend Developer" in result

    def test_format_jobs_no_info_empty_list(self, mock_env, mock_config):
        """Test _format_jobs_no_info with empty list"""
        with patch("src.telegram.telegram_manager.Bot"):
            sender = TelegramReportSender()
            result = sender._format_jobs_no_info([])
            assert result == ""


class TestAsyncTelegramSink:
    """Tests for AsyncTelegramSink class"""

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables"""
        with patch("src.telegram.telegram_error_handler.dotenv.dotenv_values") as mock_dotenv:
            mock_dotenv.return_value = {
                "tg_token": "test_token",
                "tg_chat_id": "123456",
                "tg_err_topic_id": "789",
                "tg_report_topic_id": "456",
            }
            yield mock_dotenv

    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        with (
            patch(
                "src.telegram.telegram_error_handler.SEARCH_CONFIG_FILE",
                "config/search_config.yaml",
            ),
            patch("src.telegram.telegram_error_handler.load_yaml_file") as mock_load,
        ):
            mock_load.return_value = {"user_id": "user123"}
            yield

    def test_init(self, mock_env, mock_config):
        """Test AsyncTelegramSink initialization"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            sink = AsyncTelegramSink(max_retries=5, cooldown=120)

            assert sink.chat_id == "123456"
            assert sink.err_topic_id == "789"
            assert sink.report_topic_id == "456"
            assert sink.user_id == "user123"
            assert sink.max_retries == 5
            assert sink.cooldown == 120
            assert sink.error_cache_file == "src/telegram/error_cache.yaml"
            mock_bot_class.assert_called_once_with(token="test_token")

    def test_init_default_values(self, mock_env, mock_config):
        """Test AsyncTelegramSink initialization with default values"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()

            assert sink.max_retries == 6
            assert sink.cooldown == 60

    @pytest.mark.asyncio
    async def test_send_with_retry_success(self, mock_env, mock_config):
        """Test _send_with_retry sends message successfully on first attempt"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sink = AsyncTelegramSink()
            message = "Test error message"

            result = await sink._send_with_retry(message)

            assert result is True
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert call_args.kwargs["chat_id"] == "123456"
            assert call_args.kwargs["message_thread_id"] == "789"
            assert "Test error message" in call_args.kwargs["text"]
            assert call_args.kwargs["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_send_with_retry_long_message(self, mock_env, mock_config):
        """Test _send_with_retry truncates very long messages"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sink = AsyncTelegramSink()
            long_message = "A" * 5000

            result = await sink._send_with_retry(long_message)

            assert result is True
            call_args = mock_bot.send_message.call_args
            # Should be truncated to 4050 + "Error:\n```" + "```"
            sent_text = call_args.kwargs["text"]
            assert len(sent_text) < 5000
            assert sent_text.startswith("Error:\n```")
            assert sent_text.endswith("```")

    @pytest.mark.asyncio
    async def test_send_with_retry_failure_then_success(self, mock_env, mock_config):
        """Test _send_with_retry retries on failure then succeeds"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            from telegram.error import TelegramError

            # Fail once, then succeed
            mock_bot.send_message.side_effect = [TelegramError("Network error"), None]
            mock_bot_class.return_value = mock_bot

            sink = AsyncTelegramSink()
            message = "Test error message"

            result = await sink._send_with_retry(message)

            assert result is True
            assert mock_bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_with_retry_max_retries_exceeded(self, mock_env, mock_config):
        """Test _send_with_retry fails after max retries"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            from telegram.error import TelegramError

            mock_bot.send_message.side_effect = TelegramError("Persistent error")
            mock_bot_class.return_value = mock_bot

            sink = AsyncTelegramSink(max_retries=3)
            message = "Test error message"

            with patch("src.telegram.telegram_error_handler.internal_logger") as mock_logger:
                result = await sink._send_with_retry(message)

                assert result is False
                assert mock_bot.send_message.call_count == 3
                mock_logger.error.assert_called()

    def test_is_duplicate_error_no_cache_file(self, mock_env, mock_config):
        """Test _is_duplicate_error when cache file doesn't exist"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()

            with patch("builtins.open", side_effect=FileNotFoundError):
                result = sink._is_duplicate_error("Test error")
                assert result is False

    def test_is_duplicate_error_new_error(self, mock_env, mock_config):
        """Test _is_duplicate_error with a new error"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()

            cache_data = {"Old error": "2025-10-13T10:00:00"}
            mock_file = mock_open(read_data=yaml.dump(cache_data))

            with patch("builtins.open", mock_file):
                result = sink._is_duplicate_error("New error")
                assert result is False

    def test_is_duplicate_error_recent_duplicate(self, mock_env, mock_config):
        """Test _is_duplicate_error with a recent duplicate error"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink(cooldown=60)

            # Create recent timestamp (within cooldown period)
            recent_time = datetime.now().isoformat()
            cache_data = {"Test error": recent_time}
            mock_file = mock_open(read_data=yaml.dump(cache_data))

            with patch("builtins.open", mock_file):
                result = sink._is_duplicate_error("Test error")
                assert result is True

    def test_is_duplicate_error_old_duplicate(self, mock_env, mock_config):
        """Test _is_duplicate_error with an old duplicate error (outside cooldown)"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink(cooldown=60)

            # Create old timestamp (2 hours ago)
            old_time = datetime(2025, 10, 13, 8, 0, 0).isoformat()
            cache_data = {"Test error": old_time}
            mock_file = mock_open(read_data=yaml.dump(cache_data))

            with patch("builtins.open", mock_file):
                result = sink._is_duplicate_error("Test error")
                assert result is False

    def test_update_error_cache_success(self, mock_env, mock_config):
        """Test _update_error_cache successfully updates cache"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()

            with patch("src.telegram.telegram_error_handler.save_yaml_file") as mock_save:
                sink._update_error_cache("New error")

                mock_save.assert_called_once()
                call_args = mock_save.call_args
                assert call_args[0][0] == "src/telegram/error_cache.yaml"
                cache_data = call_args[0][1]
                assert "New error" in cache_data
                # Verify timestamp is recent
                timestamp = datetime.fromisoformat(cache_data["New error"])
                assert (datetime.now() - timestamp).total_seconds() < 5

    def test_update_error_cache_io_error(self, mock_env, mock_config):
        """Test _update_error_cache handles IO errors gracefully"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()

            with patch(
                "src.telegram.telegram_error_handler.save_yaml_file",
                side_effect=IOError("Write failed"),
            ):
                with patch("src.telegram.telegram_error_handler.internal_logger") as mock_logger:
                    # Should not raise exception
                    sink._update_error_cache("New error")
                    mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_process_message_success(self, mock_env, mock_config):
        """Test _process_message processes and sends message successfully"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sink = AsyncTelegramSink()

            with (
                patch("builtins.open", side_effect=FileNotFoundError),
                patch("src.telegram.telegram_error_handler.save_yaml_file") as mock_save,
            ):
                await sink._process_message("Test error message")

                # Should send message and update cache
                mock_bot.send_message.assert_called_once()
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_duplicate_suppressed(self, mock_env, mock_config):
        """Test _process_message suppresses duplicate errors"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sink = AsyncTelegramSink(cooldown=60)

            recent_time = datetime.now().isoformat()
            cache_data = {"Test error": recent_time}
            mock_file = mock_open(read_data=yaml.dump(cache_data))

            with (
                patch("builtins.open", mock_file),
                patch("src.telegram.telegram_error_handler.internal_logger") as mock_logger,
            ):
                await sink._process_message("Test error")

                # Should not send message
                mock_bot.send_message.assert_not_called()
                # Should log that duplicate was suppressed
                mock_logger.info.assert_called_with("Duplicate error suppressed")

    @pytest.mark.asyncio
    async def test_process_message_unknown_error_on_page(self, mock_env, mock_config):
        """Test _process_message handles 'Unknown error on the page' specially"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sink = AsyncTelegramSink()

            message = "Unknown error on the page: https://example.com/job\nActual error message"

            with (
                patch("builtins.open", side_effect=FileNotFoundError),
                patch("src.telegram.telegram_error_handler.save_yaml_file"),
            ):
                await sink._process_message(message)

                # Should send full message but cache without first line
                mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_exception_handling(self, mock_env, mock_config):
        """Test _process_message handles exceptions gracefully"""
        with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_message.side_effect = Exception("Unexpected error")
            mock_bot_class.return_value = mock_bot

            sink = AsyncTelegramSink()

            with (
                patch("builtins.open", side_effect=FileNotFoundError),
                patch("src.telegram.telegram_error_handler.internal_logger") as mock_logger,
            ):
                # Should not raise exception
                await sink._process_message("Test error")
                # Should log the critical error
                mock_logger.error.assert_called()

    def test_call_no_running_loop(self, mock_env, mock_config):
        """Test __call__ when no event loop is running"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()

            with (
                patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")),
                patch("asyncio.run") as mock_run,
            ):
                sink("Test error")

                # Should use asyncio.run
                mock_run.assert_called_once()

    def test_call_with_running_loop(self, mock_env, mock_config):
        """Test __call__ when event loop is already running"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()

            mock_loop = MagicMock()
            with (
                patch("asyncio.get_running_loop", return_value=mock_loop),
                patch("asyncio.create_task") as mock_create_task,
            ):
                sink("Test error")

                # Should use create_task
                mock_create_task.assert_called_once()

    def test_call_exception_handling(self, mock_env, mock_config):
        """Test __call__ handles exceptions gracefully"""
        with patch("src.telegram.telegram_error_handler.Bot"):
            sink = AsyncTelegramSink()

            with (
                patch("asyncio.get_running_loop", side_effect=Exception("Fatal error")),
                patch("src.telegram.telegram_error_handler.internal_logger") as mock_logger,
            ):
                # Should not raise exception
                sink("Test error")
                # Should log the failure
                mock_logger.error.assert_called()


class TestGetTelegramChatAndTopicId:
    """Tests for get_telegram_chat_and_topic_id.py module"""

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables"""
        with patch(
            "src.telegram.get_telegram_chat_and_topic_id.dotenv.dotenv_values"
        ) as mock_dotenv:
            mock_dotenv.return_value = {"tg_token": "test_token"}
            yield mock_dotenv

    @pytest.mark.asyncio
    async def test_get_chat_id_success(self, mock_env):
        """Test get_chat_id sends correct response"""
        from src.telegram.get_telegram_chat_and_topic_id import get_chat_id

        # Create mock Update and Context
        mock_update = MagicMock()
        mock_update.effective_chat = {"id": 123456}
        mock_update.message.message_thread_id = 789

        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock(return_value="sent_message")

        result = await get_chat_id(mock_update, mock_context)

        # Verify send_message was called with correct parameters
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=123456,
            message_thread_id=789,
            text="ID of this chat: 123456, ID of this topic: 789",
        )
        assert result == "sent_message"

    @pytest.mark.asyncio
    async def test_get_chat_id_no_topic(self, mock_env):
        """Test get_chat_id when message has no topic"""
        from src.telegram.get_telegram_chat_and_topic_id import get_chat_id

        mock_update = MagicMock()
        mock_update.effective_chat = {"id": 123456}
        mock_update.message.message_thread_id = None

        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock(return_value="sent_message")

        await get_chat_id(mock_update, mock_context)

        mock_context.bot.send_message.assert_called_once_with(
            chat_id=123456,
            message_thread_id=None,
            text="ID of this chat: 123456, ID of this topic: None",
        )

    def test_polling_setup(self):
        """Test polling function sets up bot correctly"""
        # Mock the TELEGRAM_BOT_TOKEN constant that's loaded at module level
        with patch("src.telegram.get_telegram_chat_and_topic_id.TELEGRAM_BOT_TOKEN", "test_token"):
            from src.telegram.get_telegram_chat_and_topic_id import polling

            with patch(
                "src.telegram.get_telegram_chat_and_topic_id.Application.builder"
            ) as mock_builder:
                mock_app = MagicMock()
                mock_app.add_handler = MagicMock()
                mock_app.run_polling = MagicMock()

                mock_builder_instance = MagicMock()
                mock_builder_instance.token.return_value = mock_builder_instance
                mock_builder_instance.read_timeout.return_value = mock_builder_instance
                mock_builder_instance.get_updates_read_timeout.return_value = mock_builder_instance
                mock_builder_instance.build.return_value = mock_app

                mock_builder.return_value = mock_builder_instance

                polling()

                # Verify Application was configured
                mock_builder_instance.token.assert_called_once_with("test_token")
                mock_builder_instance.read_timeout.assert_called_once_with(60)
                mock_builder_instance.get_updates_read_timeout.assert_called_once_with(60)

                # Verify handler was added
                mock_app.add_handler.assert_called_once()

                # Verify polling started
                mock_app.run_polling.assert_called_once()


class TestTelegramErrorHandlerUtilities:
    """Tests for utility functions in telegram_error_handler.py"""

    def test_load_yaml_file_success(self):
        """Test load_yaml_file successfully loads YAML"""
        from src.telegram.telegram_error_handler import load_yaml_file

        yaml_content = "key: value\nlist:\n  - item1\n  - item2"
        mock_file = mock_open(read_data=yaml_content)

        with patch("builtins.open", mock_file):
            result = load_yaml_file(Path("test.yaml"))

            assert result == {"key": "value", "list": ["item1", "item2"]}

    def test_load_yaml_file_yaml_error(self):
        """Test load_yaml_file handles YAML errors"""
        from src.telegram.telegram_error_handler import load_yaml_file

        # Invalid YAML with tab character (not allowed in YAML)
        invalid_yaml = "key:\tvalue"
        mock_file = mock_open(read_data=invalid_yaml)

        with patch("builtins.open", mock_file):
            with pytest.raises(yaml.YAMLError):
                load_yaml_file(Path("test.yaml"))

    def test_save_yaml_file_success(self):
        """Test save_yaml_file successfully saves YAML"""
        from src.telegram.telegram_error_handler import save_yaml_file

        data = {"key": "value", "list": ["item1", "item2"]}
        mock_file = mock_open()

        with patch("builtins.open", mock_file):
            save_yaml_file(Path("test.yaml"), data)

            # Verify file was opened in write mode
            mock_file.assert_called_once_with(Path("test.yaml"), "w", encoding="UTF-8")

    def test_save_yaml_file_unicode(self):
        """Test save_yaml_file handles unicode correctly"""
        from src.telegram.telegram_error_handler import save_yaml_file

        data = {"message": "Hello 世界 🌍"}
        mock_file = mock_open()

        with patch("builtins.open", mock_file), patch("yaml.safe_dump") as mock_dump:
            save_yaml_file(Path("test.yaml"), data)

            # Verify yaml.safe_dump was called with unicode support
            mock_dump.assert_called_once()
            call_args = mock_dump.call_args
            assert call_args.kwargs["allow_unicode"] is True
