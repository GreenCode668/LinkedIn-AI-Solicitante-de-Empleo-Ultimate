import asyncio
from typing import Any, Dict, Union

import dotenv
from telethon import TelegramClient

from config.logger_config import logger
from telegram import Bot
from telegram.error import TelegramError


async def send_captcha(bot_token, chat_id, topic_id, img_path, message):
    """Send captcha message with PTB"""
    bot = Bot(token=bot_token)
    await bot.send_photo(
        chat_id=chat_id, message_thread_id=topic_id, photo=open(img_path, "rb"), caption=message
    )


async def receive_messages(api_id: str, api_hash: str, chat_id: str, topic_id: str, message: str):
    """Receive messages with Telethon"""
    client = TelegramClient("my-client", api_id, api_hash)
    async with client:
        messages_ = await client.get_messages(chat_id, limit=10, reply_to=topic_id)
        for message_ in messages_:
            if message_.reply_to_msg_id:
                reply_msg_id = message_.reply_to_msg_id
                reply_message = await client.get_messages(
                    chat_id, ids=reply_msg_id, reply_to=topic_id
                )
                if reply_message and reply_message.text == message:
                    return message_.text


async def process_captcha(
    tg_token, tg_api_id, tg_api_hash, chat_id, topic_id, img_path, message, listen=False
) -> Union[str, None]:
    """Search for a captcha and if found, send it to the chat for solving"""
    if not listen:
        # Send a message using PTB
        await send_captcha(tg_token, chat_id, topic_id, img_path, message)
    else:
        # Receive messages using Telethon
        return await receive_messages(tg_api_id, tg_api_hash, chat_id, topic_id, message)


class TelegramReportSender:
    """
    Class for sending error messages through Telegram.
    If there is an error in the sending process, we wait and send again.
    """

    def __init__(self):
        telegram_bot_token = dotenv.dotenv_values(".env")["tg_token"]
        self.bot = Bot(token=telegram_bot_token)
        self.chat_id = dotenv.dotenv_values(".env")["tg_chat_id"]
        self.report_topic_id = dotenv.dotenv_values(".env")["tg_report_topic_id"]
        self.message = ""

    async def send_telegram_report(
        self,
        login: str,
        resume: Dict[str, Any],
        success_applies_num: str,
        jobs_no_info: str,
        skill_stat: str,
        resume_recommendations: str,
        resume_component: Any,
    ) -> None:
        """
        Async version of send_telegram_report for proper async/await usage
        """
        # add client contacts
        email = resume["personal_information"].get("email", "")

        if login and "@" in login:
            header = f"Client email: {login}"
        else:
            email = resume_component.deanonymize_text(email)
            header = f"Client email: {email}"

        first_name = resume["personal_information"].get("first_name", "")
        first_name = resume_component.deanonymize_text(first_name)
        last_name = resume["personal_information"].get("last_name", "")
        last_name = resume_component.deanonymize_text(last_name)
        header += f"\nClient name: {first_name} {last_name}\n"

        message = header
        message += (
            f"Total number of vacancies to which the application responded: {success_applies_num}\n"
        )

        # add list of vacancies that couldn't be responded to
        if jobs_no_info:
            message += "Below we attach a list of vacancies to which the application could not respond for whatever reason:\n\n"
            jobs_no_info = self._format_jobs_no_info(jobs_no_info)
            message += jobs_no_info

        # add statistics on most in-demand vacancies
        if skill_stat:
            message += "\nBelow we attach statistics on the most in-demand skills in the vacancies you are interested in:\n\n"
            skill_stat = sorted(
                [(k, v) for k, v in skill_stat.items()], key=lambda x: x[1], reverse=True
            )[:20]
            for skill, stat in skill_stat:
                message += f"  {skill}: {stat}\n"

        # add resume improvement recommendations
        if resume_recommendations:
            message += "\nAlso we attach recommendations for improving your resume:\n\n"
            message += resume_recommendations

        self.message = message

        # Use proper async/await instead of asyncio.run()
        await self._send_chunked_messages(self.message, header)

    async def _send_chunked_messages(self, message, header):
        """
        Since Telegram has a limit on the length of a message of 4096 characters,
        we send the report in parts of 4096 characters
        """
        i = 0
        while i < len(message):
            if i == 0:
                part_message = message[:4096]
                i += 4096
            else:
                part_message = header + message[i : i + 4096 - len(header)]
                i += 4096 - len(header)
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    message_thread_id=self.report_topic_id,
                    text=part_message,
                )
            except TelegramError as e:
                logger.error(f"Failed to send Telegram report:\n{e}")
            await asyncio.sleep(3)  # Use async sleep

    def _format_jobs_no_info(self, jobs_no_info: list) -> str:
        """Format the information about the vacancies to which the application could not respond for whatever reason"""
        res = ""
        for job_info in jobs_no_info:
            res += f"**Vacancy name:** {job_info['job_title']}\n"
            res += f"**Vacancy link:** {job_info['link']}\n"
            res += f"**Reason:** {job_info['reason']}\n\n"
        return res


if __name__ == "__main__":
    from config.constants import TG_CAPTCHA_TOPIC_ID

    secrets = dotenv.dotenv_values(".env")
    tg_token = secrets["tg_token"]
    tg_api_id = secrets["tg_api_id"]
    tg_api_hash = secrets["tg_api_hash"]
    tg_chat_id = secrets["tg_chat_id"]

    message = "1747994625258759"
    text = asyncio.run(
        receive_messages(tg_api_id, tg_api_hash, tg_chat_id, TG_CAPTCHA_TOPIC_ID, message=message)
    )
    print(text)
