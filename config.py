import os

def get_env(name):
    value = os.getenv(name)
    if not value:
        raise Exception(f"{name} não encontrada no Railway!")
    return value

API_ID = int(get_env("API_ID"))
API_HASH = get_env("API_HASH")
STRING_SESSION = get_env("STRING_SESSION")
BOT_TOKEN = get_env("BOT_TOKEN")
