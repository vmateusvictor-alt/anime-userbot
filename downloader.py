import os
import asyncio
import aiohttp
import re

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 4 * 1024 * 1024

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".m3u8")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================================
# LISTAR TODOS OS VÍDEOS DE UMA PASTA INDEX
# =====================================================

async def extract_all_videos_from_folder(url):

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception("Não foi possível acessar a pasta.")

            html = await resp.text()

    links = re.findall(r'href="([^"]+)"', html)

    video_links = []

    for link in links:
        if link.lower().endswith(VIDEO_EXTENSIONS):

            if not link.startswith("http"):
                if url.endswith("/"):
                    link = url + link
                else:
                    link = url + "/" + link

            video_links.append(link)

    if not video_links:
        raise Exception("Nenhum vídeo encontrado na pasta.")

    video_links.sort()
    return video_links


# =====================================================
# DOWNLOAD DIRETO (MP4 / MKV)
# =====================================================

async def download_direct(url, progress_callback=None):

    filename = url.split("/")[-1].split("?")[0]
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_percent = 0

            with open(output_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total and progress_callback:
                        percent = (downloaded / total) * 100
                        if percent - last_percent >= 15:
                            last_percent = percent
                            await progress_callback(percent)

    return output_path


# =====================================================
# DOWNLOAD M3U8 (FFMPEG)
# =====================================================

async def download_m3u8(url, progress_callback=None):

    filename = "video_" + str(asyncio.get_event_loop().time()).replace(".", "") + ".mp4"
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

    # ==========================================
    # SE FOR PASTA INDEX
    # ==========================================

    if url_lower.endswith("/"):

        video_links = await extract_all_videos_from_folder(url)

        results = []

        for video_url in video_links:

            result = await process_link(video_url, progress_callback)
            results.append(result)

        return results


    # ==========================================
    # ARQUIVOS DIRETOS
    # ==========================================

    if url_lower.endswith(".m3u8"):
        return await download_m3u8(url, progress_callback)

    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)


    # ==========================================
    # TENTA DETECTAR SE É PASTA HTML
    # ==========================================

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
                            result = await process_link(video_url, progress_callback)
                            results.append(result)

                        return results
    except:
        pass


    # ==========================================
    # FALLBACK UNIVERSAL (Drive, Streamtape etc)
    # ==========================================

    return await download_with_ytdlp(url)
