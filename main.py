import os
import re
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN não definido.")

MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
CHUNK_SIZE = 512 * 1024

download_queue = asyncio.Queue()
is_processing = False


# ================= GOOGLE DRIVE =================

def convert_drive_url(url):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


# ================= DOWNLOAD =================

async def download_file(url, path, progress_message):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=True) as response:
            size = int(response.headers.get("content-length", 0))

            if size == 0:
                raise Exception("Não foi possível obter tamanho.")

            if size > MAX_SIZE:
                raise Exception("Arquivo maior que 2GB.")

            downloaded = 0
            last_percent = -1

            with open(path, "wb") as f:
                async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)

                    percent = int((downloaded / size) * 100)
                    if percent % 5 == 0 and percent != last_percent:
                        last_percent = percent
                        try:
                            await progress_message.edit_text(f"📥 Baixando: {percent}%")
                        except:
                            pass


# ================= PROCESS QUEUE =================

async def process_queue(app):
    global is_processing
    is_processing = True

    while not download_queue.empty():
        update, context, url = await download_queue.get()
        await handle_download(update, context, url)
        download_queue.task_done()

    is_processing = False


# ================= HANDLE =================

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    url = convert_drive_url(url)
    progress = await update.message.reply_text("📥 Preparando download...")

    try:
        filename = url.split("/")[-1].split("?")[0]
        if not filename:
            filename = "arquivo.mp4"

        path = f"/tmp/{filename}"

        await download_file(url, path, progress)

        await progress.edit_text("📤 Enviando...")

        await update.message.reply_video(
            video=open(path, "rb"),
            supports_streaming=True
        )

        os.remove(path)
        await progress.delete()

    except Exception as e:
        await progress.edit_text(f"❌ Erro: {str(e)}")


# ================= MESSAGE =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("❌ Envie um link válido.")
        return

    await download_queue.put((update, context, url))
    await update.message.reply_text("📌 Adicionado à fila.")

    global is_processing
    if not is_processing:
        asyncio.create_task(process_queue(context.application))


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Envie um link direto ou Google Drive.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()
