from telegram import Update, ForceReply
from telegram.ext import (
    ContextTypes,
    )

from .rag_handler import RAG

# Initiate rag whatever
rag = RAG()

# Basic start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Working· {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


# TODO document all functionalities
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


# TODO posterior use with command by voice
async def get_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice
    if voice:
        new_file = await context.bot.get_file(voice.file_id)
        await new_file.download_to_drive("teste.mp3")
        await update.message.reply_text(f"Audio salvo!")


async def response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply the user message with rag search and LLM text threatment."""
    response = rag.generate_response(update.message.text)
    await update.message.reply_text(response)
    print(f"message: {update.message.text}")
