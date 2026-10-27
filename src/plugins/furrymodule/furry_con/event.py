import os
import time
from datetime import datetime, date

from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    Message,
    Bot,
    GroupMessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from ..check_files import CON_TIMELINE_CACHE_FILE

from ..commands import (
    cmd_con_list,
    cmd_con_check,
    cmd_con_info,
    cmd_con_history,
)
from ...utils import batch_get, handle_errors, handle_json
from .tools import (
    get_fur_session,
    render_fursion_timeline_image,
    generate_furryfusion_pic,
    get_http_api,
    check_cache_expiration,
)

furryfusion_pic = CON_TIMELINE_CACHE_FILE


@cmd_con_list.handle()
@handle_errors
async def handle_con_list(bot: Bot, matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    """获取 FurryFusion 时间轴并以图片形式发送。"""
    # 检查缓存图片是否存在且未超过一天
    if args:
        os.utime(furryfusion_pic, (time.time(), 0))
    cache_status = await check_cache_expiration(furryfusion_pic)
    if cache_status:
        await matcher.finish(
            MessageSegment.reply(event.message_id)
            + "距离上一次生成时间未超过一天，将使用缓存图片：\n"
            + MessageSegment.image(cache_status)
            + "如需重新生成，请使用“兽聚列表+任意文本”以重置。"
        )
    await bot.call_api(
        "send_msg",
        group_id=event.group_id,
        message=MessageSegment.reply(event.message_id) + "FurryFusion 页面已加载，等待 10 秒确保活动背景图加载完成...",
    )
    payload = await get_http_api("timeline")

    if not payload.get("ok", True):
        message = payload.get("message") or payload.get("detail") or "未知错误"
        await matcher.finish(
            MessageSegment.reply(event.message_id)
            + f"获取 FurryFusion 活动列表失败：{message}\n发送“bug反馈”功能将该问题报告给管理员并等待回复。"
        )

    events = payload.get("items", [])
    if not events:
        await matcher.finish(MessageSegment.reply(event.message_id) + "FurryFusion 活动列表为空呢...查询的地区可能没有活动哦~")
    image_bytes = await generate_furryfusion_pic("timeline", events)
    with open(furryfusion_pic, "wb") as f:
        f.write(image_bytes)
    await matcher.finish(
        MessageSegment.reply(event.message_id)
        + MessageSegment.image(image_bytes)
        + "图片已缓存，要重新生成请使用“兽聚列表+任意文本”，例如“兽聚列表1”"
    )


@cmd_con_check.handle()
@handle_errors
async def handle_con_check(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip()
    if args.isdigit():
        response = await get_http_api("day", args)
        if not response.get("ok", True):
            message = response.get("message") or response.get("detail") or "未知错误"
            await matcher.finish(MessageSegment.reply(event.message_id) + f"获取 FurryFusion 活动列表失败：{message}")
    else:
        response = await get_http_api("address", args)
    items = response.get("items", [])
    if not items:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"{response.get('message', '该地区暂未存在有活动的展子哦')}")
    image_bytes = await generate_furryfusion_pic("timeline", items)
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(image_bytes))


@cmd_con_info.handle()
@handle_errors
async def handle_con_info(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip()
    if not args:
        await matcher.finish(MessageSegment.reply(event.message_id) + "请在命令后输入展子 ID 以获取详细信息，例如“兽聚信息 1234”")
    response = await get_http_api("detail", args)
    if not response.get("ok", False):
        message = response.get("message") or response.get("detail") or "未知错误"
        await matcher.finish(MessageSegment.reply(event.message_id) + f"获取 FurryFusion 活动详情失败：{message}")
    items = response.get("fields", {})
    if not items:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"{response.get('message', '该展子不存在哦')}")
    date_str = items.get("time_end", "1999.01.01")
    groups = items.get("groups", [])
    url = items.get("url", "暂无URL信息")
    text = f"快速访问：\n群号：{', '.join(groups) if groups else '暂无群组信息'}\n链接：{url}"
    target_date = date.fromisoformat(date_str.replace(".", "-"))
    current_date = date.today()
    if current_date > target_date:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"该展子尚未有预告，若想了解历史兽聚，请使用“兽聚历史 {args}”命令\n{text}"
        )
    image_bytes = await generate_furryfusion_pic("info", items)
    await matcher.finish(
        MessageSegment.reply(event.message_id)
        + MessageSegment.image(image_bytes)
        + f"要了解历史兽聚，请使用“兽聚历史 {args}”命令\n{text}"
    )


@cmd_con_history.handle()
@handle_errors
async def handle_con_history(bot: Bot, matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip()
    if not args:
        await matcher.finish(MessageSegment.reply(event.message_id) + "请在命令后输入展子 ID 以获取历史信息，例如“兽聚历史 1234”")
    response = await get_http_api("detail", args)
    if not response.get("ok", False):
        message = response.get("message") or response.get("detail") or "未知错误"
        await matcher.finish(MessageSegment.reply(event.message_id) + f"获取 FurryFusion 活动历史失败：{message}")
    history_list = response.get("history", [])
    if not history_list:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"{response.get('message', '该展子暂未存在有历史活动哦')}")
    finnal_list = []
    for index, item in enumerate(history_list):
        logger.info(f"历史记录 #{index + 1}: {item!r}")
        image_bytes = await generate_furryfusion_pic("info", item)
        data = await batch_get("", image_bytes, event.self_id, "兽聚历史 - " + args)
        finnal_list.append(data)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=finnal_list)