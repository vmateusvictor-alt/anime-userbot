import httpx
import tempfile
import os
import time


async def stream_video(bot, chat_id, url, cancel_event):

    progress_message = await bot.send_message(chat_id, "⏳ Iniciando download...")

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", url) as response:

            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            start_time = time.time()

            # cria arquivo temporário (não usa RAM)
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                file_path = tmp.name

                async for chunk in response.aiter_bytes(1024 * 64):

                    if cancel_event.is_set():
                        await bot.send_message(chat_id, "⛔ Cancelado.")
                        os.remove(file_path)
                        return

                    tmp.write(chunk)
                    downloaded += len(chunk)

                    # atualiza progresso a cada ~1MB
                    if downloaded % (1024 * 1024) < 65536:
                        percent = (downloaded / total * 100) if total else 0
                        speed = downloaded / (time.time() - start_time + 1)

                        text = (
                            f"📥 Baixando...\n"
                            f"{percent:.2f}%\n"
                            f"{downloaded / 1024 / 1024:.2f} MB\n"
                            f"Velocidade: {speed / 1024 / 1024:.2f} MB/s"
                        )

                        try:
                            await progress_message.edit_text(text)
                        except:
                            pass

    await progress_message.edit_text("📤 Enviando para Telegram...")

    await bot.send_video(
        chat_id,
        video=open(file_path, "rb"),
        supports_streaming=True
    )

    os.remove(file_path)
