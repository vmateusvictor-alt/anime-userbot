from telegram.ext import ApplicationBuilder
from config import TOKEN
from commands import register_handlers
from core.queue import worker
import asyncio


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    register_handlers(app)

    async def start_worker(app):
        asyncio.create_task(worker())
        print("WORKER INICIADO")

    app.post_init = start_worker

    print("Bot rodando...")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
