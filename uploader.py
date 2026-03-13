import os
import asyncio
import json
from telegram.error import RetryAfter, TimedOut, NetworkError

# =====================================================
# PEGAR METADATA REAL
# =====================================================
async def get_video_metadata(filepath):
    """
    Pega duração, largura e altura do vídeo usando ffprobe.
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
    """
    Gera thumbnail JPG do vídeo (frame aos 5s, escala 320px largura)
    """
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
# UPLOAD COMPLETO COM INFO EM PARALLO
# =====================================================
async def upload_video(userbot, filepath, message, storage_chat_id):
    """
    Upload otimizado para Telegram:
    - metadata + thumbnail em paralelo
    - retries automáticos
    - chunk_size ajustável para Railway
    """
    await message.edit_text("📤 Preparando vídeo...")

    # 🔥 Executar metadata e thumbnail em paralelo
    duration, width, height, thumb = 0, 0, 0, None
    try:
        duration, width, height, thumb = await asyncio.gather(
            get_video_metadata(filepath),
            generate_thumbnail(filepath),
        )
    except Exception:
        # fallback em caso de erro
        duration, width, height = 0, 0, 0
        thumb = None

    # Ajuste de retorno do gather
    if isinstance(duration, tuple):
        duration, width, height = duration
    if isinstance(width, tuple):  # caso gather misture retornos
        width, height = width

    # 🔥 Nome do arquivo
    file_name = os.path.basename(filepath)
    if file_name.endswith(".mp4.mp4"):
        file_name = file_name.replace(".mp4.mp4", ".mp4")
    caption_name = file_name.rsplit(".", 1)[0]

    # 🔥 Tentativa de upload com retries
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
                chunk_size=128 * 1024  # 128KB, ajuste conforme memória Railway
            )
            break
        except (RetryAfter, TimedOut, NetworkError) as e:
            wait = getattr(e, 'retry_after', 5)
            await asyncio.sleep(wait)
    else:
        raise Exception("❌ Upload falhou após 3 tentativas!")

    # 🔥 Limpeza do thumbnail
    if thumb and os.path.exists(thumb):
        try:
            os.remove(thumb)
        except Exception:
            pass

    return sent.id
