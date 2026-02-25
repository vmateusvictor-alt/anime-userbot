import httpx
import tempfile
import os
import time


async def stream_video(client, event, url):

    progress_msg = await event.reply("⏳ Iniciando download...")

    async with httpx.AsyncClient(timeout=None) as http:
        async with http.stream("GET", url) as response:

            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            start = time.time()

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                file_path = tmp.name

                async for chunk in response.aiter_bytes(1024 * 64):
                    tmp.write(chunk)
                    downloaded += len(chunk)

                    if downloaded % (1024 * 1024) < 65536:
                        percent = (downloaded / total * 100) if total else 0
                        speed = downloaded / (time.time() - start + 1)

                        try:
                            await progress_msg.edit(
                                f"📥 {percent:.2f}%\n"
                                f"{downloaded/1024/1024:.2f} MB\n"
                                f"{speed/1024/1024:.2f} MB/s"
                            )
                        except:
                            pass

    await progress_msg.edit("📤 Enviando para Telegram...")

    await client.send_file(
        event.chat_id,
        file_path,
        supports_streaming=True
    )

    os.remove(file_path)
