import os
from telegram.ext import ApplicationBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN não encontrado")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    print("Token carregado com sucesso")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
