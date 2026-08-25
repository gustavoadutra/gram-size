import logging
import os
import asyncio
import contextlib
import datetime as dtm
from typing import NoReturn

from telegram import Update, ForceReply
from telegram.error import Forbidden, NetworkError 
from telegram.ext import (
    Application,
    CommandHandler, 
    ContextTypes,
    MessageHandler,
    filters
    )
from dotenv import load_dotenv


load_dotenv()
API = os.getenv("TELEGRAM-TOKEN")

# LOGS
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Working· {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)
    print(f"message: {update.message.text}")


async def get_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice

    if voice:
        new_file = await context.bot.get_file(voice.file_id)

        await new_file.download_to_drive("teste.mp3")

        await update.message.reply_text(f"Audio salvo!")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(API).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # get the voice 
    application.add_handler(MessageHandler(filters.VOICE, get_voice))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()