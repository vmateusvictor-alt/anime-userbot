import asyncio
import os

async def smart_convert(video_path):

    # Se não for MKV não precisa converter
    if not video_path.endswith(".mkv"):
        return video_path

    output_path = video_path.replace(".mkv", ".mp4")

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-map", "0:v:0",
        "-map", "0:a:m:language:jpn?",
        "-map", "0:s?",
        "-c:v", "copy",
        "-c:a", "copy",
        "-c:s", "mov_text",
        "-disposition:s:0", "default",
        "-y",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()

    if process.returncode != 0:
        raise Exception("Erro ao converter para MP4.")

    # remove MKV original
    if os.path.exists(video_path):
        os.remove(video_path)

    return output_path
