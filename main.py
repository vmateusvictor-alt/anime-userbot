import os
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN não definido")

DOWNLOAD_PATH = "/tmp/video.mp4"

# =========================
# BARRA VISUAL
# =========================
def progress_bar(percent):
    bars = int(percent // 5)
    return "█" * bars + "░" * (20 - bars)

# =========================
# DOWNLOAD EM CHUNKS
# =========================
async def download_file(url, status_msg):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_percent = 0

            with open(DOWNLOAD_PATH, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total > 0:
                        percent = int(downloaded * 100 / total)

                        if percent - last_percent >= 5:
                            last_percent = percent
                            bar = progress_bar(percent)

                            await status_msg.edit_text(
                                f"⬇️ Baixando...\n\n"
                                f"[{bar}] {percent}%"
                            )

# =========================
# COMANDO /anime
# =========================
async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Use:\n/anime link_mp4"
        )
        return

    url = context.args[0]

    status_msg = await update.message.reply_text("🔄 Iniciando download...")

    try:
        # DOWNLOAD
        await download_file(url, status_msg)

        await status_msg.edit_text("⬆️ Enviando para Telegram...")

        # ENVIO (até 2GB)
        with open(DOWNLOAD_PATH, "rb") as video:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video,
                supports_streaming=True,
                read_timeout=600,
                write_timeout=600,
                connect_timeout=60,
            )

        await status_msg.edit_text("✅ Concluído!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Erro:\n{e}")

    finally:
        if os.path.exists(DOWNLOAD_PATH):
            os.remove(DOWNLOAD_PATH)

# =========================
# MAIN
# =========================
async def main():

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(60)
        .read_timeout(600)
        .write_timeout(600)
        .build()
    )

    app.add_handler(CommandHandler("anime", anime))

    print("🚀 Bot rodando em POLLING (anti-413)")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
