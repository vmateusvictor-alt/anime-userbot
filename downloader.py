import os
import re
import json
import uuid
import asyncio
import aiohttp

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 8 * 1024 * 1024  # 🔥 mais rápido

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".webm")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =========================================================
# ORDENAÇÃO NATURAL (Ep 1, Ep 2, Ep 10)
# =========================================================

def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r'([0-9]+)', s)
    ]


# =========================================================
# DOWNLOAD DIRETO OTIMIZADO + PROGRESSO REAL
# =========================================================

async def download_direct(url, progress_callback=None):

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as resp:

            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")

            content_type = resp.headers.get("Content-Type", "").lower()

            if "text/html" in content_type:
                raise Exception("Servidor retornou HTML.")

            filename = None

            cd = resp.headers.get("Content-Disposition")
            if cd:
                match = re.search('filename="?(.+?)"?$', cd)
                if match:
                    filename = match.group(1)

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

                    if total > 0 and progress_callback:
                        percent = (downloaded / total) * 100
                        if percent - last_percent >= 2:  # 🔥 atualiza mais suave
                            last_percent = percent
                            await progress_callback(percent)

    if os.path.getsize(output_path) < 500_000:
        os.remove(output_path)
        raise Exception("Arquivo inválido ou bloqueado.")

    return output_path


# =========================================================
# DOWNLOAD M3U8
# =========================================================

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


# =========================================================
# DETECTA LINKS DE PASTA
# =========================================================

async def detect_folder_links(url):

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
        async with session.get(url) as resp:

            if resp.status != 200:
                return None

            text = await resp.text()

            links = re.findall(r'href="([^"]+)"', text)

            video_links = []

            for link in links:
                if any(ext in link.lower() for ext in VIDEO_EXTENSIONS):
                    if not link.startswith("http"):
                        link = url.rstrip("/") + "/" + link.lstrip("/")
                    video_links.append(link)

            if video_links:
                video_links.sort(key=natural_sort_key)
                return video_links

    return None


# =========================================================
# PROCESSADOR UNIVERSAL
# =========================================================

async def process_link(url, progress_callback=None):

    # ==========================================
    # 1️⃣ FORÇA yt-dlp PARA LINKS download.aspx
    # ==========================================

    if "download.aspx" in url or "workers.dev" in url:

        cmd = [
            "yt-dlp",
            "-o", os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "--add-header", "User-Agent: Mozilla/5.0",
            "--add-header", f"Referer: {url}",
            url
        ]

        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()

        if process.returncode != 0:
            raise Exception("Erro ao baixar link protegido.")

        files = sorted(
            [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
            key=os.path.getctime
        )

        return files[-1]

    # ==========================================
    # 2️⃣ DETECTA PASTA
    # ==========================================

    folder_links = await detect_folder_links(url)
    if folder_links:

        results = []

        for link in folder_links:
            result = await process_link(link, progress_callback)
            results.append(result)

        return results

    # ==========================================
    # 3️⃣ M3U8
    # ==========================================

    if ".m3u8" in url.lower():
        return await download_m3u8(url)

    # ==========================================
    # 4️⃣ DOWNLOAD DIRETO NORMAL
    # ==========================================

    try:
        return await download_direct(url, progress_callback)
    except Exception:
        pass

    # ==========================================
    # 5️⃣ FALLBACK yt-dlp NORMAL
    # ==========================================

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-o", os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
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

    return files[-1]
