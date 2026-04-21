from nonebot.utils import run_sync
from meme_generator import Image, get_meme


# 这是一个纯同步的函数，专门负责执行耗时的生成操作
def _generate_meme_sync(meme_key: str):
    meme = get_meme(meme_key)
    if meme is None:
        raise RuntimeError("meme not found: petpet")

    result = meme.generate_preview({"circle": True})

    if isinstance(result, bytes):
        with open("preview.gif", "wb") as f:
            f.write(result)
    else:
        raise RuntimeError(str(result))

# 这是一个给 NoneBot 调用的异步入口
async def generate_meme(meme_key: str):
    # 使用 run_sync 将同步函数放入线程池运行
    return await run_sync(_generate_meme_sync)(meme_key)