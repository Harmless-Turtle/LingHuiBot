import glob

from nonebot import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent,Bot
from nonebot.internal.matcher import Matcher

from src.plugins.utils import handle_errors,batch_get
from ..commands import (
furryfusion_list,
furryfusion_check,
furryfusion_countdown,
)
from .tools import get_api,download_image
from src.plugins.Exceptions import FurryFusionError
from ..check_file import fec_images_path

@furryfusion_list.handle()
@handle_errors
async def _(
        bot:Bot,
        matcher: Matcher,
        event:GroupMessageEvent,
):
    # 发起请求
    data = await get_api("city")
    # 加入错误日志
    if not data:
        raise FurryFusionError()
    # 获取源数据
    raw_data = data['pageProps']['regionGroups']['china']
    activing_furry = []
    # 只获取存在事件的兽聚
    for item in raw_data:
        if item['event']:
            activing_furry.append(item)
    slug_list = []
    # 获取所有兽聚的slug
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
        data = await get_api(i)
        organization = data['pageProps']['organization']
        name = organization['name']
        description = organization['description']
        status = organization['status']
        if organization['logoUrl']:
            downloadURL = "https://images.furrycons.cn/" + organization['logoUrl']
            if not glob.glob(str(fec_images_path / f"{name}.png")):
                logger.info(f"[FEC] 下载 {name}.png")
                logoURL = await download_image(downloadURL, fec_images_path / f"{name}.png")
            else:
                logger.info(f"[FEC] 已存在 {name}.png，跳过下载")
                logoURL = fec_images_path / f"{name}.png"
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
        text = f"""名称：{name}
状态：{status}
简介：{description}
QQ群：{qq_group}
邮箱：{contactMail}
官网：{website}
Bilibili：{bilibili}
微博：{weibo}
Twitter：{twitter}
小红书：{rednote}
Wikifur：{wikifur}
Facebook：{facebook}
创立时间：{creationTime}"""
        make_text = await batch_get(text, logoURL,event.user_id,nickname)
        final_list.append(make_text)
        if len(final_list) >= 30:
            logger.info(f"[FEC] 发送 {len(final_list)} 条 Furry聚会信息")
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)
            final_list = []
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)