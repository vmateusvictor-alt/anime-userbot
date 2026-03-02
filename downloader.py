import os
import asyncio
import aiohttp
import re
import uuid

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 4 * 1024 * 1024
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".m3u8")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*"
}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =====================================================
# ORDENAÇÃO NATURAL (ep1, ep2, ep10 correto)
# =====================================================

def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r'([0-9]+)', s)
    ]


# =====================================================
# EXTRAIR VÍDEOS DE PASTA HTML
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # ============================
    # 1️⃣ EXTENSÃO DIRETA
    # ============================

    if url_lower.endswith(".m3u8"):
        return await download_m3u8(url, progress_callback)

    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)

    # ============================
    # 2️⃣ TENTAR LISTAR COM YT-DLP
    # ============================

    try:
        import json

        cmd = [
            "yt-dlp",
            "-J",  # JSON only
            "--flat-playlist",
            url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0 and stdout:

            data = json.loads(stdout.decode())

            entries = data.get("entries")

            if entries:

                video_urls = []

                for entry in entries:
                    entry_url = entry.get("url")
                    if entry_url:
                        video_urls.append(entry_url)

                if video_urls:
                    video_urls.sort(key=natural_sort_key)

                    results = []

                    for video_url in video_urls:
                        result = await process_link(video_url, progress_callback)
                        results.append(result)

                    return results

    except Exception:
        pass

    # ============================
    # 3️⃣ TENTAR DOWNLOAD DIRETO
    # ============================

    try:
        return await download_direct(url, progress_callback)
    except:
        pass

    # ============================
    # 4️⃣ FALLBACK YT-DLP NORMAL
    # ============================

    return await download_with_ytdlp(url)

        # ================================
        # 🔥 FALLBACK HTML SIMPLES
        # ================================
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception("Não foi possível acessar a pasta.")

            html = await resp.text()

        links = re.findall(r'href="([^"]+)"', html)
        video_links = []

        for link in links:
            if any(link.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):

                if not link.startswith("http"):
                    link = url.rstrip("/") + "/" + link.lstrip("/")

                video_links.append(link)

        if not video_links:
            raise Exception("Nenhum vídeo encontrado na pasta.")

        video_links.sort(key=natural_sort_key)

        return video_links

# =====================================================
# DOWNLOAD DIRETO (MP4 / MKV)
# =====================================================

async def download_direct(url, progress_callback=None):

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as resp:

            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")

            filename = None
            content_disposition = resp.headers.get("Content-Disposition")

            if content_disposition:
                match = re.findall('filename="?([^"]+)"?', content_disposition)
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
                        if percent - last_percent >= 10:
                            last_percent = percent
                            await progress_callback(percent)

    return output_path


# =====================================================
# DOWNLOAD M3U8 (FFMPEG)
# =====================================================

async def download_m3u8(url, progress_callback=None):

    filename = str(uuid.uuid4()) + ".mp4"
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    cmd = [
        "ffmpeg",
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
# FALLBACK UNIVERSAL (YT-DLP)
# =====================================================

async def download_with_ytdlp(url):

    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-o", output_template,
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


# =====================================================
# FUNÇÃO PRINCIPAL
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # EXTENSÃO DIRETA
    if url_lower.endswith(".m3u8"):
        return await download_m3u8(url, progress_callback)

    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)

    # TESTAR HEAD
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.head(url, allow_redirects=True) as resp:

                content_type = resp.headers.get("content-type", "")
                content_disp = resp.headers.get("content-disposition", "")

                if (
                    "video" in content_type
                    or "octet-stream" in content_type
                    or "attachment" in content_disp
                ):
                    return await download_direct(url, progress_callback)

    except:
        pass

    # 🔥 SE FOR HTML → SEMPRE TENTAR COMO PASTA
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as resp:

                content_type = resp.headers.get("content-type", "")

                if "text/html" in content_type:

                    video_links = await extract_all_videos_from_folder(url)

                    if video_links:
                        results = []

                        # 🔥 BAIXA UM POR VEZ EM ORDEM
                        for video_url in video_links:
                            result = await process_link(video_url, progress_callback)
                            results.append(result)

                        return results

    except:
        pass

    # FALLBACK (somente se realmente não for pasta)
    return await download_with_ytdlp(url)
