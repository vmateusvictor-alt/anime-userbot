import os
import asyncio
import aiohttp
import re
import uuid
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 2 * 1024 * 1024

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".m3u8")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# apenas 1 download por vez (Railway safe)
DOWNLOAD_LOCK = asyncio.Semaphore(1)


# =====================================================
# ORDENAÇÃO NATURAL
# =====================================================

def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r'([0-9]+)', s)
    ]


# =====================================================
# DOWNLOAD DIRETO
# =====================================================

async def download_direct(url, progress_callback=None):

    async with DOWNLOAD_LOCK:

        timeout = aiohttp.ClientTimeout(total=None)

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": url
            }
        ) as session:

            async with session.get(url, allow_redirects=True) as resp:

                if resp.status != 200:
                    raise Exception(f"Erro HTTP {resp.status}")

                parsed = urlparse(str(resp.url))

                filename = os.path.basename(parsed.path)

                if not filename or "." not in filename:
                    filename = str(uuid.uuid4()) + ".mp4"

                filepath = os.path.join(DOWNLOAD_DIR, filename)

                total = int(resp.headers.get("content-length", 0) or 0)

                downloaded = 0
                last_percent = 0

                with open(filepath, "wb") as f:

                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):

                        f.write(chunk)
                        downloaded += len(chunk)

                        if total and progress_callback:

                            percent = (downloaded / total) * 100

                            if percent - last_percent >= 5:
                                last_percent = percent
                                await progress_callback(round(percent, 1))

        return filepath


# =====================================================
# DOWNLOAD M3U8
# =====================================================

async def download_m3u8(url):

    async with DOWNLOAD_LOCK:

        filename = str(uuid.uuid4()) + ".mp4"
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            filepath
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        await process.wait()

        if process.returncode != 0:
            raise Exception("Erro ao baixar m3u8")

        return filepath


# =====================================================
# EXTRAIR VÍDEOS DE PASTA
# =====================================================

async def extract_videos_from_folder(url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception("Não foi possível acessar a pasta")

            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")

    video_links = []
    folder_links = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if href.startswith("?") or href.startswith("#"):
            continue

        lower = href.lower()

        if any(ext in lower for ext in VIDEO_EXTENSIONS):

            video_links.append(urljoin(url, href))

        elif href.endswith("/"):

            folder_links.append(urljoin(url, href))

    if video_links:
        video_links.sort(key=natural_sort_key)
        return video_links

    # entra nas subpastas
    for folder in folder_links:

        try:

            sub = await extract_videos_from_folder(folder)

            if sub:
                return sub

        except:
            pass

    raise Exception("Nenhum vídeo encontrado na pasta")


# =====================================================
# PROCESSADOR PRINCIPAL
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # download.aspx (workers / rclone)
    if "download.aspx" in url_lower:
        return await download_direct(url, progress_callback)

    # m3u8
    if url_lower.endswith(".m3u8"):
        return await download_m3u8(url)

    # mp4 ou mkv
    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)

    # tentar detectar pasta
    try:

        async with aiohttp.ClientSession(headers=HEADERS) as session:

            async with session.get(url) as resp:

                content_type = resp.headers.get("content-type", "")

                if "text/html" in content_type:

                    html = await resp.text()

                    if any(ext in html.lower() for ext in VIDEO_EXTENSIONS):

                        links = await extract_videos_from_folder(url)

                        results = []

                        for video in links:

                            path = await process_link(video, progress_callback)

                            results.append(path)

                        return results

    except:
        pass

    # fallback final
    raise Exception("Link não suportado ou expirado")
