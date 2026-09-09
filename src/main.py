import logging
import os
import asyncio
import contextlib
import datetime as dtm
from typing import NoReturn

from telegram import Update, ForceReply
from telegram.ext import (
    Application,
    CommandHandler, 
    ContextTypes,
    MessageHandler,
    filters
    )
from dotenv import load_dotenv
from openai import OpenAI

from telegram_utils.basic_functions as bf

load_dotenv()
API = os.getenv("TELEGRAM_API_KEY")

# LOGS
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(API).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", bf.start))
    application.add_handler(CommandHandler("help", bf.help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bf.echo))

    # get the voice 
    application.add_handler(MessageHandler(filters.VOICE, bf.get_voice))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()