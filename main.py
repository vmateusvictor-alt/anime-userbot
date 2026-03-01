import os
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from downloader import process_link
from uploader import upload_video

# ==============================
# CONFIG
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
STORAGE_CHANNEL = os.getenv("STORAGE_CHANNEL")  # @canalusername
AUTHORIZED_FILE = "authorized_users.txt"

DOWNLOAD_QUEUE = asyncio.Queue()
IS_PROCESSING = False

logging.basicConfig(level=logging.INFO)


# ==============================
# USUÁRIOS AUTORIZADOS
# ==============================

def load_authorized_users():
    if not os.path.exists(AUTHORIZED_FILE):
        return set()
    with open(AUTHORIZED_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())


def save_authorized_user(user_id):
    with open(AUTHORIZED_FILE, "a") as f:
        f.write(f"{user_id}\n")


AUTHORIZED_USERS = load_authorized_users()


def is_authorized(user_id):
    return str(user_id) in AUTHORIZED_USERS


# ==============================
# COMANDOS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot online.")


async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.reply_to_message.from_user.id

    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ Apenas usuários autorizados podem autorizar outros.")
        return

    save_authorized_user(user_id)
    AUTHORIZED_USERS.add(str(user_id))
    await update.message.reply_text("✅ Usuário autorizado.")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("❌ Você não está autorizado.")
        return

    text = update.message.text.strip()

    if not text.startswith("/an"):
        return

    try:
        url = text.split(" ", 1)[1]
    except:
        await update.message.reply_text("⚠ Use: /an link")
        return

    await DOWNLOAD_QUEUE.put((update, url))
    await update.message.reply_text("📥 Adicionado à fila.")


# ==============================
# WORKER GLOBAL (1 POR VEZ)
# ==============================

async def worker(app):

    global IS_PROCESSING

    while True:
        update, url = await DOWNLOAD_QUEUE.get()

        try:
            IS_PROCESSING = True
            await update.message.reply_text("⬇ Baixando...")

            result = await process_link(url)

            if isinstance(result, list):

                for file_path in result:
                    msg = await upload_video(app, file_path)

                    # encaminha para grupo
                    await app.bot.forward_message(
                        chat_id=update.effective_chat.id,
                        from_chat_id=STORAGE_CHANNEL,
                        message_id=msg.message_id
                    )

                    os.remove(file_path)

            else:
                msg = await upload_video(app, result)

                await app.bot.forward_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=STORAGE_CHANNEL,
                    message_id=msg.message_id
                )

                os.remove(result)

            await update.message.reply_text("✅ Concluído.")

        except Exception as e:
            await update.message.reply_text(f"❌ Erro: {e}")

        IS_PROCESSING = False
        DOWNLOAD_QUEUE.task_done()


# ==============================
# MAIN
# ==============================

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", authorize))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    asyncio.create_task(worker(app))

    print("Bot iniciado...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
