import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
from pyrogram import Client
from downloader import download_mp4, download_m3u8
from uploader import upload_video

# =====================================================
# VARIÁVEIS
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN não configurado!")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

download_lock = asyncio.Semaphore(1)

# =====================================================
# USERBOT
# =====================================================

userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    no_updates=True
)

async def start_userbot(app):
    if not userbot.is_connected:
        await userbot.start()

# =====================================================
# COMANDO /an
# =====================================================

async def anime_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Use assim:\n/an link_do_video"
        )
        return

    url = context.args[0]

    msg = await update.message.reply_text("📥 Iniciando download...")

    last_percent = 0

    async def progress(percent):
        nonlocal last_percent

        if percent - last_percent >= 2:
            last_percent = percent

            bar = "█" * int(percent // 5)
            bar = bar.ljust(20, "░")

            try:
                await msg.edit_text(
                    f"📥 Baixando...\n"
                    f"[{bar}] {percent:.2f}%"
                )
            except:
                pass

    async with download_lock:
        try:

            if ".m3u8" in url.lower():
                filepath = await download_m3u8(url, progress)
            else:
                filepath = await download_mp4(url, progress)

            await msg.edit_text("📤 Enviando para Telegram...")

            # Upload para canal
            message_id = await upload_video(
                userbot=userbot,
                filepath=filepath,
                message=msg
            )

            # Bot copia do canal
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=message_id
            )

            if os.path.exists(filepath):
                os.remove(filepath)

            await msg.edit_text("✅ Concluído!")

        except Exception as e:
            await msg.edit_text(f"❌ Erro:\n{e}")

# =====================================================
# MAIN
# =====================================================

def main():

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(start_userbot)
        .build()
    )

    app.add_handler(CommandHandler("an", anime_handler))

    print("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
