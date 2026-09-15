import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler, 
    MessageHandler,
    filters
    )
from dotenv import load_dotenv

import utils.basic_functions as bf


load_dotenv()
API = os.getenv("TELEGRAM_API_KEY")

# LOGS
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main(API) -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(API).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", bf.start))
    application.add_handler(CommandHandler("help", bf.help_command))

    # on non command i.e message - return info the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bf.response))
    
    # get the voice for future use
    application.add_handler(MessageHandler(filters.VOICE, bf.get_voice))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main(API)