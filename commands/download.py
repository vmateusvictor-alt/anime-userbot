from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.queue import download_queue
from core.streamer import stream_video
from core.extractor import extract_video_url
from core.cancel import cancel

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Use: /download <url>")

    url = context.args[0]
    chat_id = update.effective_chat.id

    await update.message.reply_text("🔍 Extraindo link...")

    real_url = await extract_video_url(url)

    if not real_url:
        return await update.message.reply_text("❌ Não foi possível extrair vídeo.")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel")]
    ])

    await update.message.reply_text("📥 Adicionado à fila...", reply_markup=keyboard)

    async def job():
        await stream_video(context.bot, chat_id, real_url)

    await download_queue.put(job)


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cancel(update.effective_chat.id)
    await query.edit_message_text("❌ Download cancelado.")
