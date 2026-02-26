import os
import asyncio
import traceback
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import API_ID, API_HASH, STRING_SESSION, BOT_TOKEN
from core.queue import worker


async def safe_worker(user_client):
    try:
        await worker(user_client)
    except Exception:
        print("Erro no worker:")
        traceback.print_exc()


async def main():
    print("Verificando variáveis de ambiente...")

    # Força Railway a falhar se não estiver lendo
    if not API_ID:
        raise Exception("API_ID não encontrada no Railway!")

    if not API_HASH:
        raise Exception("API_HASH não encontrada no Railway!")

    if not STRING_SESSION:
        raise Exception("STRING_SESSION não encontrada no Railway!")

    if not BOT_TOKEN:
        raise Exception("BOT_TOKEN não encontrada no Railway!")

    print("Todas variáveis carregadas ✅")

    # ===== USERBOT =====
    print("Iniciando userbot...")
    user_client = TelegramClient(
        StringSession(STRING_SESSION),
        API_ID,
        API_HASH
    )

    await user_client.start()

    if not await user_client.is_user_authorized():
        raise Exception("STRING_SESSION inválida!")

    print("Userbot online ✅")

    # ===== BOT =====
    print("Iniciando bot...")
    bot_client = TelegramClient(
        "bot_session",
        API_ID,
        API_HASH
    )

    await bot_client.start(bot_token=BOT_TOKEN)

    print("Bot online ✅")

    # ===== WORKER =====
    asyncio.create_task(safe_worker(user_client))

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
