# 导入标准库
import time

from src.plugins import utils
from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    Message,
    Bot,
)
from nonebot.matcher import Matcher
from nonebot.plugin import on_command
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from pathlib import Path
from .tools import (
    render_schedule_image,
    group_by_year_month,
    get_event_list,
) 
from src.plugins.utils import get_api_httpx


# 定义Data存放路径并作为全局变量使用
opendata = Path.cwd()
timeout = None
DATA_PATH = opendata / 'data' / 'Furry_System' / 'Upload'
FONT_PATH = opendata / 'data' / 'MiSans-Demibold.ttf'
PIC_URL = opendata / 'data' / 'temp.jpg'
PROCESSED_IMAGES_PATH = opendata / 'data' / 'Furry_System' / 'processed_images'


# FurryFusion 兽聚汇总服务
furryfusion_list = on_command(
    "今年兽聚", aliases={"兽聚列表", "兽聚汇总"}, priority=10, block=True)
furryfusion_check = on_command("兽聚查询", block=True)
furryfusion_countdown = on_command("兽聚倒计时", block=True)
furryfusion_quick_information = on_command("兽聚快讯#", block=True)
furryfusion_information = on_command("兽聚信息", aliases={"兽聚详情"}, block=True)



@furryfusion_list.handle()
async def furryfusion_list_handler(matcher:Matcher):
    events = await get_event_list()
    if events is False:
        await matcher.finish("无法获取活动列表，请稍后再试。")
    groups = group_by_year_month(events)
    img = render_schedule_image(groups)

    # 保存临时文件
    file_path = Path.cwd() / "schedule.png"
    img.save(file_path)

    await matcher.finish(MessageSegment.image(f"file:///{file_path}"))


@furryfusion_check.handle()
@utils.handle_errors
async def furryfusion_check_handler(matcher: Matcher, event: MessageEvent, bot: Bot, args: Message = CommandArg()):
    message = str(args)
    if "省" in message and "市" in message:
        await matcher.send("不应带有省+市字样，将取市作为查找依据。")
        message = message.split("市")
        message = message[1]
    elif "省" in message:
        message = message.split("省")
        message = message[0]
    elif "市" in message:
        message = message.split("市")
        message = message[0]
    logger.info(message)
    response = await get_api_httpx(f"service/screen?content={message}&mode=address", service="furryfusion", request_mode="get")
    city_list = response['data']['history']['province']
    final_list = []
    logger.info(message)
    logger.info(city_list)
    user_qq = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    if city_list == []:
        city_list = response['data']['history']['city']
    for i in range(0, len(city_list)):
        title = city_list[i]['title']
        name = city_list[i]['name']
        image_url = city_list[i]['image']
        group_list = city_list[i]['groups']
        group_str = ''
        if group_list != ['']:
            for j in range(0, len(group_list)):
                group_str += f"{group_list[j]}、"
        else:
            group_str = "尚未获取到已登记的官方群聊信息"
        time_start = city_list[i]['time_start']
        time_end = city_list[i]['time_end']
        time_day = city_list[i]['time_day']
        address = city_list[i]['address']
        text = f"展会名称：{title}\n举办展会主题：{name}\n官方群聊：{group_str}\n举办地点：{address}\n举办总时长：{time_day}天\n【{time_start}~{time_end}】"
        make_text = await utils.batch_get(text, image_url, event.self_id, nickname)
        final_list.append(make_text)
    if final_list == []:
        await matcher.finish(MessageSegment.reply(event.message_id) + "未查找到任何兽聚。")
    else:
        # logger.info(final_list)
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)

@furryfusion_countdown.handle()
@utils.handle_errors
async def furryfusion_countdown_handler(matcher: Matcher, event: MessageEvent, bot: Bot):
    data = await get_api_httpx("service/countdown", service="furryfusion", request_mode="get")
    data = data['data']
    state_text_list = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    final_list = []
    user_qq = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    for i in range(0, len(data)):
        title = data[i]['title']
        name = data[i]['name']
        state = data[i]['state']
        address_province = data[i]['address_province']
        address_city = data[i]['address_city']
        address = f"{address_province}省 {address_city}市"
        time_day = data[i]['time_day']
        time_start = data[i]['time_start']
        time_end = data[i]['time_end']
        time_surplus = data[i]['time_surplus']
        state = state_text_list[state]
        text = f"展会名称：{title}\n举办展会主题：{name}\n当前展会状态：{state}\n举办地点：{address}\n举办\
总时长：{time_day}天\n【{time_start}~{time_end}】\n距离展会开始还有：{time_surplus + 1}天\n该倒计时天数已加上今天"
        make_text = await utils.batch_get(f"{text}\n生成时间：{time.strftime('%Y-%m-%d %a %H:%M:%S', time.localtime())}",
                                          None, event.self_id, nickname)
        final_list.append(make_text)
    # logger.info(final_list)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)


