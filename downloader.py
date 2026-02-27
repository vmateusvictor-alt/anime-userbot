import asyncio
import os
from config import DOWNLOAD_DIR

async def download_m3u8(url, progress_callback=None):

    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".mp4"):
        filename = filename.replace(".m3u8", ".mp4")

    output_path = os.path.join(DOWNLOAD_DIR, filename)

    cmd = [
        "ffmpeg",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-progress", "pipe:1",
        "-y",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        line = line.decode().strip()

        if "out_time_ms=" in line:
            if progress_callback:
                await progress_callback()

    await process.wait()

    return output_path
