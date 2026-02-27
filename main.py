import asyncio
import re
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH, SESSION_STRING
from downloader import download_m3u8
from uploader import upload_video

download_lock = asyncio.Semaphore(1)

userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)


async def start_userbot(app):
    await userbot.start()


def extract_link(text):
    match = re.search(r"(https?://\S+)", text)
    return match.group(1) if match else None


async def handle_link(update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    url = extract_link(text)

    if not url or ".m3u8" not in url:
        await update.message.reply_text("Envie um link m3u8 válido.")
        return

    async with download_lock:

        msg = await update.message.reply_text("🎬 Iniciando download...")

        async def progress(percent):
            bar = "█" * int(percent // 5)
            bar = bar.ljust(20, "░")
            await msg.edit_text(f"🎬 Baixando...\n[{bar}] {percent:.2f}%")

        filepath = await download_m3u8(url, progress)

        await msg.edit_text("📤 Enviando...")

        await upload_video(userbot, update.effective_chat.id, filepath, msg)

        await msg.edit_text("✅ Concluído!")


def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(start_userbot)
        .build()
    )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    app.run_polling()


if __name__ == "__main__":
    main()
