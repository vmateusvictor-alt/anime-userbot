from telegram.ext import CommandHandler
from .download import download_command, cancel_command
from .start import start_command

def register_handlers(app):
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("download", download_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
