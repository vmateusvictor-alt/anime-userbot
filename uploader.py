import os
import asyncio
import json
from telegram.error import RetryAfter, TimedOut, NetworkError

# =====================================================
# PEGAR METADATA REAL
# =====================================================
async def get_video_metadata(filepath):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "json",
        filepath
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    data = json.loads(stdout.decode() or "{}")
    stream = data.get("streams", [{}])[0]

    width = int(stream.get("width", 0) or 0)
    height = int(stream.get("height", 0) or 0)
    duration = int(float(stream.get("duration", 0) or 0))
    return duration, width, height

# =====================================================
# GERAR THUMB
# =====================================================
async def generate_thumbnail(filepath):
    thumb_path = filepath + ".jpg"
    cmd = [
        "ffmpeg",
        "-ss", "00:00:05",
        "-i", filepath,
        "-vframes", "1",
        "-vf", "scale=320:-1",
        "-q:v", "3",
        thumb_path,
        "-y"
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await process.communicate()
    return thumb_path if os.path.exists(thumb_path) else None

# =====================================================
# FUNÇÃO DE PROGRESSO
# =====================================================
async def progress_callback(current, total, message):
    percent = int(current / total * 100)
    if percent % 5 == 0 or current == total:
        try:
            await message.edit_text(f"📤 Upload: {percent}% ({current/1024/1024:.2f}/{total/1024/1024:.2f} MB)")
        except Exception:
            pass

# =====================================================
# UPLOAD PARA USERBOT TELEGRAM
# =====================================================
async def upload_video(userbot, filepath, message, storage_chat_id):
    await message.edit_text("📤 Preparando vídeo...")

    # Metadata + Thumbnail em paralelo
    try:
        metadata_task = get_video_metadata(filepath)
        thumb_task = generate_thumbnail(filepath)
        duration, width, height = await metadata_task
        thumb = await thumb_task
    except Exception:
        duration, width, height, thumb = 0, 0, 0, None

    file_name = os.path.basename(filepath)
    if file_name.endswith(".mp4.mp4"):
        file_name = file_name.replace(".mp4.mp4", ".mp4")
    caption_name = file_name.rsplit(".", 1)[0]

    # Upload com retries e progresso
    for attempt in range(3):
        try:
            sent = await userbot.send_video(
                chat_id=storage_chat_id,
                video=filepath,
                duration=duration,
                width=width,
                height=height,
                thumb=thumb,
                file_name=file_name,
                caption=f"🎬 {caption_name}",
                supports_streaming=True,
                progress=lambda current, total: asyncio.create_task(progress_callback(current, total, message))
            )
            break
        except (RetryAfter, TimedOut, NetworkError) as e:
            wait = getattr(e, 'retry_after', 5)
            await asyncio.sleep(wait)
    else:
        raise Exception("❌ Upload falhou após 3 tentativas!")

    if thumb and os.path.exists(thumb):
        try:
            os.remove(thumb)
        except Exception:
            pass

    await message.edit_text(f"✅ Upload concluído: {caption_name}")
    return sent.id
