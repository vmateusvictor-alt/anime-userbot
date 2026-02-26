import asyncio
import traceback
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION
from commands import register_handlers
from core.queue import worker


async def safe_worker():
    try:
        await worker()
    except Exception:
        print("Erro no worker:")
        traceback.print_exc()


async def main():
    client = TelegramClient(
        StringSession(STRING_SESSION),
        API_ID,
        API_HASH
    )

    await client.start()

    if not await client.is_user_authorized():
        raise Exception("STRING_SESSION inválida!")

    print("Userbot online...")

    register_handlers(client)

    asyncio.create_task(safe_worker())

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        print("ERRO FATAL:")
        traceback.print_exc()
