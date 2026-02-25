import asyncio

download_queue = asyncio.Queue()

async def worker():
    while True:
        job = await download_queue.get()
        try:
            await job()
        except Exception as e:
            print("Erro:", e)
        finally:
            download_queue.task_done()
