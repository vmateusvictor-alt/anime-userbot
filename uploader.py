import os
import time

async def upload_video(userbot, chat_id, filepath, message):

    file_size = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

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

    # 🔥 IMPORTANTE: forçar conhecer o peer
    await userbot.get_chat(chat_id)

    await userbot.send_video(
        chat_id=chat_id,
        video=filepath,
        caption=filename,
        supports_streaming=True,
        file_name=filename,
        progress=progress
    )
