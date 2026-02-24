import aiohttp
import re

CHUNK_SIZE = 512 * 1024
MAX_SIZE = 2 * 1024 * 1024 * 1024


def convert_drive_url(url):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


async def stream_generator(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                yield chunk


async def handle_download(client, event, url):
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

        async def progress(current, total):
            percent = (current / total) * 100
            if int(percent) % 5 == 0:
                await msg.edit(f"📤 Enviando: {percent:.1f}%")

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
