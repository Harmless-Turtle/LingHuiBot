import io
from pathlib import Path

from PIL import Image
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent, GroupMessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import on_command
from nonebot_plugin_htmlrender import md_to_pic

menu = on_command("菜单", aliases={"凌辉菜单"}, priority=100, block=True)
main_menu = on_command("菜单01", aliases={"基本菜单"}, priority=99, block=True)
furry_menu = on_command("菜单02", aliases={"Furry菜单", "furry菜单"}, priority=99, block=True)
marry_menu = on_command("菜单03", aliases={"结婚菜单"}, priority=99, block=True)
service_menu = on_command("服务条款", aliases={"用户协议"}, block=True)

WORK_DATA = Path()
ALL_MENU_MD = WORK_DATA / 'Markdown' / 'All_Menu.md'
FURRY_MENU_MD = WORK_DATA / 'Markdown' / 'Furry_System.md'
MAIN_MENU_MD = WORK_DATA / 'Markdown' / 'Main_System.md'
SERVICE_MENU_MD = WORK_DATA / 'Markdown' / 'User_Agreement.md'
MARRY_MENU_MD = WORK_DATA / 'Markdown' / 'Marry_Menu.md'

ALL_MENU_PIC_DATA = WORK_DATA / 'data' / 'Menu' / 'All_Menu.png'
FURRY_MENU_PIC_DATA = WORK_DATA / 'data' / 'Menu' / 'Furry_Menu.png'
MAIN_MENU_PIC_DATA = WORK_DATA / 'data' / 'Menu' / 'Main_Menu.png'
SERVICE_MENU_PIC_DATA = WORK_DATA / 'data' / 'Menu' / 'Service_Menu.png'
MARRY_MENU_PIC_DATA = WORK_DATA / 'data' / 'Menu' / 'Marry_Menu.png'


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


@marry_menu.handle()
async def marry_menu_func(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    await handle_menu_command(matcher, event, MARRY_MENU_MD, MARRY_MENU_PIC_DATA, args)


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
        img.save(pic_path)
    return image_bytes


async def handle_menu_command(matcher: Matcher, event: MessageEvent, md_path: Path, pic_path: Path, args: Message):
    """通用的菜单命令处理函数"""
    if args.to_rich_text():
        await matcher.finish()

    pic = await get_menu_pic(md_path=md_path, pic_path=pic_path)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        MessageSegment.image(pic)
    )
