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
#from openai import OpenAI

import telegram_utils.basic_functions as bf



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