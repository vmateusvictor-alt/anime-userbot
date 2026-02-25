import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_string = os.getenv("SESSION_STRING")

client = None

async def start_client():
    global client

    if session_string:
        print("Usando SESSION_STRING existente...")
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.start()
    else:
        print("Nenhuma SESSION_STRING encontrada.")
        print("Iniciando login automático...")

        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.start()

        string = client.session.save()
        print("\n============================")
        print("COPIE SUA SESSION_STRING:")
        print(string)
        print("============================\n")

async def main():
    await start_client()

    @client.on(events.NewMessage(pattern=r"\.ping"))
    async def ping(event):
        await event.reply("🏓 Pong!")

    print("Userbot rodando...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
