import io
from pathlib import Path
from PIL import Image
from nonebot.plugin import on_command,on_message  # 导入事件响应器
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent, GroupMessageEvent  # 导入事件响应器以进行操作
from nonebot import require
from nonebot.params import CommandArg
from nonebot.rule import to_me
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic


menu = on_command("菜单", aliases={"凌辉菜单"}, priority=100, block=True)
main_Menu = on_command("菜单01", aliases={"基本菜单"}, priority=99, block=True)
furry_Menu = on_command("菜单02", aliases={"Furry菜单", "furry菜单"}, priority=99, block=True)
marry_Menu = on_command("菜单03", aliases={"结婚菜单"}, priority=99, block=True)
service_Menu = on_command("服务条款", aliases={"用户协议"}, block=True)
at_menu = on_message(rule=to_me(), priority=1, block=False)

WORK_DATA = Path()
All_MENU_MARKDOWN = str(WORK_DATA / 'data' / 'Menu' / 'All_Menu.md')
FURRY_MENU_MARKDOWN = str(WORK_DATA / 'Markdown' / 'Furry_System.md')
MAIN_MENU_MARKDOWN = str(WORK_DATA / 'Markdown' / 'Main_System.md')
SERVICE_MENU_MARKDOWN = str(WORK_DATA / 'Markdown' / 'User_Agreement.md')
MARRY_MENU_MARKDOWN = str(WORK_DATA / 'data' / 'Menu' / 'Marry_Menu.md')

@menu.handle()
async def menu_func(event:MessageEvent, args:Message = CommandArg()):
    if args.extract_plain_text():
        await menu.finish()    # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=All_MENU_MARKDOWN, width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")

    await menu.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(pic))


@at_menu.handle()
async def at_menu_func(event: MessageEvent):
    if event.get_message().extract_plain_text() != "":
        await at_menu.finish()

    # 直接生成并发送图片
    pic = await md_to_pic(md_path=All_MENU_MARKDOWN, width=900)
    await at_menu.finish(
        MessageSegment.reply(event.message_id) +
        MessageSegment.image(pic)
    )


@main_Menu.handle()
async def main_menu_func(event: MessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text():
        await main_Menu.finish()  # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=MAIN_MENU_MARKDOWN, width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")
    await main_Menu.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(pic))


@furry_Menu.handle()
async def furry_menu_func(event: GroupMessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text():
        await furry_Menu.finish()  # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=FURRY_MENU_MARKDOWN, width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")
    await main_Menu.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(pic))


@service_Menu.handle()
async def service_menu_func(event: GroupMessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text():
        await furry_Menu.finish()  # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=SERVICE_MENU_MARKDOWN, width=900)
    a = Image.open(io.BytesIO(pic))

    a.save("md2pic.png", format="PNG")
    await main_Menu.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(pic))


@marry_Menu.handle()
async def mm_func(event: MessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text():
        await furry_Menu.finish()  # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=MARRY_MENU_MARKDOWN, width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")
    await main_Menu.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(pic))
