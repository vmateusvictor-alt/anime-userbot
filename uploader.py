import os
import time
import asyncio
import subprocess
from pyrogram.errors import FloodWait

STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID")


def get_video_info(video_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "default=noprint_wrappers=1",
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    width = 1280
    height = 720
    duration = 0

    for line in result.stdout.splitlines():
        if line.startswith("width="):
            width = int(line.split("=")[1])
        elif line.startswith("height="):
            height = int(line.split("=")[1])
        elif line.startswith("duration="):
            duration = int(float(line.split("=")[1]))

    return width, height, duration


def generate_thumbnail(video_path):
    thumb_path = video_path + ".jpg"

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-ss", "00:00:03",
        "-vframes", "1",
        thumb_path,
        "-y"
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return thumb_path


async def upload_video(userbot, filepath, message):

    width, height, duration = get_video_info(filepath)
    thumb = generate_thumbnail(filepath)

    last_percent = 0
    last_time = 0

    async def progress(current, total):
        nonlocal last_percent, last_time

        percent = (current / total) * 100
        now = time.time()

        # Atualiza apenas se passou 5% OU 3 segundos
        if percent - last_percent < 5 and now - last_time < 3:
            return

        last_percent = percent
        last_time = now

        bar = "█" * int(percent // 5)
        bar = bar.ljust(20, "░")

        try:
            await message.edit_text(
                f"📤 Enviando...\n[{bar}] {percent:.2f}%"
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            pass

    sent = await userbot.send_video(
        chat_id=STORAGE_CHANNEL_ID,
        video=filepath,
        duration=duration,
        width=width,
        height=height,
        thumb=thumb,
        supports_streaming=True,
        progress=progress
    )

    if os.path.exists(thumb):
        os.remove(thumb)

    return sent.id
