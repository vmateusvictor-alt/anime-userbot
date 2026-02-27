import os
import time
from pyrogram import Client

# ⚠️ ENV NECESSÁRIAS:
# API_ID
# API_HASH
# SESSION_STRING

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_string = os.getenv("SESSION_STRING")

userbot = Client(
    "userbot",
    api_id=api_id,
    api_hash=api_hash,
    session_string=session_string
)


async def upload_video(chat_id, filepath, message):

    await userbot.start()

    file_size = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    last_percent = 0
    last_edit_time = 0

    async def progress(current, total):
        nonlocal last_percent, last_edit_time

        percent = (current / total) * 100
        now = time.time()

        # 🔥 Atualiza apenas a cada 3% ou 2 segundos
        if percent - last_percent >= 3 or (now - last_edit_time) > 2:
            last_percent = percent
            last_edit_time = now

            bar = "█" * int(percent // 5)
            bar = bar.ljust(20, "░")

            try:
                await message.edit_text(
                    f"📤 Enviando...\n"
                    f"[{bar}] {percent:.2f}%"
                )
            except:
                pass

    await userbot.send_video(
        chat_id=chat_id,
        video=filepath,
        caption=filename,
        supports_streaming=True,
        file_name=filename,
        progress=progress
    )

    await userbot.stop()
