import os
import aiohttp
import asyncio
import subprocess
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from pyrogram import Client

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

DOWNLOAD_DIR = "./cache"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

# =====================
# UTILS
# =====================
def progress_bar(percent):
    bars = int(percent / 5)
    return "█" * bars + "░" * (20 - bars)

async def get_file_size(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url, allow_redirects=True) as resp:
            size = resp.headers.get("Content-Length")
            if size:
                return int(size)
    return None

async def download_stream(url, filepath, status):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_percent = 0

            with open(filepath, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024*1024):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total:
                        percent = int(downloaded * 100 / total)
                        if percent - last_percent >= 5:
                            last_percent = percent
                            await status.edit_text(
                                f"⬇️ Baixando\n[{progress_bar(percent)}] {percent}%"
                            )

async def convert_m3u8(url, output):
    cmd = [
        "ffmpeg",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        output
    ]
    subprocess.run(cmd, check=True)

def generate_thumbnail(video, thumb):
    cmd = [
        "ffmpeg",
        "-i", video,
        "-ss", "00:00:02",
        "-vframes", "1",
        thumb
    ]
    subprocess.run(cmd)

async def upload_progress(current, total, status):
    percent = int(current * 100 / total)
    if percent % 5 == 0:
        await status.edit_text(
            f"⬆️ Enviando\n[{progress_bar(percent)}] {percent}%"
        )

# =====================
# COMANDO
# =====================
async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use:\n/anime link")
        return

    url = context.args[0]
    status = await update.message.reply_text("🔍 Verificando tamanho...")

    size = await get_file_size(url)

    if size:
        gb = size / (1024**3)
        if gb > 2:
            await status.edit_text("❌ Arquivo maior que 2GB.")
            return
        await status.edit_text(f"📦 Tamanho: {gb:.2f} GB\nIniciando download...")

    filename = os.path.basename(urlparse(url).path)
    if not filename:
        filename = "video.mp4"

    filepath = os.path.join(DOWNLOAD_DIR, filename)

    try:
        if ".m3u8" in url:
            await status.edit_text("🎬 Convertendo m3u8...")
            await convert_m3u8(url, filepath)
        else:
            await download_stream(url, filepath, status)

        thumb = filepath + ".jpg"
        generate_thumbnail(filepath, thumb)

        await userbot.send_video(
            chat_id=update.effective_chat.id,
            video=filepath,
            thumb=thumb,
            caption=filename,
            supports_streaming=True,
            progress=upload_progress,
            progress_args=(status,)
        )

        await status.edit_text("✅ Concluído!")

    except Exception as e:
        await status.edit_text(f"❌ Erro:\n{e}")

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(thumb):
            os.remove(thumb)

# =====================
# START USERBOT
# =====================
async def start_userbot(app):
    await userbot.start()

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
