import os
import time
import subprocess

# ACEITA @username OU ID
storage_value = os.getenv("STORAGE_CHANNEL_ID")
if storage_value.startswith("@"):
    STORAGE_CHANNEL_ID = storage_value
else:
    STORAGE_CHANNEL_ID = int(storage_value)


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


async def upload_video(userbot, filepath, message):

    filename = os.path.basename(filepath)
    width, height, duration = get_video_info(filepath)

    last_percent = 0
    last_time = 0

    async def progress(current, total):
        nonlocal last_percent, last_time

        percent = (current / total) * 100
        now = time.time()

        if percent - last_percent >= 10 or (now - last_time) > 3:
            last_percent = percent
            last_time = now
            try:
                await message.edit_text(
                    f"📤 Enviando... {percent:.0f}%"
                )
            except:
                pass

    sent = await userbot.send_video(
        chat_id=STORAGE_CHANNEL_ID,
        video=filepath,
        caption=filename,
        duration=duration,
        width=width,
        height=height,
        supports_streaming=True,
        progress=progress
    )

    return sent.id
