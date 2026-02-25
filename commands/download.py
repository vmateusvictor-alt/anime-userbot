import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from core.queue import download_queue
from core.streamer import stream_video
from core.extractor import extract_video_url

# Guarda eventos de cancelamento por usuário
user_cancel_events = {}

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Use: /download <url>")

    url = context.args[0]
    chat_id = update.effective_chat.id

    await update.message.reply_text("📥 Adicionado à fila...")

    cancel_event = asyncio.Event()
    user_cancel_events[chat_id] = cancel_event

    async def job():
        final_url = await extract_video_url(url)

        if not final_url:
            await context.bot.send_message(chat_id, "❌ Não foi possível extrair o vídeo.")
            return

        await stream_video(context.bot, chat_id, final_url, cancel_event)

    await download_queue.put(job)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in user_cancel_events:
        user_cancel_events[chat_id].set()
        await update.message.reply_text("⛔ Download cancelado.")
    else:
        await update.message.reply_text("Nenhum download ativo.")
