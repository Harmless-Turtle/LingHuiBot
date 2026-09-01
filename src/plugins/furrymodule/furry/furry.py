from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.internal.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session
from nonebot.adapters.onebot.v11 import MessageSegment,GroupMessageEvent,Message
from sqlalchemy import select, func
from nonebot.params import CommandArg

from ..commands import (
furry_random,
furry_list,
)
from src.plugins.utils import handle_errors
from .models import FurryPictureData
from ...utils import batch_get


@furry_random.handle()
@handle_errors
async def furry_random_function(
        matcher:Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent,
        args:Message = CommandArg()
):
    furry_name = args.extract_plain_text().strip()
    result = await session.execute(select(FurryPictureData).order_by(func.random()).limit(1))
    is_number = False
    if furry_name.isdigit():
        result = await session.execute(
            select(FurryPictureData).where(FurryPictureData.id == int(furry_name)).order_by(func.random()).limit(1))
        is_number = True
    elif furry_name:
        result = await session.execute(
            select(FurryPictureData).where(FurryPictureData.furry_name == furry_name).order_by(func.random()).limit(1))
    picture = result.scalar_one_or_none()
    if picture:
        text = f"""这只兽兽叫做”{picture.furry_name}”~
图片码为：{picture.id}"""
        await matcher.finish(MessageSegment.reply(event.message_id)+f"{text}" + MessageSegment.image(picture.file_path)+"您也想上传图片？发送“投图 <崽崽名字> <图片类型 1为毛照 2为稿子>”即可上传图片啦~")
    else:
        text = f"似乎没有找到名字为{furry_name}的图片呢qwq"
        if is_number:
            text = f"似乎没有找到图片码为{furry_name}的图片呢qwq"
        await matcher.finish(MessageSegment.reply(event.message_id)+text)

@furry_list.handle()
@handle_errors
async def furry_list_function(
        matcher: Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent,
        bot:Bot,
        args:Message = CommandArg()
):
    args = args.extract_plain_text().strip()
    result = await session.execute(
        select(FurryPictureData).
        where(FurryPictureData.furry_name.contains(args))
    )
    pictures = result.scalars().all()
    if not pictures:
        await matcher.finish(MessageSegment.reply(event.message_id)+"当前没有图片呢qwq")
    final_list = []
    for picture in pictures:
        text = f"""图片码：{picture.id}
崽崽名字：{picture.furry_name}
文件名：{picture.file_name}
图片类型：{picture.type}
上传时间：{picture.upload_timestamp}
"""
        batch_text = await batch_get(text,picture.file_path,event.user_id,"furry_list")
        final_list.append(batch_text)
    # await matcher.finish(MessageSegment.reply(event.message_id)+f"当前共有{len(pictures)}张图片")
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=final_list)