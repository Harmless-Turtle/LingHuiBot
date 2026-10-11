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
from ..check_file import furryfusion_login_session

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

@furryfusion_list.handle()
async def furry_fusion_list_handler(matcher: Matcher):
    """获取 FurryFusion 时间轴并以图片形式发送。"""
    fur_session = handle_json(furryfusion_login_session, 'r')
    if not isinstance(fur_session, dict) or not fur_session.get("fur_session"):
        fur_session = await get_fur_session()

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
        await matcher.finish("FurryFusion 返回的数据格式不正确，预期为 JSON 对象。")

    if not payload.get("ok", True):
        message = payload.get("message") or payload.get("detail") or "未知错误"
        await matcher.finish(f"获取 FurryFusion 活动列表失败：{message}")

    events = payload.get("items", [])
    if not isinstance(events, list):
        await matcher.finish("FurryFusion 返回的数据格式不正确，items 不是列表。")

    try:
        image_bytes = await render_fursion_timeline_image(events)
    except Exception:
        logger.exception("FurryFusion 时间轴图片生成失败")
        await matcher.finish("FurryFusion 活动列表图片生成失败，请查看终端日志。")

    await matcher.finish(MessageSegment.image(image_bytes))
