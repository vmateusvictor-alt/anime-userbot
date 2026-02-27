import os
import aiohttp
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from pyrogram import Client

# ==============================
# VARIÁVEIS
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN não definido")

if not API_ID:
    raise RuntimeError("API_ID não definido")

if not API_HASH:
    raise RuntimeError("API_HASH não definido")

if not SESSION_STRING:
    raise RuntimeError("SESSION_STRING não definido")

API_ID = int(API_ID)

DOWNLOAD_PATH = "/tmp/video.mp4"

# ==============================
# USERBOT (PYROGRAM)
# ==============================

userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

# ==============================
# BARRA VISUAL
# ==============================

def progress_bar(percent):
    bars = int(percent // 5)
    return "█" * bars + "░" * (20 - bars)

# ==============================
# DOWNLOAD COM PROGRESSO
# ==============================

async def download_file(url, status_msg):
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

                    if total:
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

# ==============================
# UPLOAD PROGRESSO
# ==============================

async def upload_progress(current, total, status_msg):
    percent = int(current * 100 / total)
    bar = progress_bar(percent)

    if percent % 5 == 0:
        try:
            await status_msg.edit_text(
                f"⬆️ Enviando...\n\n"
                f"[{bar}] {percent}%"
            )
        except:
            pass

# ==============================
# COMANDO
# ==============================

async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Use:\n/anime link_mp4")
        return

    url = context.args[0]
    chat_id = update.effective_chat.id

    status_msg = await update.message.reply_text("🔄 Iniciando...")

    try:
        # DOWNLOAD
        await download_file(url, status_msg)

        await status_msg.edit_text("⬆️ Enviando para Telegram...")

        # UPLOAD via USERBOT (2GB permitido)
        await userbot.send_video(
            chat_id=chat_id,
            video=DOWNLOAD_PATH,
            caption="🎬 Aqui está!",
            supports_streaming=True,
            progress=upload_progress,
            progress_args=(status_msg,)
        )

        await status_msg.edit_text("✅ Concluído!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Erro:\n{e}")

    finally:
        if os.path.exists(DOWNLOAD_PATH):
            os.remove(DOWNLOAD_PATH)

# ==============================
# MAIN
# ==============================

def main():

    loop = asyncio.get_event_loop()
    loop.run_until_complete(userbot.start())

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("anime", anime))

    print("🚀 Bot + Userbot rodando")
    app.run_polling()

if __name__ == "__main__":
    main()
