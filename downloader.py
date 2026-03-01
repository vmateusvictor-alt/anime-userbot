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


# =====================================================
# LISTAR TODOS OS VÍDEOS DA PASTA
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

    # ordena alfabeticamente
    video_links.sort()
    return video_links


# =====================================================
# DOWNLOAD DIRETO
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
# DOWNLOAD M3U8
# =====================================================

async def download_m3u8(url):

    filename = "video.mp4"
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
# PROCESSAR LINK (ARQUIVO OU PASTA)
# =====================================================

async def process_link(url, progress_callback=None):

    url_lower = url.lower()

    # SE FOR PASTA
    if url_lower.endswith("/") or not url_lower.endswith(VIDEO_EXTENSIONS):

        try:
            video_links = await extract_all_videos_from_folder(url)

            results = []

            for video_url in video_links:
                path = await process_link(video_url, progress_callback)
                results.append(path)

            return results

        except:
            pass

    # ARQUIVO INDIVIDUAL

    if url_lower.endswith(".m3u8"):
        return await download_m3u8(url)

    if url_lower.endswith((".mp4", ".mkv")):
        return await download_direct(url, progress_callback)

    raise Exception("Formato não suportado.")
