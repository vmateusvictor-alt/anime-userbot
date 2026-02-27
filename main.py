import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
from downloader import download_mp4, download_m3u8
from uploader import upload_video

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN não encontrado no Railway!")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ======================================================
# COMANDO /an
# ======================================================

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

    try:

        if url.endswith(".m3u8"):
            filepath = await download_m3u8(url, progress)
        else:
            filepath = await download_mp4(url, progress)

        await msg.edit_text("📤 Enviando para Telegram...")

        await upload_video(
            chat_id=update.effective_chat.id,
            filepath=filepath,
            message=msg
        )

        await msg.edit_text("✅ Concluído!")

        os.remove(filepath)

    except Exception as e:
        await msg.edit_text(f"❌ Erro:\n{e}")


# ======================================================
# MAIN
# ======================================================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("an", anime_handler))

    print("Bot iniciado...")

    app.run_polling()


if __name__ == "__main__":
    main()
