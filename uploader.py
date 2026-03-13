import os
import asyncio
import json
from telegram.error import RetryAfter, TimedOut, NetworkError

# =====================================================
# PEGAR METADATA REAL
# =====================================================
async def get_video_metadata(filepath):
    """
    Retorna: duration(int), width(int), height(int)
    Garante que duration seja int >=1
    """
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

    try:
        data = json.loads(stdout.decode())
    except json.JSONDecodeError:
        data = {}

    width = 0
    height = 0
    duration = 0

    stream = data.get("streams", [{}])[0]
    width = int(stream.get("width", 0) or 0)
    height = int(stream.get("height", 0) or 0)

    raw_duration = stream.get("duration")
    if raw_duration and raw_duration != "N/A":
        try:
            duration = max(1, int(float(raw_duration)))
        except:
            duration = 1  # fallback mínimo de 1s
    else:
        duration = 1

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
# UPLOAD COMPLETO COM THUMBNAIL E TEMPO CORRETO
# =====================================================
async def upload_video(userbot, filepath, message, storage_chat_id):
    await message.edit_text("📤 Preparando vídeo...")

    # Metadata + thumbnail em paralelo
    try:
        metadata_task = get_video_metadata(filepath)
        thumb_task = generate_thumbnail(filepath)
        duration, width, height = await metadata_task
        thumb = await thumb_task
    except Exception:
        duration, width, height, thumb = 1, 0, 0, None

    # Se thumbnail falhar, gerar novamente
    if not thumb or not os.path.exists(thumb):
        thumb = await generate_thumbnail(filepath)

    # Nome do arquivo
    file_name = os.path.basename(filepath)
    if file_name.endswith(".mp4.mp4"):
        file_name = file_name.replace(".mp4.mp4", ".mp4")
    caption_name = file_name.rsplit(".", 1)[0]

    # Upload com retries
    for attempt in range(3):
        try:
            sent = await userbot.send_video(
                chat_id=storage_chat_id,
                video=filepath,
                duration=duration,  # ⬅️ garante que seja int válido
                width=width,
                height=height,
                thumb=thumb,
                file_name=file_name,
                caption=f"🎬 {caption_name}",
                supports_streaming=True
            )
            break
        except (RetryAfter, TimedOut, NetworkError):
            await asyncio.sleep(5)
    else:
        raise Exception("❌ Upload falhou após 3 tentativas!")

    # Limpar thumbnail
    if thumb and os.path.exists(thumb):
        try:
            os.remove(thumb)
        except:
            pass

    await message.edit_text(f"✅ Upload concluído: {caption_name}")
    return sent.id
