from pathlib import Path

import httpx
from io import BytesIO
from PIL import Image
from nonebot import logger
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select
from .models import FurryPictureData
from ...Exceptions import UserVisibleError

# 单张图上限，避免被超大文件拖垮磁盘/内存
MAX_IMAGE_BYTES = 25 * 1024 * 1024

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
    if len(response.content) > MAX_IMAGE_BYTES:
        raise UserVisibleError("图片太大了，请上传 25MB 以内的图片呢xwx")
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

async def is_picture(
        file_md5: str,
        path: Path,
        session: async_scoped_session
):
    # 查表是否有重复值
    result = await session.execute(
        select(FurryPictureData.id)
        .where(FurryPictureData.file_name == file_md5)
        .limit(1)
    )
    # 检查图片是否已存在
    if any(path.glob(f"{file_md5}.*")) or result.scalar_one_or_none() is not None:
        return True
    return False