import os
import time
import subprocess


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


async def upload_video(userbot, chat_id, filepath, message):

    filename = os.path.basename(filepath)
    thumb = generate_thumbnail(filepath)

    last_percent = 0
    last_edit_time = 0

    async def progress(current, total):
        nonlocal last_percent, last_edit_time

        percent = (current / total) * 100
        now = time.time()

        if percent - last_percent >= 3 or (now - last_edit_time) > 2:
            last_percent = percent
            last_edit_time = now

            bar = "█" * int(percent // 5)
            bar = bar.ljust(20, "░")

            try:
                await message.edit_text(
                    f"📤 Enviando...\n[{bar}] {percent:.2f}%"
                )
            except:
                pass

    await userbot.get_chat(chat_id)

    sent = await userbot.send_video(
        chat_id=chat_id,
        video=filepath,
        caption=filename,
        thumb=thumb,
        supports_streaming=True,
        file_name=filename,
        progress=progress
    )

    file_id = sent.video.file_id

    os.remove(thumb)

    return file_id
