import random as rd
import time

import httpx
import jwt
from httpx import NetworkError, TimeoutException
from nonebot import get_plugin_config, logger
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..commands import cmd_suit_see
from ..config import Config
from ...utils import handle_errors


@cmd_suit_see.handle()
@handle_errors
async def handle_suit_see(
        matcher: Matcher,
        event: MessageEvent,
        args: Message = CommandArg()):
    if "#" not in str(args) and str(args) != "":
        await matcher.finish()
    plugin_config = get_plugin_config(Config)
    if not plugin_config.FURRY_SUIT_BASE_URL or not plugin_config.FURRY_SUIT_KEY:
        await matcher.finish(
            MessageSegment.reply(event.message_id)
            + "未读取到鉴毛 (FurrySuit) API 配置（FURRY_SUIT_BASE_URL / FURRY_SUIT_KEY），鉴毛功能暂不可用！"
        )
        return
    params_data = {"all": "1"}
    try:
        input_data = str(args).split("#")
        input_data = input_data[1]
        splice_url = "search"
        params_data['name'] = f"{input_data}"
        if input_data.isdigit():
            params_data.pop('name')
            params_data['qishu'] = f"{input_data}"
            splice_url = "qishu"
    except IndexError:
        splice_url = "random"
    # 生成 JWT
    payload = {
        "qq": str(event.user_id),  # 用户唯一标识
        "timestamp": int(time.time())  # 当前时间戳
    }
    token = jwt.encode(payload, plugin_config.FURRY_SUIT_KEY, algorithm="HS256")
    logger.debug(f"生成的 JWT: {token}")
    logger.debug(f"最终生成的params数据：{params_data}")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{plugin_config.FURRY_SUIT_BASE_URL}/{splice_url}",
                                         json={"qq": payload["qq"], "token": token},
                                         params=params_data)
    except (NetworkError, TimeoutException):
        await matcher.finish(MessageSegment.reply(event.message_id) + "网络异常或请求超时，无法访问鉴毛API，请稍后再试。")
    try:
        data = response.json()
    except ValueError:
        await matcher.finish(MessageSegment.reply(event.message_id) + "鉴毛API返回了无法解析的数据，请稍后再试。")
    if not isinstance(data, dict):
        await matcher.finish(MessageSegment.reply(event.message_id) + "鉴毛API返回了无法解析的数据，请稍后再试。")
    if response.status_code != 200:
        text = data.get('message', '未知错误')
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"鉴毛API返回：{text}[HTTP {response.status_code}]，请稍后再试。")
    data = data.get('data') or []
    if not isinstance(data, list) or not data:
        await matcher.finish(MessageSegment.reply(event.message_id) + "没有找到匹配的鉴毛记录呢qwq")
    select = rd.randint(0, len(data) - 1)
    data = data[select]
    qishu = data['qishu']
    name = data['name']
    city = data['city']
    race = data['race']
    studio = data['studio']
    by = data['by']
    image_url = data['url']
    if image_url == "":
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"鉴毛API返回了数据，但似乎没有图片URL，请稍后再试。")
    await matcher.finish(MessageSegment.reply(event.message_id) + f"期数：{qishu}\n"
                                                                  f"名字：{name}\n"
                                                                  f"城市：{city}\n"
                                                                  f"种族：{race}\n"
                                                                  f"工作室：{studio}\n"
                                                                  f"图片制作：{by}" + MessageSegment.image(image_url))