import time

import jwt
import httpx
from httpx import NetworkError
import random as rd
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot import logger,get_driver

from ..commands import see_furry
from src.plugins.utils import handle_errors


try:
    see_furry_baseURL = get_driver().config.furry_see_furry
    secret_key = get_driver().config.furry_see_furry_key
except AttributeError:
    see_furry_baseURL = None
    logger.warning("未读取到鉴毛API，鉴毛功能可能不可用！")

@see_furry.handle()
@handle_errors
async def see_furry_function(
        matcher: Matcher,
        event: MessageEvent,
        args: Message = CommandArg()):
    if "#" not in str(args) and str(args) != "":
        await matcher.finish()
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
        "qq": "1097740481",  # 用户唯一标识
        "timestamp": int(time.time())  # 当前时间戳
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    logger.debug(f"生成的 JWT: {token}")
    logger.debug(f"最终生成的params数据：{params_data}")
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f"{see_furry_baseURL}/{splice_url}",
                                         json={"qq": payload["qq"], "token": token},
                                         params=params_data,
                                         timeout=None)
    except NetworkError:
        await matcher.finish(MessageSegment.reply(event.message_id) + "网络异常，无法访问鉴毛API，请稍后再试。")
    data = response.json()
    if response.status_code != 200:
        text = data['message']
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"鉴毛API返回：{text}[HTTP {response.status_code}]，请稍后再试。")
    data = data['data']
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