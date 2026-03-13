import os
import aiohttp
import asyncio
import uuid
from urllib.parse import urlparse

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

CHUNK = 1024 * 1024 * 2


async def download_file(url, progress=None):

    timeout = aiohttp.ClientTimeout(total=None)

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    async with aiohttp.ClientSession(timeout=timeout) as session:

        async with session.get(url, headers=headers, allow_redirects=True) as r:

            if r.status != 200:
                raise Exception(f"HTTP {r.status}")

            # pegar nome do arquivo
            filename = None

            cd = r.headers.get("Content-Disposition")

            if cd and "filename=" in cd:
                filename = cd.split("filename=")[1].replace('"', "")

            if not filename:
                path = urlparse(str(r.url)).path
                filename = os.path.basename(path)

            if not filename or "." not in filename:
                filename = str(uuid.uuid4()) + ".mp4"

            filepath = os.path.join(DOWNLOAD_DIR, filename)

            total = r.headers.get("Content-Length")

            if total:
                total = int(total)
            else:
                total = 0

            downloaded = 0
            last = 0

            with open(filepath, "wb") as f:

                async for chunk in r.content.iter_chunked(CHUNK):

                    f.write(chunk)
                    downloaded += len(chunk)

                    if total and progress:

                        percent = int(downloaded * 100 / total)

                        if percent - last >= 5:
                            last = percent
                            await progress(percent)

            return filepath
