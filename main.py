import asyncio
import traceback
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import API_ID, API_HASH, STRING_SESSION, BOT_TOKEN
from commands import register_handlers
from core.queue import worker


async def safe_worker():
    try:
        await worker()
    except Exception:
        print("Erro no worker:")
        traceback.print_exc()


async def main():
    # USERBOT
    user_client = TelegramClient(
        StringSession(STRING_SESSION),
        API_ID,
        API_HASH
    )

    # BOT
    bot_client = TelegramClient(
        "bot_session",
        API_ID,
        API_HASH
    )

    print("Iniciando userbot...")
    await user_client.start()

    if not await user_client.is_user_authorized():
        raise Exception("STRING_SESSION inválida!")

    print("Userbot online ✅")

    print("Iniciando bot...")
    await bot_client.start(bot_token=BOT_TOKEN)

    print("Bot online ✅")

    # Registra handlers no BOT (interface pública)
    register_handlers(bot_client)

    # Worker usa o userbot para tarefas pesadas
    asyncio.create_task(safe_worker())

    # Mantém ambos vivos
    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        print("ERRO FATAL:")
        traceback.print_exc()
