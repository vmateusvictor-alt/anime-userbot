import os
import asyncio
import json
import time


# =====================================================
# PEGAR METADATA REAL
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

    try:
        raw_duration = data.get("format", {}).get("duration", 0)
        if raw_duration and raw_duration != "N/A":
            duration = int(float(raw_duration))
    except:
        duration = 0

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = stream.get("width", 0) or 0
            height = stream.get("height", 0) or 0
            break

    return duration, width, height


# =====================================================
# GERAR THUMB
# =====================================================

async def generate_thumbnail(filepath):

    thumb_path = filepath + ".jpg"

    cmd = (
        f'ffmpeg -ss 00:00:05 -i "{filepath}" '
        f'-vframes 1 -vf "scale=320:-1" -q:v 3 "{thumb_path}" -y'
    )

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )

    await process.communicate()

    if os.path.exists(thumb_path):
        return thumb_path

    return None


# =====================================================
# UPLOAD COMPLETO COM INFO
# =====================================================

import os

async def upload_video(userbot, filepath, message, storage_chat_id):

    await message.edit_text("📤 Preparando vídeo...")

    duration, width, height = await get_video_metadata(filepath)
    thumb = await generate_thumbnail(filepath)

    file_name = os.path.basename(filepath)

    # 🔥 Remove duplicação .mp4.mp4
    if file_name.endswith(".mp4.mp4"):
        file_name = file_name.replace(".mp4.mp4", ".mp4")

    # 🔥 Remove extensão da legenda (opcional)
    caption_name = file_name.rsplit(".", 1)[0]

    sent = await userbot.send_video(
        chat_id=storage_chat_id,
        video=filepath,
        duration=duration,
        width=width,
        height=height,
        thumb=thumb,
        file_name=file_name,
        caption=f"🎬 {caption_name}",
        supports_streaming=True
    )

    if thumb and os.path.exists(thumb):
        os.remove(thumb)

    return sent.id
