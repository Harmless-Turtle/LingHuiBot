from pathlib import Path, PurePosixPath, PureWindowsPath

import httpx
from io import BytesIO
from PIL import Image
from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot_plugin_orm import async_scoped_session, get_session
from sqlalchemy import select

from ..check_files import BASE_DIR, SUIT_PICTURE_DATA_DIR
from .models import FurryPictureData


def to_relative_path(path: Path) -> str:
    """转换为相对 BASE_DIR 的 POSIX 路径，便于跨平台/跨容器存储。"""
    return Path(path).resolve().relative_to(BASE_DIR.resolve()).as_posix()


def _is_absolute(stored: str) -> bool:
    return PureWindowsPath(stored).is_absolute() or PurePosixPath(stored).is_absolute()


def resolve_picture_path(stored: str, fallback_dir: Path) -> Path:
    """解析存储的路径；旧版绝对路径失效时按文件名回退到 fallback_dir。"""
    path = Path(stored) if _is_absolute(stored) else BASE_DIR / stored
    if path.is_file():
        return path
    return fallback_dir / PureWindowsPath(stored).name


def load_picture(stored: str | None, fallback_dir: Path) -> bytes | None:
    # 协议端（NapCat）可能运行在另一个容器，无法读取本地路径，因此统一以 base64 发送
    if not stored:
        return None
    path = resolve_picture_path(stored, fallback_dir)
    if not path.is_file():
        logger.warning(f"图片文件不存在：{stored}")
        return None
    return path.read_bytes()


def picture_segment(stored: str | None, fallback_dir: Path) -> MessageSegment:
    data = load_picture(stored, fallback_dir)
    if data is None:
        return MessageSegment.text("\n（图片文件丢失）\n")
    return MessageSegment.image(data)


@get_driver().on_startup
async def normalize_picture_paths():
    async with get_session() as session:
        pictures = (await session.scalars(select(FurryPictureData))).all()
        changed = 0
        for picture in pictures:
            if not picture.file_path:
                continue
            # 已审核图片都在 SUIT_PICTURE_DATA_DIR，按文件名统一成规范的相对路径
            canonical = to_relative_path(SUIT_PICTURE_DATA_DIR / PureWindowsPath(picture.file_path).name)
            if picture.file_path != canonical:
                picture.file_path = canonical
                changed += 1
        if changed:
            await session.commit()
            logger.info(f"已将 {changed} 条毛图记录的路径规范化为相对路径")


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
