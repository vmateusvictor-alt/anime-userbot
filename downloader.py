import os
import re
import uuid
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 2 * 1024 * 1024

VIDEO_EXT = (".mp4", ".mkv", ".webm", ".m3u8")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

DOWNLOAD_LOCK = asyncio.Semaphore(1)


# ===============================================
# ORDENAÇÃO NATURAL
# ===============================================

def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"([0-9]+)", s)
    ]


# ===============================================
# CONVERTER LINK GOOGLE DRIVE
# ===============================================

def convert_drive_link(url):

    match = re.search(r"/file/d/([^/]+)", url)

    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    return url


# ===============================================
# PEGAR NOME DO ARQUIVO
# ===============================================

def get_filename(resp):

    cd = resp.headers.get("Content-Disposition")

    if cd:

        match = re.findall('filename="?([^"]+)"?', cd)

        if match:
            return match[0]

    parsed = urlparse(str(resp.url))
    name = os.path.basename(parsed.path)

    name = name.split("?")[0]

    if not name or "." not in name:
        name = str(uuid.uuid4()) + ".mp4"

    return name


# ===============================================
# DOWNLOAD DIRETO
# ===============================================

async def download_direct(url, progress_callback=None):

    async with DOWNLOAD_LOCK:

        timeout = aiohttp.ClientTimeout(total=None)

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={**HEADERS, "Referer": url}
        ) as session:

            async with session.get(url, allow_redirects=True) as resp:

                if resp.status != 200:
                    raise Exception(f"Erro HTTP {resp.status}")

                filename = get_filename(resp)

                filepath = os.path.join(DOWNLOAD_DIR, filename)

                total = resp.headers.get("content-length")

                if total:
                    total = int(total)
                else:
                    total = 0

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


# ===============================================
# DOWNLOAD M3U8
# ===============================================

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
            raise Exception("Erro ao baixar stream")

        return filepath


# ===============================================
# EXTRAIR VÍDEOS DE PASTA
# ===============================================

async def extract_videos_from_folder(url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception("Não foi possível acessar pasta")

            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")

    videos = []
    folders = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if href.startswith("?") or href.startswith("#"):
            continue

        lower = href.lower()

        if any(ext in lower for ext in VIDEO_EXT):

            videos.append(urljoin(url, href))

        elif href.endswith("/"):

            folders.append(urljoin(url, href))

    if videos:

        videos.sort(key=natural_sort_key)

        return videos

    for folder in folders:

        try:

            result = await extract_videos_from_folder(folder)

            if result:
                return result

        except:
            pass

    raise Exception("Nenhum vídeo encontrado")


# ===============================================
# PROCESSADOR PRINCIPAL
# ===============================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # GOOGLE DRIVE
    if "drive.google.com" in url_lower:

        url = convert_drive_link(url)

        return await download_direct(url, progress_callback)

    # WORKERS DOWNLOAD
    if "download.aspx" in url_lower:

        return await download_direct(url, progress_callback)

    # STREAM
    if url_lower.endswith(".m3u8"):

        return await download_m3u8(url)

    # VIDEO DIRETO
    if url_lower.endswith((".mp4", ".mkv", ".webm")):

        return await download_direct(url, progress_callback)

    # TENTAR DETECTAR PASTA

    try:

        async with aiohttp.ClientSession(headers=HEADERS) as session:

            async with session.get(url) as resp:

                content_type = resp.headers.get("content-type", "")

                if "text/html" in content_type:

                    html = await resp.text()

                    if any(ext in html.lower() for ext in VIDEO_EXT):

                        links = await extract_videos_from_folder(url)

                        results = []

                        for video in links:

                            path = await process_link(video, progress_callback)

                            results.append(path)

                        return results

    except:
        pass

    raise Exception("Link não suportado ou expirado")
