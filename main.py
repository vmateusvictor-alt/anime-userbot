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
from downloader import process_link
from uploader import upload_video


# =====================================================
# USUÁRIOS AUTORIZADOS
# =====================================================

AUTHORIZED_USERS = set()

def load_authorized_users():
    try:
        with open("authorized_users.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    AUTHORIZED_USERS.add(int(line))
        print(f"✅ {len(AUTHORIZED_USERS)} usuários autorizados carregados.")
    except FileNotFoundError:
        print("⚠ authorized_users.txt não encontrado.")


def is_authorized(update: Update):
    user = update.effective_user
    if not user:
        return False
    return user.id in AUTHORIZED_USERS


# =====================================================
# VARIÁVEIS DE AMBIENTE
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
STORAGE_CHANNEL_RAW = os.getenv("STORAGE_CHANNEL_ID")

if STORAGE_CHANNEL_RAW.startswith("@"):
    STORAGE_CHANNEL_ID = STORAGE_CHANNEL_RAW
else:
    STORAGE_CHANNEL_ID = int(STORAGE_CHANNEL_RAW)

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
    no_updates=True,
    workers=1  # 🔥 apenas 1 worker MTProto
)


# =====================================================
# FILA GLOBAL
# =====================================================

download_queue = asyncio.Queue()
processing_lock = asyncio.Lock()


# =====================================================
# WORKER (NUNCA PARALELO)
# =====================================================

async def worker(app):

    while True:
        task = await download_queue.get()

        async with processing_lock:  # 🔥 garante 1 por vez

            task_id = task["id"]
            chat_id = task["chat_id"]
            url = task["url"]
            msg = task["message"]

            try:
                await msg.edit_text("📥 Iniciando download...")

                last_percent = 0

                async def progress(percent):
                    nonlocal last_percent
                    if percent - last_percent >= 10:
                        last_percent = percent
                        try:
                            await msg.edit_text(
                                f"📥 Baixando...\n{percent:.0f}%"
                            )
                        except:
                            pass

                result = await process_link(url, progress)

                # ===============================
                # SE FOR PASTA
                # ===============================

                if isinstance(result, list):

                    for filepath in result:

                        await msg.edit_text("📤 Enviando para o canal...")

                        message_id = await upload_video(
                            userbot=userbot,
                            filepath=filepath,
                            message=msg,
                            storage_chat_id=STORAGE_CHANNEL_ID
                        )

                        await app.bot.copy_message(
                            chat_id=chat_id,
                            from_chat_id=STORAGE_CHANNEL_ID,
                            message_id=message_id
                        )

                        if os.path.exists(filepath):
                            os.remove(filepath)

                    await msg.edit_text("✅ Pasta concluída!")

                # ===============================
                # ARQUIVO ÚNICO
                # ===============================

                else:

                    await msg.edit_text("📤 Enviando para o canal...")

                    message_id = await upload_video(
                        userbot=userbot,
                        filepath=result,
                        message=msg,
                        storage_chat_id=STORAGE_CHANNEL_ID
                    )

                    await app.bot.copy_message(
                        chat_id=chat_id,
                        from_chat_id=STORAGE_CHANNEL_ID,
                        message_id=message_id
                    )

                    if os.path.exists(result):
                        os.remove(result)

                    await msg.edit_text("✅ Concluído!")

            except Exception as e:
                await msg.edit_text(f"❌ Erro:\n{e}")

        download_queue.task_done()


# =====================================================
# COMANDO /an
# =====================================================

async def anime_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_authorized(update):
        await update.message.reply_text("❌ Você não está autorizado.")
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Funciona apenas em grupos.")
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
        f"📌 ID: {task_id}\n"
        f"📥 Posição na fila: {position}"
    )


# =====================================================
# START
# =====================================================

async def start_services(app):

    load_authorized_users()

    print("🔌 Iniciando userbot...")
    await userbot.start()

    print("⚙ Worker iniciado.")
    asyncio.create_task(worker(app))


# =====================================================
# MAIN
# =====================================================

def main():

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(start_services)
        .build()
    )

    app.add_handler(CommandHandler("an", anime_handler))

    print("🚀 Bot iniciado...")
    app.run_polling()


if __name__ == "__main__":
    main()
