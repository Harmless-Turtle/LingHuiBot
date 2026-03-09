import time
from pathlib import Path

from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    Message,
    Bot,
    GroupMessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from .tools import (
    render_schedule_image,
    group_by_year_month,
    get_event_list,
    add_custom_footer
)
from ..commands import (
    furryfusion_list,
    furryfusion_check,
    furryfusion_countdown,
    furryfusion_quick_information,
    furryfusion_information
)
from ...utils import get_api_httpx, handle_errors, batch_get


@furryfusion_list.handle()
async def furry_fusion_list_handler(matcher: Matcher):
    events = await get_event_list()
    if events is False:
        await matcher.finish("无法获取活动列表，请稍后再试。")
    groups = group_by_year_month(events)
    img = render_schedule_image(groups)
    img = add_custom_footer(img)

    # 保存临时文件
    file_path = Path.cwd() / "schedule.png"
    img.save(file_path)

    await matcher.finish(MessageSegment.image(f"file:///{file_path}"))


@furryfusion_check.handle()
@handle_errors
async def furry_fusion_check_handler(matcher: Matcher, event: GroupMessageEvent, bot: Bot,
                                     args: Message = CommandArg()):
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
    response = await get_api_httpx(
        f"service/screen?content={message}&mode=address",
        service="furryfusion",
        request_mode="get"
    )
    city_list = response['data']['history']['province']
    final_list = []
    logger.info(message)
    logger.info(city_list)
    user_qq = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    if not city_list:
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
        text = (
            f"展会名称：{title}\n"
            f"举办展会主题：{name}\n"
            f"官方群聊：{group_str}\n"
            f"举办地点：{address}\n举办总时长：{time_day}天\n"
            f"【{time_start}~{time_end}】"
        )
        make_text = await batch_get(text, image_url, event.self_id, nickname)
        final_list.append(make_text)
    if not final_list:
        await matcher.finish(MessageSegment.reply(event.message_id) + "未查找到任何兽聚。")
    else:
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)


@furryfusion_countdown.handle()
@handle_errors
async def furry_fusion_countdown_handler(matcher: Matcher, event: GroupMessageEvent, bot: Bot):
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
        text = (
            f"展会名称：{title}\n"
            f"举办展会主题：{name}\n"
            f"当前展会状态：{state}\n"
            f"举办地点：{address}\n"
            f"举办总时长：{time_day}天\n"
            f"【{time_start}~{time_end}】\n"
            f"距离展会开始还有：{time_surplus + 1}天\n"
            f"该倒计时天数已加上今天"
        )
        make_text = await batch_get(
            f"{text}\n"
            f"生成时间：{time.strftime('%Y-%m-%d %a %H:%M:%S', time.localtime())}",
            None,
            event.self_id,
            nickname
        )
        final_list.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)
    await matcher.finish()


@furryfusion_quick_information.handle()
@handle_errors
async def furry_fusion_quick_information_handler(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        args: Message = CommandArg()
):
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
    text = (
        f"展会名称：{title}\n"
        f"举办展会主题：{name}\n"
        f"展会状态：{state_text}\n"
        f"官方群聊：{group_str}\n"
        f"举办地点：{address}\n举办总时长：{time_day}天\n"
        f"【{time_start}~{time_end}】\n"
        f"推荐结合“今年兽聚”命令使用"
    )
    user_qq = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    make_text = await batch_get(text, image, event.self_id, nickname)
    final_list.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)


@furryfusion_information.handle()
@handle_errors
async def furry_fusion_information_handler(matcher: Matcher, event: GroupMessageEvent, bot: Bot,
                                           args: Message = CommandArg()):
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
    text = (
        f"展会名称：{title}\n"
        f"展会介绍：{brief}\n"
        f"展会状态：{state_text}\n"
        f"展会官网：{url}\n"
        f"工商主体：{ltd_name}，URL：{ltd_url}\n"
        f"bilibili：{bilibili_name}，URL：{bilibili_url}\n"
        f"官方微博：{weibo_name}，URL：{weibo_url}\n"
        f"官方邮箱：{mail}\n"
        f"官方群聊：{group_str}\n"
        f"具有关联性的其他品牌名称：{correlation_str}\n"
        f"下面为该展会举办的部分活动/线下兽聚\n"
    )
    user_qq = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    make_text = await batch_get(text, image, event.self_id, nickname)
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
        text = (
            f"第{i + 1}条：\n"
            f"举办展会：{info_title}\n"
            f"活动名称：{info_name}\n"
            f"活动举办状态：{info_state}\n"
            f"活动举办地点：{info_address}\n"
            f"举办时间：【{info_time_start}~{info_time_end}】"
        )
        make_text = await batch_get(text, info_image, event.self_id, nickname)
        final_list.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)
