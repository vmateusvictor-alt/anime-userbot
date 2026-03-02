import os
import re
import uuid
import asyncio
import aiohttp

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 8 * 1024 * 1024

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".webm", ".m3u8")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =====================================================
# ORDENAÇÃO NATURAL
# =====================================================

def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r'([0-9]+)', s)
    ]


# =====================================================
# DOWNLOAD DIRETO (ANTI HTML)
# =====================================================

async def download_direct(url, progress_callback=None):

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as resp:

            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")

            content_type = resp.headers.get("Content-Type", "").lower()

            if "text/html" in content_type:
                raise Exception("Resposta HTML detectada.")

            filename = None
            cd = resp.headers.get("Content-Disposition")

            if cd:
                match = re.findall('filename="?([^"]+)"?', cd)
                if match:
                    filename = match[0]

            if not filename:
                filename = os.path.basename(url.split("?")[0])

            if not filename or "." not in filename:
                filename = str(uuid.uuid4()) + ".mp4"

            output_path = os.path.join(DOWNLOAD_DIR, filename)

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_percent = 0

            with open(output_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total and progress_callback:
                        percent = (downloaded / total) * 100
                        if percent - last_percent >= 5:
                            last_percent = percent
                            await progress_callback(percent)

    if os.path.getsize(output_path) < 500_000:
        os.remove(output_path)
        raise Exception("Arquivo inválido ou bloqueado.")

    return output_path


# =====================================================
# DOWNLOAD M3U8
# =====================================================

async def download_m3u8(url):

    filename = str(uuid.uuid4()) + ".mp4"
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    cmd = [
        "ffmpeg",
        "-loglevel", "error",
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
# EXTRAIR LINKS DE PASTA HTML
# =====================================================

async def extract_folder_links(url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as resp:

            if resp.status != 200:
                return None

            html = await resp.text()

    links = re.findall(r'href="([^"]+)"', html)
    videos = []

    for link in links:
        if link.lower().endswith(VIDEO_EXTENSIONS):

            if not link.startswith("http"):
                link = url.rstrip("/") + "/" + link.lstrip("/")

            videos.append(link)

    if videos:
        videos.sort(key=natural_sort_key)
        return videos

    return None


# =====================================================
# DOWNLOAD VIA YT-DLP (UNIVERSAL)
# =====================================================

async def download_with_ytdlp(url):

    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "best",
        "--no-playlist",
        "--user-agent", "Mozilla/5.0",
        "--sleep-interval", "2",
        "--retries", "10",
        "-o", output_template,
        url
    ]

    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro ao extrair vídeo da página.")

    files = sorted(
        [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
        key=os.path.getctime
    )

    return files[-1]


# =====================================================
# FUNÇÃO PRINCIPAL
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # 1️⃣ M3U8 direto
    if url_lower.endswith(".m3u8"):
        return await download_m3u8(url)

    # 2️⃣ Arquivo direto
    if url_lower.endswith((".mp4", ".mkv", ".webm")):
        return await download_direct(url, progress_callback)

    # 3️⃣ Detectar pasta
    folder_links = await extract_folder_links(url)
    if folder_links:

        results = []

        for link in folder_links:
            result = await process_link(link, progress_callback)
            results.append(result)

        return results

    # 4️⃣ Tentar download direto via HEAD
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.head(url, allow_redirects=True) as resp:

                content_type = resp.headers.get("content-type", "")

                if "video" in content_type or "octet-stream" in content_type:
                    return await download_direct(url, progress_callback)

    except:
        pass

    # 5️⃣ Fallback universal (sites tipo anroll, drive, workers)
    return await download_with_ytdlp(url)
