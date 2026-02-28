import os
import subprocess

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


async def upload_video(userbot, filepath, message):

    width, height, duration = get_video_info(filepath)

    sent = await userbot.send_video(
        chat_id=STORAGE_CHANNEL_ID,
        video=filepath,
        duration=duration,
        width=width,
        height=height,
        supports_streaming=True
    )

    return sent.id
