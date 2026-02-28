import os
import asyncio
import time
import yt_dlp

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def download_universal(url, progress_callback=None):

    loop = asyncio.get_event_loop()
    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    last_percent = 0
    last_time = 0

    def progress_hook(d):
        nonlocal last_percent, last_time

        if d['status'] == 'downloading':
            if d.get("total_bytes"):
                percent = (d["downloaded_bytes"] / d["total_bytes"]) * 100
                now = time.time()

                # Atualiza apenas se:
                # - passou 5%
                # - ou passou 3 segundos
                if percent - last_percent < 5 and now - last_time < 3:
                    return

                last_percent = percent
                last_time = now

                if progress_callback:
                    asyncio.run_coroutine_threadsafe(
                        progress_callback(percent),
                        loop
                    )

    ydl_opts = {
        "outtmpl": output_template,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mkv",
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "concurrent_fragment_downloads": 1,
        "retries": 10,
        "fragment_retries": 10,
        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        }
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    filepath = await loop.run_in_executor(None, run)

    return filepath


# Compatibilidade
async def download_mp4(url, progress_callback=None):
    return await download_universal(url, progress_callback)


async def download_m3u8(url, progress_callback=None):
    return await download_universal(url, progress_callback)
