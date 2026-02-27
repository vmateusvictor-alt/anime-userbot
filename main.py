import os
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from pyrogram import Client
from downloader import download_mp4, download_m3u8
from uploader import upload_video

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

download_lock = asyncio.Semaphore(1)

# 🔥 userbot inicia UMA VEZ
userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

async def start_userbot(app):
    await userbot.start()


async def anime_handler(update, context):

    if not context.args:
        await update.message.reply_text("Use:\n/an link")
        return

    url = context.args[0]
    msg = await update.message.reply_text("📥 Baixando...")

    async def progress(percent):
        bar = "█" * int(percent // 5)
        bar = bar.ljust(20, "░")
        try:
            await msg.edit_text(f"📥 Baixando...\n[{bar}] {percent:.2f}%")
        except:
            pass

    async with download_lock:

        try:
            if ".m3u8" in url:
                filepath = await download_m3u8(url, progress)
            else:
                filepath = await download_mp4(url, progress)

            await msg.edit_text("📤 Enviando...")

            await upload_video(
                userbot,
                update.effective_chat.id,
                filepath,
                msg
            )

            os.remove(filepath)

            await msg.edit_text("✅ Concluído!")

        except Exception as e:
            await msg.edit_text(f"❌ Erro:\n{e}")


def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(start_userbot)  # 🔥 inicia userbot aqui
        .build()
    )

    app.add_handler(CommandHandler("an", anime_handler))

    print("Bot iniciado")
    app.run_polling()


if __name__ == "__main__":
    main()
