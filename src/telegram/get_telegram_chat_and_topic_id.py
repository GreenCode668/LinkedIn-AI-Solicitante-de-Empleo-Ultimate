"""
Helper file to find out the chat and topic ID in Telegram.
Simply run this file, previously adding the bot to the group
and in this group/topic enter /id
"""

import dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = dotenv.dotenv_values(".env")["tg_token"]


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Print chat id in response to user message"""
    chat_id = update.effective_chat["id"]
    message_thread_id = update.message.message_thread_id
    text = f"ID of this chat: {chat_id}, ID of this topic: {message_thread_id}"
    x = await context.bot.send_message(
        chat_id=chat_id, message_thread_id=message_thread_id, text=text
    )
    return x


def polling() -> None:
    """Start the bot polling"""
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(60)
        .get_updates_read_timeout(60)
        .build()
    )
    # on non command i.e. message - echo the message on Telegram
    application.add_handler(CommandHandler("id", get_chat_id))
    # Run the bot until the user presses Ctrl-C
    application.run_polling()
