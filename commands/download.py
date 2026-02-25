from telethon import events
from core.queue import download_queue
from core.streamer import stream_video


def register_download(client):

    @client.on(events.NewMessage(pattern=r"\.download (.+)"))
    async def handler(event):

        url = event.pattern_match.group(1)

        await event.reply("📥 Adicionado à fila...")

        async def job():
            await stream_video(client, event, url)

        await download_queue.put(job)
