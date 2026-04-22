import io
from pathlib import Path

import httpx

from nonebot.utils import run_sync
from meme_generator import (
    get_meme,
    search_memes
)
from PIL import Image


def _generate_meme_sync(meme_key: str, image_bytes: bytes):
    meme = get_meme(meme_key)
    if meme is None:
        raise RuntimeError("meme not found: petpet")

    # 将传入的 bytes 数据转换为 meme-generator 可用的 Image 对象
    img = Image.open(io.BytesIO(image_bytes))

    # 将图片列表传给 generate_preview
    result = meme.generate_preview()

    if isinstance(result, bytes):
        return result
    else:
        raise RuntimeError(str(result))

async def generate_meme(meme_key: str, image_bytes: bytes):
    return await run_sync(_generate_meme_sync)(meme_key, image_bytes)

async def check_memes_func(meme_key: str):
    """

    Args:
        meme_key: 传入要查找的meme标签，接受中文

    Returns:
        meme.Image对象

    """
    meme = search_memes(meme_key, True)
    if meme is None:
        raise RuntimeError(f"meme not found: {meme}")
    if len(meme) >= 100:
        raise RuntimeError(f"No args")
    return get_meme(f"{meme[0]}")

async def download_avatar(user_id: str,target_dir: Path):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://q.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640&img_type=jpg")
    with open(target_dir, 'wb') as f:
        f.write(resp.content)
        return