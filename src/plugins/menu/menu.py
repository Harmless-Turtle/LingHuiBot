import io


from PIL import Image
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent, GroupMessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_htmlrender import md_to_pic

from .commands import *
from .check_files import *

@menu.handle()
async def menu_func(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    await handle_menu_command(matcher, event, ALL_MENU_MD, ALL_MENU_PIC_DATA, args)


@main_menu.handle()
async def main_menu_func(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    await handle_menu_command(matcher, event, MAIN_MENU_MD, MAIN_MENU_PIC_DATA, args)


@furry_menu.handle()
async def furry_menu_func(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    await handle_menu_command(matcher, event, FURRY_MENU_MD, FURRY_MENU_PIC_DATA, args)


@service_menu.handle()
async def service_menu_func(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    await handle_menu_command(matcher, event, SERVICE_MENU_MD, SERVICE_MENU_PIC_DATA, args)

@admin_menu.handle()
async def admin_menu_func(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    await handle_menu_command(matcher, event, ADMIN_MENU_MD, ADMIN_MENU_PIC_DATA, args)

async def handle_menu_command(matcher: Matcher, event: MessageEvent, md_path: Path, pic_path: Path, args: Message):
    """通用的菜单命令处理函数"""
    if args.to_rich_text():
        await matcher.finish()

    pic = await get_menu_pic(md_path=md_path, pic_path=pic_path)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        MessageSegment.image(pic)
    )


async def get_menu_pic(md_path: Path, pic_path: Path = None, width: int = 900) -> bytes:
    # 判断图片是否存在且比md文件新，否则重新生成
    if pic_path and pic_path.exists() and md_path.exists():
        pic_mtime = pic_path.stat().st_mtime
        md_mtime = md_path.stat().st_mtime
        if pic_mtime > md_mtime:
            with open(pic_path, 'rb') as f:
                return f.read()

    image_bytes = await md_to_pic(md_path=str(md_path), width=width)
    with Image.open(io.BytesIO(image_bytes)) as img:
        pic_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(pic_path)
    return image_bytes
