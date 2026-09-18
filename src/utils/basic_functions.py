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
        rf"Olá {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Olá! O Brian - Fisio foi desenvolvido para responder dúvidas fisioterapêuticas usando o conteúdo de livros e materiais de estudo disponíveis no sistema.\n\n"
        "Como funciona:\n"
        "• Você envia uma pergunta em texto;\n"
        "• O sistema busca informações relevantes no acervo de documentos;\n"
        "• A resposta é montada com base nesses materiais e enviada de forma clara;\n"
        "• O objetivo é ajudar na consulta de conteúdos acadêmicos e de estudo.\n\n"
        "Comandos disponíveis:\n"
        "• /start - inicia a conversa;\n"
        "• /help - mostra esta explicação;\n"
        "• Envie qualquer dúvida em texto e o sistema tentará responder com base nos materiais indexados.\n\n"
        "Obs.: o bot está em evolução e pode receber novas funcionalidades no futuro, como suporte a áudio e respostas ainda mais refinadas."
    )
    await update.message.reply_text(help_text)


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