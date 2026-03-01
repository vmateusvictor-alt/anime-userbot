import os
import asyncio
import yt_dlp

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def download_universal(url, progress_callback=None):

    loop = asyncio.get_event_loop()
    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)

            if total and progress_callback:
                percent = (downloaded / total) * 100
                asyncio.run_coroutine_threadsafe(
                    progress_callback(percent),
                    loop
                )

    ydl_opts = {
        "outtmpl": output_template,

        # ⚡ muito mais rápido
        "format": "best[ext=mp4]/best",

        "noplaylist": True,
        "progress_hooks": [progress_hook],

        # Turbo fragmentado
        "concurrent_fragment_downloads": 5,

        "retries": 5,
        "fragment_retries": 5,

        "quiet": True,
        "no_warnings": True
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    filepath = await loop.run_in_executor(None, run)

    return filepath


async def download_mp4(url, progress_callback=None):
    return await download_universal(url, progress_callback)


async def download_m3u8(url, progress_callback=None):
    return await download_universal(url, progress_callback)
