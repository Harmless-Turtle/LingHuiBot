import os
import time

import httpx
from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    Message,
    Bot,
    GroupMessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from ..check_file import furryfusion_login_session,OPENDATA

from ..commands import (
    furryfusion_list,
    furryfusion_check,
    furryfusion_countdown,
    furryfusion_quick_information,
    furryfusion_information,
    furryfusion_login
)
from ...utils import get_api_httpx, handle_errors, batch_get, get_config_item, handle_json
from .tools import get_fur_session, render_fursion_timeline_image

furryfusion_pic = OPENDATA / "data" / "furry_system" / "furryfusion" / "furryfusion_timeline.png"

@furryfusion_list.handle()
@handle_errors
async def furry_fusion_list_handler(bot:Bot,matcher: Matcher, event:GroupMessageEvent, args:Message = CommandArg()):
    """获取 FurryFusion 时间轴并以图片形式发送。"""
    # 检查缓存图片是否存在且未超过一天
    if os.path.exists(furryfusion_pic):
        creation_time = int(os.path.getmtime(furryfusion_pic))
        if int(time.time()) - creation_time < 86400:
            with open(furryfusion_pic, "rb") as f:
                image_bytes = f.read()
            await matcher.finish(MessageSegment.reply(event.message_id)+"距离上一次生成时间未超过一天，将使用缓存图片：\n"+MessageSegment.image(image_bytes)+"如需重新生成，请使用“兽聚列表+任意文本”以重置。")
    # 确认缓存已过期，进入获取新图片步骤
    fur_session = handle_json(furryfusion_login_session, 'r')
    if not isinstance(fur_session, dict) or not fur_session.get("fur_session"):
        fur_session = await get_fur_session()
    if args:
        os.utime(furryfusion_pic, (time.time(), 0))
    await bot.call_api("send_msg", group_id=event.group_id, message=MessageSegment.reply(event.message_id)+"FurryFusion 页面已加载，等待 10 秒确保活动背景图加载完成...")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://qqbot.fur-bot.com/api/v1/fursion/timeline",
            cookies=fur_session,
        )
        if response.status_code == 401:
            logger.info("FurryFusion 会话过期，正在重新登录...")
            fur_session = await get_fur_session()
            logger.success("FurryFusion 登录成功！")
            response = await client.get(
                "https://qqbot.fur-bot.com/api/v1/fursion/timeline",
                cookies=fur_session,
            )

        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, dict):
        await matcher.finish(MessageSegment.reply(event.message_id)+"FurryFusion 返回的数据格式不正确，预期为 JSON 对象。\n发送“bug反馈”功能将该问题报告给管理员并等待回复。")

    if not payload.get("ok", True):
        message = payload.get("message") or payload.get("detail") or "未知错误"
        await matcher.finish(MessageSegment.reply(event.message_id)+f"获取 FurryFusion 活动列表失败：{message}\n发送“bug反馈”功能将该问题报告给管理员并等待回复。")

    events = payload.get("items", [])
    if not isinstance(events, list):
        await matcher.finish(MessageSegment.reply(event.message_id)+"FurryFusion 返回的数据格式不正确，items 不是列表。\n发送“bug反馈”功能将该问题报告给管理员并等待回复。")

    try:
        image_bytes = await render_fursion_timeline_image(events)
    except Exception:
        logger.exception("FurryFusion 时间轴图片生成失败")
        await matcher.finish(MessageSegment.reply(event.message_id)+"FurryFusion 活动列表图片生成失败，请查看终端日志。\n发送“bug反馈”功能将该问题报告给管理员并等待回复。")
    with open(furryfusion_pic, "wb") as f:
        f.write(image_bytes)
    await matcher.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(image_bytes)+"图片已缓存，要重新生成请使用“兽聚列表+任意文本”，例如“兽聚列表1”")
