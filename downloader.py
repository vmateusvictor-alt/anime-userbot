import asyncio
import os
import subprocess
import re
from config import DOWNLOAD_DIR


def get_duration(url):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


async def download_m3u8(url, progress_callback=None):

    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".mp4"):
        filename = filename.replace(".m3u8", ".mp4")

    output_path = os.path.join(DOWNLOAD_DIR, filename)

    total_duration = get_duration(url)

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
            time_ms = int(line.split("=")[1])
            current_time = time_ms / 1_000_000
            percent = (current_time / total_duration) * 100

            if progress_callback:
                await progress_callback(percent)

    await process.wait()

    return output_path
