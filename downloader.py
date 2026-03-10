import os
import asyncio
import aiohttp
import re
import uuid
from urllib.parse import urljoin, urlparse

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 4 * 1024 * 1024
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".m3u8")

HEADERS = {"User-Agent": "Mozilla/5.0"}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =====================================================
# TORRENT / MAGNET
# =====================================================

async def download_torrent(url):

    cmd = [
        "aria2c",
        "--seed-time=0",
        "--dir", DOWNLOAD_DIR,
        url
    ]

    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro ao baixar torrent.")

    videos = []

    for root, _, files in os.walk(DOWNLOAD_DIR):
        for f in files:
            if f.lower().endswith((".mkv", ".mp4")):
                videos.append(os.path.join(root, f))

    if not videos:
        raise Exception("Nenhum vídeo encontrado no torrent.")

    return max(videos, key=os.path.getsize)


# =====================================================
# DOWNLOAD DIRETO
# =====================================================

async def download_direct(url, progress_callback=None):

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as resp:

            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")

            filename = os.path.basename(str(resp.url).split("?")[0])

            if not filename or "." not in filename:
                filename = str(uuid.uuid4()) + ".mp4"

            output_path = os.path.join(DOWNLOAD_DIR, filename)

            total = int(resp.headers.get("content-length", 0) or 0)
            downloaded = 0
            last_percent = 0

            with open(output_path, "wb") as f:
                while True:
                    chunk = await resp.content.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)

                    if total and progress_callback:
                        percent = (downloaded / total) * 100
                        if percent - last_percent >= 5:
                            last_percent = percent
                            await progress_callback(round(percent, 1))

    if progress_callback:
        await progress_callback(100)

    return output_path


# =====================================================
# PROCESS LINK UNIVERSAL
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    if url_lower.startswith("magnet:") or url_lower.endswith(".torrent"):
        return await download_torrent(url)

    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.head(url, allow_redirects=True) as resp:

                content_type = resp.headers.get("content-type", "")

                if "video" in content_type or "octet-stream" in content_type:
                    return await download_direct(url, progress_callback)

    except:
        pass

    return await download_direct(url, progress_callback)
