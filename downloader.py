import os
import asyncio
import aiohttp
import subprocess

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 4 * 1024 * 1024


# =====================================================
# DOWNLOAD MP4 DIRETO
# =====================================================

async def download_mp4(url, progress_callback=None):

    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".mp4"):
        filename += ".mp4"

    output_path = os.path.join(DOWNLOAD_DIR, filename)

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_percent = 0

            with open(output_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total and progress_callback:
                        percent = (downloaded / total) * 100
                        if percent - last_percent >= 1:
                            last_percent = percent
                            await progress_callback(percent)

    return output_path


# =====================================================
# DOWNLOAD M3U8
# =====================================================

async def download_m3u8(url, progress_callback=None):

    filename = "video.mp4"
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    cmd = [
        "ffmpeg",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-y",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro ao converter m3u8.")

    return output_path


# =====================================================
# DOWNLOAD UNIVERSAL (Google Drive, páginas, etc)
# =====================================================

async def download_universal(url, progress_callback=None):

    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "-o", output_path,
        url
    ]

    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro ao baixar com yt-dlp.")

    # pegar último arquivo baixado
    files = sorted(
        [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
        key=os.path.getctime
    )

    return files[-1]
