import os
import re
import aiohttp
import asyncio
import yt_dlp
from urllib.parse import urljoin

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 1024 * 1024 * 4

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# =====================================================
# DOWNLOAD DIRETO (MP4 / MKV)
# =====================================================

async def download_direct(url, progress_callback=None):

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:

        async with session.get(url, allow_redirects=True) as resp:

            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")

            filename = os.path.basename(str(resp.url).split("?")[0])

            if not filename:
                filename = "video.mp4"

            filepath = os.path.join(DOWNLOAD_DIR, filename)

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_percent = 0

            with open(filepath, "wb") as f:

                while True:

                    chunk = await resp.content.read(CHUNK_SIZE)

                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)

                    if total and progress_callback:

                        percent = downloaded / total * 100

                        if percent - last_percent >= 5:
                            last_percent = percent
                            await progress_callback(percent)

    if progress_callback:
        await progress_callback(100)

    return filepath


# =====================================================
# DOWNLOAD COM YT-DLP (SITES / M3U8)
# =====================================================

async def download_with_ytdlp(url, progress_callback=None):

    loop = asyncio.get_event_loop()

    filename = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": filename,
        "noplaylist": True,
        "concurrent_fragment_downloads": 5,
        "retries": 10,
        "fragment_retries": 10,
        "quiet": True,
    }

    def run():

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            return ydl.prepare_filename(info)

    file_path = await loop.run_in_executor(None, run)

    if progress_callback:
        await progress_callback(100)

    return file_path


# =====================================================
# DETECTAR LINKS DE VÍDEO EM PÁGINA
# =====================================================

async def extract_video_links(page_url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        async with session.get(page_url) as resp:

            text = await resp.text()

    links = re.findall(r'https?://[^\s"\']+\.(?:mp4|mkv|m3u8)', text)

    return links


# =====================================================
# DETECTAR PASTA DE EPISÓDIOS
# =====================================================

async def extract_folder_links(folder_url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        async with session.get(folder_url) as resp:

            html = await resp.text()

    links = re.findall(r'href="([^"]+)"', html)

    videos = []

    for link in links:

        if any(link.endswith(ext) for ext in [".mp4", ".mkv", ".m3u8"]):

            if not link.startswith("http"):
                link = urljoin(folder_url, link)

            videos.append(link)

    # ordenar episódios
    videos.sort(key=lambda x: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', x)])

    return videos


# =====================================================
# PROCESSAR LINK UNIVERSAL
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # link direto
    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)

    # possível pasta
    if url.endswith("/"):

        videos = await extract_folder_links(url)

        if videos:

            files = []

            for video in videos:

                filepath = await download_direct(video, progress_callback)

                files.append(filepath)

            return files

    # tentar detectar vídeo na página
    links = await extract_video_links(url)

    if links:

        return await download_direct(links[0], progress_callback)

    # fallback yt-dlp
    return await download_with_ytdlp(url, progress_callback)
