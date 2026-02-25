from telegram.ext import ApplicationBuilder
from config import TOKEN
from commands import register_handlers
from core.queue import worker
import asyncio


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    register_handlers(app)

    # inicia worker quando o bot iniciar
    async def on_startup(app):
        asyncio.create_task(worker())

    app.post_init = on_startup

    print("Bot rodando...")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
