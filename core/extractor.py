import httpx
from bs4 import BeautifulSoup

async def extract_video_url(url):

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)

        content_type = r.headers.get("Content-Type", "")

        if "video" in content_type or url.endswith((".mp4", ".mkv")):
            return url

        if "application/vnd.apple.mpegurl" in content_type:
            return url

        if "text/html" in content_type:
            soup = BeautifulSoup(r.text, "html.parser")

            # procura <video>
            video = soup.find("video")
            if video and video.get("src"):
                return video.get("src")

            # procura iframe
            iframe = soup.find("iframe")
            if iframe and iframe.get("src"):
                return iframe.get("src")

    return None
