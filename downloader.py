import os
import asyncio
import aiohttp
import subprocess
from config import DOWNLOAD_DIR

# 🔥 Chunk maior = mais rápido
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB


# ==========================================================
# DOWNLOAD MP4 DIRETO (RÁPIDO + STREAMING)
# ==========================================================

async def download_mp4(url, progress_callback=None):

    filename = url.split("/")[-1].split("?")[0]

    if not filename.endswith(".mp4"):
        filename += ".mp4"

    output_path = os.path.join(DOWNLOAD_DIR, filename)

    timeout = aiohttp.ClientTimeout(total=None)

    connector = aiohttp.TCPConnector(
        limit=20,
        force_close=False
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector
    ) as session:

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


# ==========================================================
# PEGAR DURAÇÃO DO M3U8
# ==========================================================

def get_duration(url):

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        url
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception("Não foi possível obter duração do stream.")

    return float(result.stdout.strip())


# ==========================================================
# DOWNLOAD M3U8 (FFMPEG OTIMIZADO)
# ==========================================================

async def download_m3u8(url, progress_callback=None):

    filename = url.split("/")[-1].split("?")[0]

    if filename.endswith(".m3u8"):
        filename = filename.replace(".m3u8", ".mp4")
    else:
        filename += ".mp4"

    output_path = os.path.join(DOWNLOAD_DIR, filename)

    total_duration = get_duration(url)

    cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-preset", "ultrafast",
        "-progress", "pipe:1",
        "-y",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )

    last_percent = 0

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        line = line.decode().strip()

        if "out_time_ms=" in line:
            time_ms = int(line.split("=")[1])
            current_time = time_ms / 1_000_000
            percent = (current_time / total_duration) * 100

            if progress_callback:
                if percent - last_percent >= 1:
                    last_percent = percent
                    await progress_callback(min(percent, 100))

    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro ao converter m3u8.")

    return output_path
