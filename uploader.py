import os
import subprocess

STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID")


# =====================================================
# PEGAR INFO DO VÍDEO (SEGURO CONTRA N/A)
# =====================================================

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
# GERAR CAPA AUTOMÁTICA
# =====================================================

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

    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    if os.path.exists(thumb_path):
        return thumb_path

    return None


# =====================================================
# UPLOAD STREAMING
# =====================================================

async def upload_video(userbot, filepath, message):

    width, height, duration = get_video_info(filepath)
    thumb = generate_thumbnail(filepath)

    sent = await userbot.send_video(
        chat_id=STORAGE_CHANNEL_ID,
        video=filepath,
        duration=duration,
        width=width,
        height=height,
        thumb=thumb,
        supports_streaming=True
    )

    # Remove thumbnail
    if thumb and os.path.exists(thumb):
        os.remove(thumb)

    return sent.id
