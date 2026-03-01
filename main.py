import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from pyrogram import Client
from downloader import process_link
from uploader import upload_video

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

storage_value = os.getenv("STORAGE_CHANNEL_ID")

if storage_value.startswith("@"):
    STORAGE_CHANNEL_ID = storage_value
else:
    STORAGE_CHANNEL_ID = int(storage_value)

DOWNLOAD_DIR = "downloads"
AUTHORIZED_FILE = "authorized_users.txt"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================================
# CARREGAR USUÁRIOS AUTORIZADOS
# =====================================================

def load_authorized_users():
    if not os.path.exists(AUTHORIZED_FILE):
        return set()

    with open(AUTHORIZED_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())

AUTHORIZED_USERS = load_authorized_users()

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
# FILA GLOBAL (1 POR VEZ)
# =====================================================

download_queue = asyncio.Queue()

# =====================================================
# WORKER
# =====================================================

async def worker(app):

    while True:
        task = await download_queue.get()

        chat_id = task["chat_id"]
        url = task["url"]
        msg = task["message"]

        try:
            await msg.edit_text("📥 Iniciando download...")

            last_update = 0

            async def progress(percent):
                nonlocal last_update
                if percent - last_update >= 15:
                    last_update = percent
                    try:
                        await msg.edit_text(f"📥 Baixando... {percent:.0f}%")
                    except:
                        pass

            result = await process_link(url, progress)

            # ==========================================
            # SE FOR PASTA (lista de arquivos)
            # ==========================================

            if isinstance(result, list):

                for filepath in result:

                    await msg.edit_text("📤 Enviando para o canal...")

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

                await msg.edit_text("✅ Pasta concluída!")

            # ==========================================
            # ARQUIVO ÚNICO
            # ==========================================

            else:

                await msg.edit_text("📤 Enviando para o canal...")

                message_id = await upload_video(
                    userbot=userbot,
                    filepath=result,
                    message=msg
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

        finally:
            download_queue.task_done()

# =====================================================
# COMANDO /an
# =====================================================

async def anime_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Apenas grupos.")
        return

    user_id = update.effective_user.id

    if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("⛔ Você não está autorizado.")
        return

    if not context.args:
        await update.message.reply_text("Use:\n/an link")
        return

    url = context.args[0]

    msg = await update.message.reply_text("📥 Adicionado à fila...")

    task = {
        "chat_id": update.effective_chat.id,
        "url": url,
        "message": msg
    }

    await download_queue.put(task)

    position = download_queue.qsize()

    await msg.edit_text(f"📥 Posição na fila: {position}")

# =====================================================
# START
# =====================================================

async def start_bot(app):

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
        .post_init(start_bot)
        .build()
    )

    app.add_handler(CommandHandler("an", anime_handler))

    print("🚀 Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
