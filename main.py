from telegram.ext import ApplicationBuilder
from config import TOKEN
from commands import register_handlers
from core.queue import worker
import asyncio


async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    register_handlers(app)

    print("Bot rodando...")

    # inicia worker manualmente
    asyncio.create_task(worker())

    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
