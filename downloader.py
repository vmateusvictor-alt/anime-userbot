import os
import asyncio
import aiohttp
import re
import uuid
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 4 * 1024 * 1024

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".m3u8")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 🔒 apenas 1 download por vez
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
# EXTRAIR VÍDEOS DE PASTA
# =====================================================

async def extract_all_videos_from_folder(url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception("Não foi possível acessar a pasta.")

            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")

    video_links = []

    for a in soup.find_all("a", href=True):

        href = a["href"]
        lower = href.lower()

        if any(ext in lower for ext in VIDEO_EXTENSIONS):

            full_link = urljoin(url, href)
            video_links.append(full_link)

    if not video_links:
        raise Exception("Nenhum vídeo encontrado na pasta.")

    video_links.sort(key=natural_sort_key)

    return video_links


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
                content_type = resp.headers.get("content-type", "")

                # Permite download.aspx mesmo se vier como HTML
                if "text/html" in content_type and "download.aspx" not in parsed.path:
                    raise Exception("Servidor retornou HTML inesperado.")

                # nome do arquivo
                filename = None
                cd = resp.headers.get("Content-Disposition")

                if cd:
                    match = re.findall('filename="?([^"]+)"?', cd)
                    if match:
                        filename = match[0]

                if not filename:
                    filename = os.path.basename(parsed.path)

                if not filename or "." not in filename:
                    filename = str(uuid.uuid4()) + ".mp4"

                filepath = os.path.join(DOWNLOAD_DIR, filename)

                total = int(resp.headers.get("content-length", 0) or 0)
                downloaded = 0
                last_percent = 0

                with open(filepath, "wb") as f:

                    async for chunk in resp.content.iter_chunked(2 * 1024 * 1024):

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
        output_path = os.path.join(DOWNLOAD_DIR, filename)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        await process.wait()

        if process.returncode != 0:
            raise Exception("Erro ao converter m3u8.")

        return output_path


# =====================================================
# DOWNLOAD YT-DLP
# =====================================================

async def download_with_ytdlp(url):

    async with DOWNLOAD_LOCK:

        output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-o",
            output_template,
            url
        ]

        process = await asyncio.create_subprocess_exec(*cmd)

        await process.wait()

        if process.returncode != 0:
            raise Exception("Erro ao baixar com yt-dlp.")

        files = sorted(
            [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
            key=os.path.getctime
        )

        if not files:
            raise Exception("yt-dlp não gerou arquivo.")

        return files[-1]


# =====================================================
# PROCESSADOR PRINCIPAL
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # =====================================================
    # ANIMEFIRE → usa yt-dlp
    # =====================================================

    if "animefire" in url_lower:
        return await download_with_ytdlp(url)

    # =====================================================
    # M3U8
    # =====================================================

    if url_lower.endswith(".m3u8"):
        return await download_m3u8(url)

    # =====================================================
    # MP4 / MKV
    # =====================================================

    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)

    # =====================================================
    # TESTE HTML (pasta)
    # =====================================================

    try:

        async with aiohttp.ClientSession(headers=HEADERS) as session:

            async with session.get(url) as resp:

                content_type = resp.headers.get("content-type", "")

                if "text/html" in content_type:

                    html = await resp.text()

                    if any(ext in html.lower() for ext in VIDEO_EXTENSIONS):

                        video_links = await extract_all_videos_from_folder(url)

                        results = []

                        for video_url in video_links:

                            result = await process_link(
                                video_url,
                                progress_callback
                            )

                            results.append(result)

                        return results

    except:
        pass

    # =====================================================
    # FALLBACK
    # =====================================================

    return await download_with_ytdlp(url)
