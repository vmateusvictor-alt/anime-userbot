import os
import asyncio
import uuid
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
from pyrogram import Client
from downloader import download_mp4, download_m3u8, download_universal
from uploader import upload_video

# =====================================================
# VARIÁVEIS
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================================
# USERBOT
# =====================================================

userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    no_updates=True
)

# =====================================================
# FILA GLOBAL
# =====================================================

download_queue = asyncio.Queue()
active_tasks = {}

# =====================================================
# WORKER
# =====================================================

async def worker(app):

    while True:
        task = await download_queue.get()

        task_id = task["id"]
        chat_id = task["chat_id"]
        url = task["url"]
        msg = task["message"]

        active_tasks[task_id] = task

        try:

            await msg.edit_text("📥 Iniciando download...")

            last_percent = 0

            async def progress(percent):
                nonlocal last_percent

                if percent - last_percent >= 2:
                    last_percent = percent
                    bar = "█" * int(percent // 5)
                    bar = bar.ljust(20, "░")
                    try:
                        await msg.edit_text(
                            f"📥 Baixando...\n[{bar}] {percent:.2f}%"
                        )
                    except:
                        pass

            url_lower = url.lower()

            if ".m3u8" in url_lower:
                filepath = await download_m3u8(url, progress)
            elif url_lower.endswith(".mp4"):
                filepath = await download_mp4(url, progress)
            else:
                await msg.edit_text("🔎 Detectando fonte...")
                filepath = await download_universal(url, progress)

            await msg.edit_text("📤 Enviando para Telegram...")

            message_id = await upload_video(
                userbot=userbot,
                filepath=filepath,
                message=msg
            )

            await app.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=message_id
            )

            if os.path.exists(filepath):
                os.remove(filepath)

            await msg.edit_text("✅ Concluído!")

        except Exception as e:
            await msg.edit_text(f"❌ Erro:\n{e}")

        finally:
            active_tasks.pop(task_id, None)
            download_queue.task_done()

# =====================================================
# COMANDO /an (APENAS GRUPOS)
# =====================================================

async def anime_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "❌ Este bot funciona apenas em grupos."
        )
        return

    if not context.args:
        await update.message.reply_text("Use:\n/an link")
        return

    url = context.args[0]

    msg = await update.message.reply_text("📥 Adicionado à fila...")

    task_id = str(uuid.uuid4())[:8]

    task = {
        "id": task_id,
        "chat_id": update.effective_chat.id,
        "url": url,
        "message": msg
    }

    await download_queue.put(task)

    position = download_queue.qsize()

    await msg.edit_text(
        f"📌 Tarefa ID: {task_id}\n"
        f"📥 Posição na fila: {position}"
    )

# =====================================================
# CANCELAR TAREFA
# =====================================================

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Use:\n/cancel ID")
        return

    task_id = context.args[0]

    # Cancelar tarefa ativa
    if task_id in active_tasks:
        await update.message.reply_text(
            "⚠️ Não é possível cancelar tarefa em execução."
        )
        return

    # Remover da fila
    new_queue = asyncio.Queue()

    cancelled = False

    while not download_queue.empty():
        task = await download_queue.get()
        if task["id"] == task_id:
            cancelled = True
            download_queue.task_done()
            continue
        await new_queue.put(task)
        download_queue.task_done()

    download_queue._queue = new_queue._queue

    if cancelled:
        await update.message.reply_text("✅ Tarefa cancelada.")
    else:
        await update.message.reply_text("❌ ID não encontrado.")

# =====================================================
# START USERBOT
# =====================================================

async def start_userbot(app):
    if not userbot.is_connected:
        await userbot.start()

    asyncio.create_task(worker(app))

# =====================================================
# MAIN
# =====================================================

def main():

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(start_userbot)
        .build()
    )

    app.add_handler(CommandHandler("an", anime_handler))
    app.add_handler(CommandHandler("cancel", cancel_handler))

    print("Bot iniciado com fila avançada...")
    app.run_polling()

if __name__ == "__main__":
    main()
