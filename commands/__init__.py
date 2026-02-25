from telegram.ext import CommandHandler, CallbackQueryHandler
from .download import download_command, cancel_callback

def register_handlers(app):
    app.add_handler(CommandHandler("download", download_command))
    app.add_handler(CallbackQueryHandler(cancel_callback, pattern="cancel"))
