import os
import re
import asyncio
import aiohttp
import uuid
import gdown
from urllib.parse import urlparse, urljoin

DOWNLOAD_DIR = "downloads"
VIDEO_EXT = (".mp4", ".mkv", ".m3u8")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================================
# FILA GLOBAL (evita travar Railway)
# =====================================================

DOWNLOAD_QUEUE = asyncio.Queue()


async def download_worker():

    while True:

        url, callback, future = await DOWNLOAD_QUEUE.get()

        try:

            result = await _process_link(url, callback)
            future.set_result(result)

        except Exception as e:

            future.set_exception(e)

        DOWNLOAD_QUEUE.task_done()


async def process_link(url, progress_callback=None):

    loop = asyncio.get_event_loop()
    future = loop.create_future()

    await DOWNLOAD_QUEUE.put((url, progress_callback, future))

    return await future


# =====================================================
# DOWNLOAD DIRETO
# =====================================================

async def download_direct(url, progress_callback=None):

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:

        async with session.get(url, allow_redirects=True) as resp:

            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")

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

                async for chunk in resp.content.iter_chunked(4 * 1024 * 1024):

                    f.write(chunk)

                    downloaded += len(chunk)

                    if total and progress_callback:

                        percent = (downloaded / total) * 100

                        if percent - last_percent >= 5:
                            last_percent = percent
                            await progress_callback(round(percent, 1))

    return path


# =====================================================
# DOWNLOAD M3U8
# =====================================================

async def download_m3u8(url):

    filename = str(uuid.uuid4()) + ".mp4"
    path = os.path.join(DOWNLOAD_DIR, filename)

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        path
    ]

    process = await asyncio.create_subprocess_exec(*cmd)

    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro ao baixar m3u8")

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


def extract_drive_folder(url):

    m = re.search(r'folders/([a-zA-Z0-9_-]+)', url)

    if m:
        return m.group(1)

    return None


async def download_drive(url):

    file_id = extract_drive_id(url)

    if file_id:

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

    folder_id = extract_drive_folder(url)

    if folder_id:

        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            None,
            lambda: gdown.download_folder(
                id=folder_id,
                output=DOWNLOAD_DIR,
                quiet=False,
                remaining_ok=True
            )
        )

        files = sorted(
            [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
            key=os.path.getctime
        )

        return files

    raise Exception("Link Drive inválido")


# =====================================================
# EXTRAIR LINKS DE PASTA HTML
# =====================================================

async def extract_html_videos(url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception("Erro ao acessar pasta")

            html = await resp.text()

    links = re.findall(r'href=[\'"]?([^\'" >]+)', html)

    videos = []

    for link in links:

        if link.lower().endswith(VIDEO_EXT):

            full = urljoin(url, link)

            videos.append(full)

    if not videos:
        raise Exception("Nenhum vídeo encontrado")

    videos.sort()

    return videos


# =====================================================
# YT-DLP FALLBACK
# =====================================================

async def download_ytdlp(url):

    template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-o", template,
        url
    ]

    process = await asyncio.create_subprocess_exec(*cmd)

    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro yt-dlp")

    files = sorted(
        [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
        key=os.path.getctime
    )

    return files[-1]


# =====================================================
# PROCESSADOR UNIVERSAL
# =====================================================

async def _process_link(url, progress_callback=None):

    url_lower = url.lower()

    # m3u8
    if url_lower.endswith(".m3u8"):
        return await download_m3u8(url)

    # video direto
    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)

    # google drive
    if "drive.google.com" in url_lower:
        return await download_drive(url)

    # html folder
    try:

        videos = await extract_html_videos(url)

        results = []

        for v in videos[:10]:  # limite

            file = await download_direct(v, progress_callback)

            results.append(file)

        return results

    except:
        pass

    # fallback
    return await download_ytdlp(url)
