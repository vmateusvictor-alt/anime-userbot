import os
import re
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN não definido.")

MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
CHUNK_SIZE = 512 * 1024

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

download_queue = asyncio.Queue()
is_processing = False

# ================= GOOGLE DRIVE =================

def convert_drive_url(url):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

# ================= STREAM DOWNLOAD =================

async def download_file(url, path, progress_msg):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=True) as response:
            size = int(response.headers.get("content-length", 0))

            if size == 0:
                raise Exception("Não foi possível obter tamanho do arquivo.")

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
                            await progress_msg.edit_text(f"📥 Baixando: {percent}%")
                        except:
                            pass

# ================= PROCESS QUEUE =================

async def process_queue():
    global is_processing
    is_processing = True

    while not download_queue.empty():
        message, url = await download_queue.get()
        await handle_download(message, url)
        download_queue.task_done()

    is_processing = False

# ================= HANDLE DOWNLOAD =================

async def handle_download(message: types.Message, url: str):
    url = convert_drive_url(url)
    progress = await message.answer("📥 Preparando download...")

    try:
        filename = url.split("/")[-1].split("?")[0]
        if not filename:
            filename = "arquivo.mp4"

        path = f"/tmp/{filename}"

        await download_file(url, path, progress)

        await progress.edit_text("📤 Enviando para o Telegram...")

        await message.answer_video(
            FSInputFile(path),
            supports_streaming=True
        )

        os.remove(path)

        await progress.delete()

    except Exception as e:
        await progress.edit_text(f"❌ Erro: {str(e)}")

# ================= COMMAND =================

@dp.message()
async def handle_message(message: types.Message):
    if message.text.startswith("/start"):
        await message.answer("🤖 Envie um link direto ou Google Drive para baixar.")
        return

    url = message.text.strip()

    if not url.startswith("http"):
        await message.answer("❌ Envie um link válido.")
        return

    await download_queue.put((message, url))
    await message.answer("📌 Adicionado à fila.")

    global is_processing
    if not is_processing:
        asyncio.create_task(process_queue())

# ================= START =================

async def main():
    print("Bot rodando...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
