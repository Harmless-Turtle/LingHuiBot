import asyncio
import json


from nonebot import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent,Bot
from nonebot.internal.matcher import Matcher

from src.plugins.utils import handle_errors,batch_get
from ..commands import (
furryfusion_list,
furryfusion_check,
furryfusion_countdown,
)
from .tools import get_api
from src.plugins.Exceptions import FurryFusionError

@furryfusion_list.handle()
@handle_errors
async def _(
        bot:Bot,
        matcher: Matcher,
        event:GroupMessageEvent,
):
    data = await get_api("city")
    if not data:
        raise FurryFusionError()
    raw_data = data['pageProps']['regionGroups']['china']
    activing_furry = []
    for item in raw_data:
        if item['event']:
            activing_furry.append(item)
    if len(activing_furry) > 100:
        await matcher.finish(f"活动的Furry数量过多，无法显示全部。")
    slug_list = []
    for slug in activing_furry:
        slug_event = slug['event']
        for slug_sum in range(0,len(slug_event)):
            slug_organization = slug_event[slug_sum]['event_organization']
            for slug_sum2 in range(0,len(slug_organization)):
                slug_list.append(slug_organization[slug_sum2]['organization']['slug'])
    final_list = []
    stranger_info = await bot.call_api('get_stranger_info', user_id=event.user_id, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    for i in slug_list:
        # await asyncio.sleep(0.3)
        data = await get_api(i)
        organization = data['pageProps']['organization']
        name = organization['name']
        description = organization['description']
        status = organization['status']
        if organization['logoUrl']:
            logoURL = "https://images.furrycons.cn/" + organization['logoUrl']
        else:
            logoURL = None
        qq_group = organization['qqGroup']
        contactMail = organization['contactMail']
        website = organization['website']
        twitter = organization['twitter']
        weibo = organization['weibo']
        bilibili = organization['bilibili']
        rednote = organization['rednote']
        wikifur = organization['wikifur']
        facebook = organization['facebook']
        creationTime = organization['creationTime']
        text = f"""
        名称：{name}\n
        状态：{status}\n
        简介：{description}\n
        QQ群：{qq_group}\n
        邮箱：{contactMail}\n
        官网：{website}\n
        Bilibili：{bilibili}\n
        微博：{weibo}\n
        Twitter：{twitter}\n
        小红书：{rednote}\n
        Wikifur：{wikifur}\n
        Facebook：{facebook}\n
        创立时间：{creationTime}
        """
        make_text = await batch_get(text, logoURL,event.user_id,nickname)
        final_list.append(make_text)
        # TODO：转发消息一直发送失败。
        if len(final_list) > 95:
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)
            final_list = []
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)