@furryfusion_quick_information.handle()
@utils.handle_errors
async def furryfusion_quick_information_handler(matcher: Matcher, event: MessageEvent, bot: Bot,
                                                 args: Message = CommandArg()):
    args = int(str(args))
    response = await get_api_httpx("service/activity", service="furryfusion", request_mode="get")
    code = response['code']
    msg = response['rel']
    if code != "OK":
        await matcher.finish(f"遇到错误：{msg}[Code={code}]")
    data = response['data']
    number = args - 1
    final_list = []
    information = data[number]
    title = information['title']
    name = information['name']
    image = information['image']
    state = information['state']
    state_text_list = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    state_text = state_text_list[state]
    group_list = information['groups']
    group_str = ''
    if group_list != ['']:
        for j in range(0, len(group_list)):
            group_str += f"{group_list[j]}、"
    else:
        group_str = "尚未获取到已登记的官方群聊信息"
    address = information['address']
    time_day = information['time_day']
    time_start = information['time_start']
    time_end = information['time_end']
    text = f"展会名称：{title}\n举办展会主题：{name}\n展会状态：{state_text}\n官方群聊：{group_str}\n举办地点：{address}\n举办总时长：{time_day}天\n【{time_start}~{time_end}】\n推荐结合“今年兽聚”命令使用"
    user_qq = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    make_text = await utils.batch_get(text, image, event.self_id, nickname)
    final_list.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)


@furryfusion_information.handle()
@utils.handle_errors
async def furryfusion_information_handler(matcher: Matcher, event: MessageEvent, bot: Bot, args: Message = CommandArg()):
    args = str(args)
    final_list = []
    response = await get_api_httpx(f"service/details?title={args}", service="furryfusion", request_mode="get")
    code = response['code']
    if code != "OK" or args == "":
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "好像没有找到你想要查找的兽聚或你要查找的兽聚是个空值呢qwq...")
    data = response['data']
    title = data['title']
    url = data['url']
    group_list = data['groups']
    group_str = ''
    correlation_str = ''
    if group_list != ['']:
        for i in range(0, len(group_list)):
            group_str += f"{group_list[i]}、"
            logger.info(i)
    else:
        group_str = "尚未获取到已登记的官方群聊信息"
    image = data['image']
    brief = data['brief']
    correlation = data['correlation']
    if correlation != ['']:
        for i in range(0, len(correlation)):
            correlation_str += f"{correlation[i]}、"
    else:
        correlation_str = "尚未获取到具有关联性的其他品牌名称"
    state_text_list = ["正常运行", "举办预告中", "宣告解散、停止运行", "信息失联"]
    state_text = state_text_list[data['state']]
    ltd_name, ltd_url = data['ltd']['name'], data['ltd']['url']
    bilibili_name, bilibili_url = data['bilibili']['name'], data['bilibili']['url']
    weibo_name, weibo_url = data['weibo']['name'], data['weibo']['url']
    mail = data['mail']['name']
    if correlation_str == "":
        correlation_str = "暂未获取到数据"
    if url == "":
        url = "暂未获取到数据"
    if ltd_name == "":
        ltd_name, ltd_url = "暂未获取到数据", "暂未获取到数据"
    if weibo_name == "":
        weibo_name, weibo_url = "暂未获取到数据", "暂未获取到数据"
    if mail == "":
        mail = "暂未获取到数据"
    text = f"""展会名称：{title}
展会介绍：{brief}
展会状态：{state_text}
展会官网：{url}
工商主体：{ltd_name}，URL：{ltd_url}
bilibili：{bilibili_name}，URL：{bilibili_url}
官方微博：{weibo_name}，URL：{weibo_url}
官方邮箱：{mail}
官方群聊：{group_str}
具有关联性的其他品牌名称：{correlation_str}
下面为该展会举办的部分活动/线下兽聚"""
    user_qq = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    make_text = await utils.batch_get(text, image, event.self_id, nickname)
    final_list.append(make_text)
    info = response['info']
    info_state_list_str = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    for i in range(0, len(info)):
        info_title = info[i]['title']
        info_name = info[i]['name']
        info_image = info[i]['image']
        info_state = info_state_list_str[info[i]['state']]
        info_address = info[i]['address']
        info_time_start = info[i]['time_start']
        info_time_end = info[i]['time_end']
        text = f"""第{i + 1}条：
举办展会：{info_title}
活动名称：{info_name}
活动举办状态：{info_state}
活动举办地点：{info_address}
举办时间：【{info_time_start}~{info_time_end}】"""
        make_text = await utils.batch_get(text, info_image, event.self_id, nickname)
        final_list.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)