import os
import re
import asyncio
import aiohttp
import uuid
import gdown
from urllib.parse import urlparse, urljoin

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

VIDEO_EXT = (".mp4", ".mkv", ".mov", ".webm")


# =====================================================
# DOWNLOAD DIRETO
# =====================================================

async def download_direct(url, progress_callback=None):

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:

        async with session.get(url, allow_redirects=True) as resp:

            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")

            # =========================
            # PEGAR NOME
            # =========================

            filename = None

            cd = resp.headers.get("Content-Disposition")

            if cd:
                match = re.findall('filename="?([^"]+)"?', cd)
                if match:
                    filename = match[0]

            if not filename:
                parsed = urlparse(str(resp.url))
                filename = os.path.basename(parsed.path)

            if not filename or "." not in filename:
                filename = str(uuid.uuid4()) + ".mp4"

            path = os.path.join(DOWNLOAD_DIR, filename)

            total = int(resp.headers.get("content-length", 0))

            downloaded = 0
            last_percent = 0

            with open(path, "wb") as f:

                async for chunk in resp.content.iter_chunked(2 * 1024 * 1024):

                    f.write(chunk)

                    downloaded += len(chunk)

                    if total and progress_callback:

                        percent = (downloaded / total) * 100

                        if percent - last_percent >= 5:
                            last_percent = percent
                            await progress_callback(percent)

    return path


# =====================================================
# GOOGLE DRIVE
# =====================================================

def extract_drive_id(url):

    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)'
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


async def download_drive(url):

    file_id = extract_drive_id(url)

    if not file_id:
        raise Exception("Link Drive inválido")

    output = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

    loop = asyncio.get_event_loop()

    await loop.run_in_executor(
        None,
        lambda: gdown.download(
            id=file_id,
            output=output,
            quiet=False
        )
    )

    return output


# =====================================================
# EXTRAIR VIDEOS DE HTML
# =====================================================

async def extract_html_videos(url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception("Erro ao acessar página")

            html = await resp.text()

    links = re.findall(r'href=[\'"]?([^\'" >]+)', html)

    videos = []

    for link in links:

        if link.lower().endswith(VIDEO_EXT):

            full = urljoin(url, link)

            videos.append(full)

    if not videos:
        raise Exception("Nenhum vídeo encontrado")

    return videos


# =====================================================
# YT-DLP FALLBACK
# =====================================================

async def download_ytdlp(url):

    template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-o",
        template,
        "--no-playlist",
        url
    ]

    process = await asyncio.create_subprocess_exec(*cmd)

    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro ao baixar com yt-dlp")

    files = sorted(
        [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
        key=os.path.getctime
    )

    return files[-1]


# =====================================================
# PROCESSADOR UNIVERSAL
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # =============================
    # GOOGLE DRIVE
    # =============================

    if "drive.google.com" in url_lower:

        return await download_drive(url)

    # =============================
    # VIDEO DIRETO
    # =============================

    if url_lower.endswith(VIDEO_EXT):

        return await download_direct(url, progress_callback)

    # =============================
    # TENTAR HTML
    # =============================

    try:

        videos = await extract_html_videos(url)

        results = []

        for v in videos[:10]:

            file = await download_direct(v, progress_callback)

            results.append(file)

        return results

    except:
        pass

    # =============================
    # FALLBACK
    # =============================

    return await download_ytdlp(url)
