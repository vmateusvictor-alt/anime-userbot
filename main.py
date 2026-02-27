import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH, SESSION_STRING
from downloader import download_m3u8, download_mp4
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


def is_m3u8(url):
    return ".m3u8" in url.lower()


async def an_command(update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Use:\n/an link_do_video")
        return

    url = context.args[0]

    async with download_lock:

        msg = await update.message.reply_text("🔍 Verificando link...")

        async def progress(percent):
            bar = "█" * int(percent // 5)
            bar = bar.ljust(20, "░")
            await msg.edit_text(
                f"📥 Baixando...\n[{bar}] {percent:.2f}%"
            )

        try:

            if is_m3u8(url):
                filepath = await download_m3u8(url, progress)
            else:
                filepath = await download_mp4(url, progress)

        except Exception as e:
            await msg.edit_text(f"❌ Erro ao baixar:\n{str(e)}")
            return

        await msg.edit_text("📤 Enviando...")

        await upload_video(
            userbot,
            update.effective_chat.id,
            filepath,
            msg
        )

        await msg.edit_text("✅ Concluído!")


def main():

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(start_userbot)
        .build()
    )

    app.add_handler(CommandHandler("an", an_command))

    print("Bot iniciado com /an")
    app.run_polling()


if __name__ == "__main__":
    main()
