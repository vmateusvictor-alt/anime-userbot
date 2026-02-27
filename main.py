import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
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

async def anime(update, context):

    if not context.args:
        await update.message.reply_text("Envie um link m3u8")
        return

    url = context.args[0]

    async with download_lock:

        msg = await update.message.reply_text("🎬 Baixando...")

        async def download_progress():
            await msg.edit_text("🎬 Convertendo...")

        filepath = await download_m3u8(url, download_progress)

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

    app.add_handler(CommandHandler("anime", anime))

    app.run_polling()

if __name__ == "__main__":
    main()
