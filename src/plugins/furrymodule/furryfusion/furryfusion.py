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
from .tools import get_fur_session

@furryfusion_list.handle()
async def furry_fusion_list_handler(matcher: Matcher):
    fur_session = handle_json(furryfusion_login_session,'r')
    async with httpx.AsyncClient() as client:
        response = await client.get("https://qqbot.fur-bot.com/api/v1/fursion/timeline",cookies=fur_session)
        if response.status_code == 401:
            logger.info("FurryFusion 会话过期，正在重新登录...")
            fur_session = await get_fur_session()
            logger.success("FurryFusion 登录成功！")
            response = await client.get("https://qqbot.fur-bot.com/api/v1/fursion/timeline",cookies=fur_session)
        response = response.json()
        logger.info(response)
    await matcher.finish()