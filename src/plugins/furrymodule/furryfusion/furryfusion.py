import os
import time
from datetime import datetime

from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    Message,
    Bot,
    GroupMessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from ..check_file import OPENDATA

from ..commands import (
    furryfusion_list,
    furryfusion_check,
    furryfusion_information,
)
from ...utils import handle_errors, batch_get, get_config_item, handle_json
from .tools import get_fur_session, render_fursion_timeline_image, generate_furryfusion_pic, get_http_api,check_cache_expiration

furryfusion_pic = OPENDATA / "data" / "furry_system" / "furryfusion" / "furryfusion_timeline.png"

@furryfusion_list.handle()
@handle_errors
async def furry_fusion_list_handler(bot:Bot,matcher: Matcher, event:GroupMessageEvent, args:Message = CommandArg()):
    """获取 FurryFusion 时间轴并以图片形式发送。"""
    # 检查缓存图片是否存在且未超过一天
    if args:
        os.utime(furryfusion_pic, (time.time(), 0))
    cache_status = await check_cache_expiration(furryfusion_pic)
    if cache_status:
        await matcher.finish(MessageSegment.reply(event.message_id)+"距离上一次生成时间未超过一天，将使用缓存图片：\n"+MessageSegment.image(cache_status)+"如需重新生成，请使用“兽聚列表+任意文本”以重置。")
    await bot.call_api("send_msg", group_id=event.group_id, message=MessageSegment.reply(event.message_id)+"FurryFusion 页面已加载，等待 10 秒确保活动背景图加载完成...")
    payload = await get_http_api("timeline")

    if not payload.get("ok", True):
        message = payload.get("message") or payload.get("detail") or "未知错误"
        await matcher.finish(MessageSegment.reply(event.message_id)+f"获取 FurryFusion 活动列表失败：{message}\n发送“bug反馈”功能将该问题报告给管理员并等待回复。")

    events = payload.get("items", [])
    if not events:
        await matcher.finish(MessageSegment.reply(event.message_id)+"FurryFusion 活动列表为空呢...查询的地区可能没有活动哦~")
    image_bytes = await generate_furryfusion_pic("timeline", events)
    with open(furryfusion_pic, "wb") as f:
        f.write(image_bytes)
    await matcher.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(image_bytes)+"图片已缓存，要重新生成请使用“兽聚列表+任意文本”，例如“兽聚列表1”")

@furryfusion_check.handle()
@handle_errors
async def furry_fusion_check_handler(matcher: Matcher, event:GroupMessageEvent, args:Message = CommandArg()):
    args = args.extract_plain_text().strip()
    if args.isdigit():
        response = await get_http_api("day", args)
        if not response.get("ok", True):
            message = response.get("message") or response.get("detail") or "未知错误"
            await matcher.finish(MessageSegment.reply(event.message_id)+f"获取 FurryFusion 活动列表失败：{message}")
    else:
        response = await get_http_api("address", args)
    items = response.get("items", [])
    if not items:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"{response.get('message',"该地区暂未存在有活动的展子哦")}")
    image_bytes = await generate_furryfusion_pic("timeline", items)
    await matcher.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(image_bytes))

@furryfusion_information.handle()
@handle_errors
async def furry_fusion_information_handler(matcher: Matcher, event:GroupMessageEvent, args:Message = CommandArg()):
    args = args.extract_plain_text().strip()
    if not args:
        await matcher.finish(MessageSegment.reply(event.message_id)+"请在命令后输入展子 ID 以获取详细信息，例如“兽聚信息 1234”")
    response = await get_http_api("detail", args)
    if not response.get("ok", False):
        message = response.get("message") or response.get("detail") or "未知错误"
        await matcher.finish(MessageSegment.reply(event.message_id)+f"获取 FurryFusion 活动详情失败：{message}")
    items = response.get("fields", {})
    if not items:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"{response.get("message")}" or "该展子不存在哦")
    image_bytes = await generate_furryfusion_pic("info", items)
    await matcher.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(image_bytes))