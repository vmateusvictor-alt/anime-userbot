import os
import subprocess

def generate_thumbnail(video_path, thumb_path):
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-ss", "00:00:05",
        "-vframes", "1",
        thumb_path,
        "-y"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def format_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
