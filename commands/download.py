import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from core.queue import download_queue
from core.streamer import stream_video
from core.extractor import extract_video_url

# Guarda eventos de cancelamento por chat
user_cancel_events = {}


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Use: /download <url>")

    url = context.args[0].strip()
    chat_id = update.effective_chat.id

    await update.message.reply_text("📥 Download adicionado à fila...")

    cancel_event = asyncio.Event()
    user_cancel_events[chat_id] = cancel_event

    async def job():
        print("JOB INICIADO:", url)

        try:
            # Se já for link direto
            if url.endswith(".mp4") or url.endswith(".m3u8"):
                final_url = url
            else:
                print("Extraindo URL...")
                final_url = await extract_video_url(url)

            print("URL FINAL:", final_url)

            if not final_url:
                await context.bot.send_message(
                    chat_id,
                    "❌ Não foi possível extrair o vídeo."
                )
                return

            print("Iniciando streaming...")
            await stream_video(
                context.bot,
                chat_id,
                final_url,
                cancel_event
            )

        except Exception as e:
            print("Erro no JOB:", e)
            await context.bot.send_message(
                chat_id,
                f"❌ Erro durante o download:\n{e}"
            )

    await download_queue.put(job)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in user_cancel_events:
        user_cancel_events[chat_id].set()
        await update.message.reply_text("⛔ Download cancelado.")
    else:
        await update.message.reply_text("Nenhum download ativo.")
