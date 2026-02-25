import asyncio
from telegram.ext import ApplicationBuilder
from config import TOKEN
from commands import register_handlers
from core.queue import worker

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    register_handlers(app)

    asyncio.create_task(worker())

    print("Bot rodando...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
