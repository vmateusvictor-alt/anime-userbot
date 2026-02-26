import os
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from pyrogram import Client

# ==============================
# VERIFICAÇÃO DE VARIÁVEIS
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN não definido")

if not API_ID:
    raise ValueError("API_ID não definido")

if not API_HASH:
    raise ValueError("API_HASH não definido")

if not SESSION_STRING:
    raise ValueError("SESSION_STRING não definido")

API_ID = int(API_ID)

# ==============================
# CONFIG
# ==============================

DOWNLOAD_PATH = "/tmp/video.mp4"
QUEUE = asyncio.Queue()

# ==============================
# USERBOT (PYROGRAM)
# ==============================

userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

# ==============================
# BARRA DE PROGRESSO
# ==============================

def progress_bar(percent: int):
    bars = int(percent // 5)
    return "█" * bars + "░" * (20 - bars)

# ==============================
# DOWNLOAD COM PROGRESSO
# ==============================

async def download_file(url: str, status_msg):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_percent = 0

            with open(DOWNLOAD_PATH, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total > 0:
                        percent = int(downloaded * 100 / total)

                        if percent - last_percent >= 5:
                            last_percent = percent
                            bar = progress_bar(percent)

                            await status_msg.edit_text(
                                f"⬇️ Baixando...\n\n"
                                f"[{bar}] {percent}%"
                            )

# ==============================
# UPLOAD PROGRESSO
# ==============================

async def upload_progress(current, total, status_msg):
    percent = int(current * 100 / total)
    bar = progress_bar(percent)

    if percent % 5 == 0:
        try:
            await status_msg.edit_text(
                f"⬆️ Enviando...\n\n"
                f"[{bar}] {percent}%"
            )
        except:
            pass

# ==============================
# WORKER DA FILA
# ==============================

async def worker():
    await userbot.start()

    while True:
        chat_id, url = await QUEUE.get()

        status_msg = await userbot.send_message(
            chat_id,
            "🔄 Iniciando..."
        )

        try:
            # DOWNLOAD
            await download_file(url, status_msg)

            # UPLOAD
            await userbot.send_video(
                chat_id=chat_id,
                video=DOWNLOAD_PATH,
                caption="🎬 Aqui está!",
                supports_streaming=True,
                progress=upload_progress,
                progress_args=(status_msg,)
            )

            await status_msg.edit_text("✅ Concluído!")

        except Exception as e:
            await status_msg.edit_text(f"❌ Erro:\n{str(e)}")

        finally:
            if os.path.exists(DOWNLOAD_PATH):
                os.remove(DOWNLOAD_PATH)

            QUEUE.task_done()

# ==============================
# COMANDO /anime
# ==============================

async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Use:\n/anime link_mp4"
        )
        return

    url = context.args[0]

    await update.message.reply_text("📥 Adicionado à fila...")
    await QUEUE.put((update.effective_chat.id, url))

# ==============================
# MAIN
# ==============================

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("anime", anime))

    asyncio.create_task(worker())

    print("🚀 Bot online")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
