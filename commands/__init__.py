from .download import register_download

def register_handlers(client):
    register_download(client)
