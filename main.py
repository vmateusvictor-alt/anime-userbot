import asyncio
from telethon import TelegramClient
from config import API_ID, API_HASH, STRING_SESSION
from commands import register_handlers
from core.queue import worker


async def main():
    client = TelegramClient(
        STRING_SESSION,
        API_ID,
        API_HASH
    )

    await client.start()

    print("Userbot online...")

    register_handlers(client)

    asyncio.create_task(worker())

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
