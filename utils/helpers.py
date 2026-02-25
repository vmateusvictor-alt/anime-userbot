import re

def is_m3u8(url: str) -> bool:
    return ".m3u8" in url.lower()

def extract_m3u8_from_html(html: str):
    matches = re.findall(r'https?://[^"\']+\.m3u8[^"\']*', html)
    return matches[0] if matches else None
