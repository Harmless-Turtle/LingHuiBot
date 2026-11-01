from nonebot import logger
import re
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent, Message
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select, func, and_

from ..commands import (
    cmd_suit_random,
    cmd_suit_list,
)
from ...utils import batch_get, handle_errors
from ..check_files import SUIT_PICTURE_DATA_DIR
from .models import FurryPictureData
from .tools import load_picture, picture_segment
from ..furry_con.tools import get_http_api


@cmd_suit_random.handle()
@handle_errors
async def handle_suit_random(
        matcher: Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent,
        args: Message = CommandArg()
):
    furry_name = args.extract_plain_text().strip()
    get_api = False
    if "云" in str(event.get_message()):
        get_api = True
    is_number = False
    picture = None
    if furry_name.isdigit():
        picture = (await session.execute(
            select(FurryPictureData).where(FurryPictureData.id == int(furry_name)).order_by(func.random()).limit(1))).scalar_one_or_none()
        is_number = True
    elif furry_name:
        # 第一阶段：整体子串模糊匹配（纯“字符串 in 字符串”，不预设任何分隔符）。
        # 第二阶段：未命中时才按常见分隔符（“/”“或”“和”“、”等）拆分关键词兜底，
        #   要求每个片段都包含在 furry_name 中（AND、顺序无关），复杂度 O(关键词数)，
        #   不枚举任何排列；因此无论库中名字使用哪种分隔符、两种命名含义（多角色或
        #   同一角色的多个名字）、用户输入顺序如何，均可命中。
        #   注意：SQLAlchemy 的 Result 只能消费一次，故每段查询直接取出 picture，
        #   避免复用已关闭的结果对象（ResourceClosedError）。
        picture = (await session.execute(
            select(FurryPictureData).where(FurryPictureData.furry_name.contains(furry_name)).order_by(func.random()).limit(1))).scalar_one_or_none()
        if picture is None:
            tokens = [t for t in re.split(r"[/或和、&·，,;；\s]+", furry_name) if t]
            if len(tokens) > 1:
                conditions = [FurryPictureData.furry_name.contains(tok) for tok in tokens]
                picture = (await session.execute(
                    select(FurryPictureData).where(and_(*conditions)).order_by(func.random()).limit(1))).scalar_one_or_none()
    else:
        picture = (await session.execute(
            select(FurryPictureData).order_by(func.random()).limit(1))).scalar_one_or_none()
    if picture and not get_api:
        description = ""
        if picture.description:
            description = f"ta的留言是：{picture.description}\n"
        text = f"这只兽兽叫做“{picture.furry_name}”~\n{description}图片码为：{picture.id}"
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"{text}"
            + picture_segment(picture.file_path, SUIT_PICTURE_DATA_DIR) + "来源：本地\n"
            "您想上传图片吗？仅需发送“上传”即可开始上传流程（上传到本地）\n"
            f"想要从网络获取图片吗？仅需使用命令“云来只{picture.furry_name}”即可~"
        )
    else:
        response = await get_http_api("furpic", furry_name)
        logger.info(f" {furry_name}")
        if not response.get("ok"):
            text = f"似乎没有找到名字为{furry_name}的图片呢qwq"
            if is_number:
                text = f"似乎没有找到图片码为{furry_name}的图片呢qwq"
            await matcher.finish(MessageSegment.reply(event.message_id) + text)
        item = response.get("item")
        text = f"这只兽兽叫做“{item.get('furry_name')}”~\nta的留言是：{item.get('message')}\n图片码为：{item.get('id')}"
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"{text}" + MessageSegment.image(item.get("image")) + "来源：网络"
        )


@cmd_suit_list.handle()
@handle_errors
async def handle_suit_list(
        matcher: Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent,
        bot: Bot,
        args: Message = CommandArg()
):
    args = args.extract_plain_text().strip()
    result = await session.execute(
        select(FurryPictureData).
        where(FurryPictureData.furry_name.contains(args))
    )
    pictures = result.scalars().all()
    if not pictures:
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前没有图片呢qwq")
    final_list = []
    for picture in pictures:
        text = f"""图片码：{picture.id}
崽崽名字：{picture.furry_name}
文件名：{picture.file_name}
图片类型：{picture.type}
上传时间：{picture.upload_timestamp}
"""
        batch_text = await batch_get(
            text, load_picture(picture.file_path, SUIT_PICTURE_DATA_DIR), event.user_id, "furry_list"
        )
        final_list.append(batch_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=final_list)
