from nonebot.plugin import on_command  # 导入事件响应器
from nonebot.adapters import Message  # 导入抽象基类Message以允许Bot回复str
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent, GroupMessageEvent  # 导入事件响应器以进行操作
from nonebot import require
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic
from pathlib import Path
from PIL import Image
import io
from nonebot.params import CommandArg


Menu = on_command("菜单", aliases={"凌辉菜单"}, priority=100, block=True)
Main_Menu = on_command("菜单01",aliases={"基本菜单"},priority=99,block=True)
Furry_Menu = on_command("菜单02",aliases={"Furry菜单","furry菜单"}, priority=99, block=True)
Marry_Menu = on_command("菜单03",aliases={"结婚菜单"},priority=99,block=True)
Service_Menu = on_command("服务条款",aliases={"用户协议"},block=True)

opendata = Path.cwd()
All_Menu_Markdown = opendata / 'data/Menu/All_Menu.md'
Furry_Menu_Markdown = opendata / 'data/Menu/Furry_Menu.md'
Main_Menu_Markdown = opendata / 'data/Menu/Main_Menu.md'
Service_Menu_Markdown = opendata / 'data/Menu/Service.md'
Marry_Menu_Markdown = opendata / 'data/Menu/Marry_Menu.md'

@Menu.handle()
async def Menu_Function(event:MessageEvent,args:Message = CommandArg()):
    if args.extract_plain_text():
        await Menu.finish()    # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=All_Menu_Markdown,width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")

    await Menu.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(pic))

@Main_Menu.handle()
async def Main_Menu_Function(event:MessageEvent,args:Message = CommandArg()):
    if args.extract_plain_text():
        await Main_Menu.finish()    # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=Main_Menu_Markdown,width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")
    await Main_Menu.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(pic))


@Furry_Menu.handle()
async def Furry_Menu_Function(event: GroupMessageEvent,args:Message = CommandArg()):
    if args.extract_plain_text():
        await Furry_Menu.finish()    # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=Furry_Menu_Markdown,width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")
    await Main_Menu.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(pic))

@Service_Menu.handle()
async def Service_Menu_Function(event: GroupMessageEvent,args:Message = CommandArg()):
    if args.extract_plain_text():
        await Furry_Menu.finish()    # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=Service_Menu_Markdown,width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")
    await Main_Menu.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(pic))

@Marry_Menu.handle()
async def MM_Function(event:MessageEvent,args:Message = CommandArg()):
    if args.extract_plain_text():
        await Furry_Menu.finish()    # 若消息后面存在文本则不响应
    pic = await md_to_pic(md_path=Marry_Menu_Markdown,width=900)
    a = Image.open(io.BytesIO(pic))
    a.save("md2pic.png", format="PNG")
    await Main_Menu.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(pic))