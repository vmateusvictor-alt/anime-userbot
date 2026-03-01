import os
import asyncio
import time


# =====================================================
# GERAR THUMB
# =====================================================

async def generate_thumbnail(filepath):
    thumb_path = filepath + ".jpg"

    cmd = (
        f'ffmpeg -ss 00:00:08 -i "{filepath}" '
        f'-vframes 1 -vf "scale=320:-1" -q:v 3 "{thumb_path}" -y'
    )

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )

    await process.communicate()

    if os.path.exists(thumb_path):
        return thumb_path

    return None


# =====================================================
# UPLOAD MTProto OTIMIZADO
# =====================================================

async def upload_video(userbot, filepath, message, storage_chat_id):

    await message.edit_text("📤 Preparando upload...")

    thumb = await generate_thumbnail(filepath)

    start_time = time.time()
    last_update = 0

    async def progress(current, total):
        nonlocal last_update

        now = time.time()

        if now - last_update > 4:
            last_update = now

            percent = current * 100 / total
            speed = current / (now - start_time) / 1024 / 1024

            try:
                await message.edit_text(
                    f"📤 Enviando vídeo...\n"
                    f"{percent:.1f}%\n"
                    f"⚡ {speed:.2f} MB/s"
                )
            except:
                pass

    sent = await userbot.send_video(
        chat_id=storage_chat_id,
        video=filepath,
        thumb=thumb,
        supports_streaming=True,
        file_name=os.path.basename(filepath),
        progress=progress
    )

    await message.edit_text("✅ Upload concluído!")

    if thumb and os.path.exists(thumb):
        os.remove(thumb)

    return sent.id
