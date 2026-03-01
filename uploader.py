import os
import subprocess

STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID")


# =====================================================
# PEGAR INFO COMPLETA DO VÍDEO
# =====================================================

def get_video_info(video_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format=duration:stream=width,height",
        "-of",
        "default=noprint_wrappers=1",
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    width = 1280
    height = 720
    duration = 0

    for line in result.stdout.splitlines():

        if line.startswith("width="):
            try:
                width = int(line.split("=")[1])
            except:
                pass

        elif line.startswith("height="):
            try:
                height = int(line.split("=")[1])
            except:
                pass

        elif line.startswith("duration="):
            value = line.split("=")[1]
            if value != "N/A":
                try:
                    duration = int(float(value))
                except:
                    duration = 0

    return width, height, duration


# =====================================================
# GERAR THUMB
# =====================================================

def generate_thumbnail(video_path):
    thumb_path = video_path + ".jpg"

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-ss", "00:00:05",
        "-vframes", "1",
        thumb_path,
        "-y"
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(thumb_path):
        return thumb_path

    return None


# =====================================================
# UPLOAD COM NOME + DURAÇÃO CORRETOS
# =====================================================

async def upload_video(userbot, filepath, message):

    width, height, duration = get_video_info(filepath)
    thumb = generate_thumbnail(filepath)

    # Nome real do arquivo
    file_name = os.path.basename(filepath)

    # Se duração falhar, tenta pegar manualmente
    if duration == 0:
        duration = 1  # evita 0:00

    sent = await userbot.send_video(
        chat_id=STORAGE_CHANNEL_ID,
        video=filepath,
        duration=duration,
        width=width,
        height=height,
        thumb=thumb,
        supports_streaming=True,
        file_name=file_name,
        caption=file_name
    )

    if thumb and os.path.exists(thumb):
        os.remove(thumb)

    return sent.id
