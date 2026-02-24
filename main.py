import os
import asyncio
import aiohttp
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ================= CONFIG (RAILWAY VARIABLES) =================

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_string = os.getenv("SESSION_STRING")

if not api_id or not api_hash or not session_string:
    raise ValueError("API_ID, API_HASH ou SESSION_STRING não definidos.")

MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
CHUNK_SIZE = 512 * 1024  # 512KB

client = TelegramClient(StringSession(session_string), api_id, api_hash)

download_queue = asyncio.Queue()
is_processing = False

# ================= GOOGLE DRIVE CONVERTER =================

def convert_drive_url(url):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

# ================= STREAM GENERATOR =================

async def stream_generator(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=True) as response:
            response.raise_for_status()
            async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                yield chunk

# ================= DOWNLOAD HANDLER =================

async def handle_download(event, url):
    msg = await event.reply("📥 Preparando download...")

    url = convert_drive_url(url)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True) as resp:
                size = int(resp.headers.get("content-length", 0))

        if size == 0:
            return await msg.edit("❌ Não foi possível obter tamanho do arquivo.")

        if size > MAX_SIZE:
            return await msg.edit("❌ Arquivo maior que 2GB.")

        await msg.edit("📤 Iniciando upload por streaming...")

        last_percent = -1

        async def progress(current, total):
            nonlocal last_percent
            percent = int((current / total) * 100)
            if percent % 5 == 0 and percent != last_percent:
                last_percent = percent
                try:
                    await msg.edit(f"📤 Enviando: {percent}%")
                except:
                    pass

        file = await client.upload_file(
            stream_generator(url),
            file_size=size,
            part_size_kb=512,
            progress_callback=progress
        )

        await client.send_file(
            event.chat_id,
            file,
            supports_streaming=True
        )

        await msg.delete()

    except Exception as e:
        await msg.edit(f"❌ Erro: {str(e)}")

# ================= FILA =================

async def process_queue():
    global is_processing
    is_processing = True

    while not download_queue.empty():
        event, url = await download_queue.get()
        await handle_download(event, url)
        download_queue.task_done()

    is_processing = False

# ================= COMANDO =================

@client.on(events.NewMessage(pattern=r"\.baixar (.+)"))
async def handler(event):
    url = event.pattern_match.group(1)
    await download_queue.put((event, url))
    await event.reply("📌 Adicionado à fila.")

    global is_processing
    if not is_processing:
        asyncio.create_task(process_queue())

# ================= START =================

def main():
    print("Iniciando Userbot...")
    client.start()
    print("Userbot rodando...")
    client.run_until_disconnected()

if __name__ == "__main__":
    main()
