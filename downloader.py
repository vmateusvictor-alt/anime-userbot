import os
import asyncio
import aiohttp

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 4 * 1024 * 1024

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive",
}


# =====================================================
# DOWNLOAD MP4 DIRETO (COM HEADERS + RETRY)
# =====================================================

async def download_mp4(url, progress_callback=None):

    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".mp4"):
        filename += ".mp4"

    output_path = os.path.join(DOWNLOAD_DIR, filename)

    timeout = aiohttp.ClientTimeout(total=None)

    for attempt in range(3):  # retry automático
        try:
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
                                if percent - last_percent >= 10:
                                    last_percent = percent
                                    await progress_callback(percent)

            return output_path

        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(2)


# =====================================================
# DOWNLOAD M3U8 (MELHORADO)
# =====================================================

async def download_m3u8(url, progress_callback=None):

    output_path = os.path.join(DOWNLOAD_DIR, "video.mp4")

    cmd = [
        "ffmpeg",
        "-user_agent", HEADERS["User-Agent"],
        "-headers", "Referer: {}\r\n".format(url),
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
# DOWNLOAD UNIVERSAL (VERSÃO BLINDADA)
# =====================================================

async def download_universal(url, progress_callback=None):

    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--force-overwrites",
        "--no-check-certificate",
        "--no-warnings",
        "--retries", "5",
        "--fragment-retries", "5",
        "--retry-sleep", "2",
        "--concurrent-fragments", "4",
        "--user-agent", HEADERS["User-Agent"],
        "--add-header", f"Referer:{url}",
        "--remux-video", "mp4",
        "--merge-output-format", "mp4",
        "-f", "bestvideo+bestaudio/best",
        "-o", output_path,
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
