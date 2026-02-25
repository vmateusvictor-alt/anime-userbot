active_downloads = {}

def register(chat_id):
    active_downloads[chat_id] = True

def cancel(chat_id):
    active_downloads[chat_id] = False

def is_active(chat_id):
    return active_downloads.get(chat_id, False)
