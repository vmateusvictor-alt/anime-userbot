import os
import asyncio
import json
from pyrogram.types import Video

# =====================================================
# PEGAR METADATA COM FFMPEG
# =====================================================

async def get_video_metadata(filepath):

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        filepath
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, _ = await process.communicate()

    data = json.loads(stdout.decode())

    duration = 0
    width = 0
    height = 0

    # duration
    try:
        raw_duration = data.get("format", {}).get("duration", 0)

        if raw_duration and raw_duration != "N/A":
            duration = int(float(raw_duration))
        else:
            duration = 0
    except:
        duration = 0

    # video stream
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = stream.get("width", 0) or 0
            height = stream.get("height", 0) or 0
            break

    return duration, width, height


# =====================================================
# UPLOAD VIDEO
# =====================================================

async def upload_video(userbot, filepath, message):

    duration, width, height = await get_video_metadata(filepath)

    async def progress(current, total):
        try:
            percent = current * 100 / total
            await message.edit_text(f"📤 Enviando... {percent:.0f}%")
        except:
            pass

    sent = await userbot.send_video(
        chat_id=message.chat.id,  # envia primeiro no canal depois copy
        video=filepath,
        duration=duration,
        width=width,
        height=height,
        supports_streaming=True,
        progress=progress
    )

    return sent.id
