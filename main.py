from telegram.ext import ApplicationBuilder
from config import TOKEN
from commands import register_handlers
from core.queue import worker
import asyncio

async def post_init(application):
    asyncio.create_task(worker())

def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    register_handlers(app)

    print("Bot rodando em polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
