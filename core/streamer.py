import time
import httpx
import m3u8
from config import CHUNK_SIZE
from utils.formatters import format_size
from core.cancel import is_active, register

async def stream_video(bot, chat_id, url):

    register(chat_id)

    status = await bot.send_message(chat_id, "📥 Preparando...")

    async with httpx.AsyncClient(timeout=None) as client:

        if url.endswith(".m3u8"):
            playlist = m3u8.loads((await client.get(url)).text)
            segments = playlist.segments

            total_segments = len(segments)
            current = 0
            start = time.time()

            async def generator():
                nonlocal current

                for segment in segments:

                    if not is_active(chat_id):
                        break

                    seg_url = segment.uri
                    if not seg_url.startswith("http"):
                        seg_url = url.rsplit("/", 1)[0] + "/" + seg_url

                    r = await client.get(seg_url)
                    current += 1

                    percent = (current / total_segments) * 100
                    elapsed = time.time() - start
                    speed = current / elapsed if elapsed > 0 else 0

                    await status.edit_text(
                        f"📤 Enviando...\n"
                        f"{percent:.1f}%\n"
                        f"🚀 {speed:.2f} segmentos/s"
                    )

                    yield r.content

            await bot.send_video(chat_id, video=generator())

        else:
            async with client.stream("GET", url) as response:

                total = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                start = time.time()
                last_update = 0

                async def generator():
                    nonlocal downloaded, last_update

                    async for chunk in response.aiter_bytes(CHUNK_SIZE):

                        if not is_active(chat_id):
                            break

                        downloaded += len(chunk)
                        now = time.time()
                        elapsed = now - start
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        eta = (total - downloaded) / speed if speed > 0 else 0
                        percent = (downloaded / total) * 100 if total else 0

                        if now - last_update > 2:
                            filled = int(percent // 5)
                            bar = "█" * filled + "░" * (20 - filled)

                            await status.edit_text(
                                f"[{bar}] {percent:.1f}%\n"
                                f"📦 {format_size(downloaded)} / {format_size(total)}\n"
                                f"🚀 {format_size(speed)}/s\n"
                                f"⏳ {int(eta)}s"
                            )
                            last_update = now

                        yield chunk

                await bot.send_video(chat_id, video=generator(), supports_streaming=True)

    await status.edit_text("✅ Finalizado!")
