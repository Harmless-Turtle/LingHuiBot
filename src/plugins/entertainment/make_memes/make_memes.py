import httpx
from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import MessageSegment, Message,GroupMessageEvent
from meme_generator import (
    Image,
)
from nonebot.params import CommandArg

from src.plugins.entertainment.check_files import memes_make_path
from src.plugins.utils import handle_errors,at_is_true
from .tools import check_memes_func,download_avatar

meme_matcher = on_command("制作表情", aliases={"memes"})


@meme_matcher.handle()
@handle_errors
async def handle_meme(
        event: GroupMessageEvent,
        args:Message = CommandArg()
):
    user_id = await at_is_true(event, args)
    if not user_id.isdigit():
        user_id = str(event.user_id)
    # 拼接路径
    target_dir = memes_make_path / f"{event.user_id}.jpg"
    meme = await check_memes_func(args.extract_plain_text()[0])
    await download_avatar(user_id,target_dir)
    with open(target_dir, "rb") as f:
        data = f.read()
    result = meme.generate([Image("test", data)], [], {"circle": True})
    if isinstance(result, bytes):
        await meme_matcher.finish(MessageSegment.image(result))
    else:
        raise RuntimeError(str(result))