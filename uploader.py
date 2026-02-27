import os

async def upload_video(userbot, chat_id, filepath, message):

    thumb = filepath.replace(".mp4", ".jpg")

    from utils import generate_thumbnail
    generate_thumbnail(filepath, thumb)

    async def progress(current, total):
        percent = current * 100 / total
        await message.edit_text(f"📤 Enviando: {percent:.2f}%")

    await userbot.send_video(
        chat_id=chat_id,
        video=filepath,
        thumb=thumb,
        caption=os.path.basename(filepath),
        supports_streaming=True,
        progress=progress
    )

    os.remove(filepath)
    if os.path.exists(thumb):
        os.remove(thumb)
