import os
import asyncio

async def upload_video(userbot, filepath, message):

    async def progress(current, total):
        percent = (current / total) * 100
        bar = "█" * int(percent // 5)
        bar = bar.ljust(20, "░")

        try:
            await message.edit_text(
                f"📤 Enviando...\n[{bar}] {percent:.2f}%"
            )
        except:
            pass

    msg = await userbot.send_video(
        chat_id=os.getenv("STORAGE_CHANNEL_ID"),
        video=filepath,
        supports_streaming=True,
        progress=progress
    )

    return msg.id
