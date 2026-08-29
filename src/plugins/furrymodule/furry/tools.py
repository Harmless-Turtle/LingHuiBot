from pathlib import Path

import httpx
from io import BytesIO
from PIL import Image
from nonebot import logger

async def download_image(
        client: httpx.AsyncClient,
        url: str,
        md5:str,
        download_path:Path
) -> tuple[Path, str]:
    """
    下载图片并返回 Path 对象。
    """
    response = await client.get(url)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    image_format = image.format
    if image_format == "PNG":
        file_path =download_path / f"{md5}.jpg"
        if image.mode == "RGBA":
            image = image.convert("RGB")
        image.save(file_path, "JPEG")
    elif image_format == "GIF":
        file_path = download_path / f"{md5}.gif"
        with open(file_path, "wb") as f:
            f.write(response.content)
    else:
        file_path =download_path / f"{md5}.{image_format.lower()}"
        with open(file_path, "wb") as f:
            f.write(response.content)
    return file_path,md5