import os
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =========================
# TOKEN
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN não definido no Railway")

DOWNLOAD_PATH = "/tmp/video.mp4"

# =========================
# BARRA DE PROGRESSO
# =========================
def progress_bar(percent: int):
    bars = int(percent // 5)
    return "█" * bars + "░" * (20 - bars)

# =========================
# DOWNLOAD EM CHUNKS (1MB)
# =========================
async def download_file(url: str, status_msg):
    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout) as session:
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

                            try:
                                await status_msg.edit_text(
                                    f"⬇️ Baixando...\n\n"
                                    f"[{bar}] {percent}%"
                                )
                            except:
                                pass

# =========================
# COMANDO /anime
# =========================
async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Use:\n/anime link_mp4")
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
                connect_timeout=60,
                read_timeout=600,
                write_timeout=600,
            )

        await status_msg.edit_text("✅ Concluído!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Erro:\n{e}")

    finally:
        if os.path.exists(DOWNLOAD_PATH):
            os.remove(DOWNLOAD_PATH)

# =========================
# MAIN (SEM ASYNCIO.RUN)
# =========================
def main():

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(60)
        .read_timeout(600)
        .write_timeout(600)
        .build()
    )

    app.add_handler(CommandHandler("anime", anime))

    print("🚀 Bot rodando em polling (anti-413)")
    app.run_polling()

if __name__ == "__main__":
    main()
