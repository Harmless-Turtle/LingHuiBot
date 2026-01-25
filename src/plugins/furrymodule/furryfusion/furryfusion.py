# 导入所需的库和模块
import os, time, httpx
from src.plugins import utils
from types import SimpleNamespace
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
    get_event_list
)


# 定义Data存放路径并作为全局变量使用
opendata = Path.cwd()
timeout = None
Data_Path = opendata / 'data' / 'Furry_System' / 'Upload'
Font_Path = opendata / 'data' / 'MiSans-Demibold.ttf'
Pic_URL = opendata / 'data' / 'temp.jpg'
allin_pic_prerequisite_path = opendata / 'data' / 'Furry_System' / 'processed_images'


# FurryFusion 兽聚汇总服务
furryfusion_list = on_command(
    "今年兽聚", aliases={"兽聚列表", "兽聚汇总"}, priority=10, block=True)
furryfusion_check = on_command("兽聚查询", block=True)
furryfusion_countdown = on_command("兽聚倒计时", block=True)
furryfusion_quick_information = on_command("兽聚快讯#", block=True)
furryfusion_information = on_command("兽聚信息", aliases={"兽聚详情"}, block=True)



@furryfusion_list.handle()
async def FurryfusionListFunction(matcher:Matcher,arg: Message = CommandArg()):
    events = await get_event_list()
    if events is False:
        await matcher.finish("无法获取活动列表，请稍后再试。")
    groups = group_by_year_month(events)
    img = render_schedule_image(groups)

    # 保存临时文件
    file_path = os.path.join(os.getcwd(), "schedule.png")
    img.save(file_path)

    await matcher.finish(MessageSegment.image(f"file:///{file_path}"))


@furryfusion_check.handle()
@utils.handle_errors
async def FurryFusion_Check_Function(matcher: Matcher, event: MessageEvent, bot: Bot, args: Message = CommandArg()):
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
    a = httpx.get(
        f"https://api.furryfusion.net/service/screen?content={message}&mode=address", timeout=timeout).json()
    Code = a['code']
    msg = a['rel']
    city_list = a['data']['history']['province']
    List = []
    logger.info(message)
    logger.info(city_list)
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    if city_list == []:
        city_list = a['data']['history']['city']
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
        List.append(make_text)
    if List == []:
        await matcher.finish(MessageSegment.reply(event.message_id) + "未查找到任何兽聚。")
    else:
        # logger.info(List)
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)


@furryfusion_countdown.handle()
@utils.handle_errors
async def FurryFusion_countdown_Function(matcher: Matcher, event: MessageEvent, bot: Bot):
    data = httpx.get(
        "https://api.furryfusion.net/service/countdown", timeout=timeout).json()
    code = data['code']
    msg = data['rel']
    data = data['data']
    State_text_List = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    List = []
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    for i in range(0, len(data)):
        title = data[i]['title']
        name = data[i]['name']
        State = data[i]['state']
        address_province = data[i]['address_province']
        address_city = data[i]['address_city']
        address = f"{address_province}省 {address_city}市"
        time_day = data[i]['time_day']
        time_start = data[i]['time_start']
        time_end = data[i]['time_end']
        time_surplus = data[i]['time_surplus']
        State = State_text_List[State]
        text = f"展会名称：{title}\n举办展会主题：{name}\n当前展会状态：{State}\n举办地点：{address}\n举办\
总时长：{time_day}天\n【{time_start}~{time_end}】\n距离展会开始还有：{time_surplus + 1}天\n该倒计时天数已加上今天"
        make_text = await utils.batch_get(f"{text}\n生成时间：{time.strftime('%Y-%m-%d %a %H:%M:%S', time.localtime())}",
                                          None, event.self_id, nickname)
        List.append(make_text)
    # logger.info(List)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)


@furryfusion_quick_information.handle()
@utils.handle_errors
async def FurryFusion_Quick_Information_Function(matcher: Matcher, event: MessageEvent, bot: Bot,
                                                 args: Message = CommandArg()):
    args = int(str(args))
    Get = httpx.get(
        "https://api.furryfusion.net/service/activity", timeout=timeout).json()
    code = Get['code']
    msg = Get['rel']
    if code != "OK":
        await matcher.finish(f"遇到错误：{msg}[Code={code}]")
    data = Get['data']
    Number = args - 1
    List = []
    Information = data[Number]
    title = Information['title']
    name = Information['name']
    image = Information['image']
    state = Information['state']
    State_Text_List = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    State_Text = State_Text_List[state]
    group_list = Information['groups']
    group_str = ''
    if group_list != ['']:
        for j in range(0, len(group_list)):
            group_str += f"{group_list[j]}、"
    else:
        group_str = "尚未获取到已登记的官方群聊信息"
    address = Information['address']
    time_day = Information['time_day']
    time_start = Information['time_start']
    time_end = Information['time_end']
    text = f"展会名称：{title}\n举办展会主题：{name}\n展会状态：{State_Text}\n官方群聊：{group_str}\n举办地点：{address}\n举办总时长：{time_day}天\n【{time_start}~{time_end}】\n推荐结合“今年兽聚”命令使用"
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    make_text = await utils.batch_get(text, image, event.self_id, nickname)
    List.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)


@furryfusion_information.handle()
@utils.handle_errors
async def FurryFusion_Information_Function(matcher: Matcher, event: MessageEvent, bot: Bot,
                                           args: Message = CommandArg()):
    args = str(args)
    List = []
    a = httpx.get(
        f"https://api.furryfusion.net/service/details?title={args}", timeout=timeout).json()
    msg = a['rel']
    code = a['code']
    if code != "OK" or args == "":
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "好像没有找到你想要查找的兽聚或你要查找的兽聚是个空值呢qwq...")
    data = a['data']
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
    State_List_str = ["正常运行", "举办预告中", "宣告解散、停止运行", "信息失联"]
    State = State_List_str[data['state']]
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
展会状态：{State}
展会官网：{url}
工商主体：{ltd_name}，URL：{ltd_url}
bilibili：{bilibili_name}，URL：{bilibili_url}
官方微博：{weibo_name}，URL：{weibo_url}
官方邮箱：{mail}
官方群聊：{group_str}
具有关联性的其他品牌名称：{correlation_str}
下面为该展会举办的部分活动/线下兽聚"""
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    make_text = await utils.batch_get(text, image, event.self_id, nickname)
    List.append(make_text)
    info = a['info']
    Info_State_List_str = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    for i in range(0, len(info)):
        Info_title = info[i]['title']
        Info_name = info[i]['name']
        Info_image = info[i]['image']
        Info_state = Info_State_List_str[info[i]['state']]
        Info_address = info[i]['address']
        Info_time_start = info[i]['time_start']
        Info_time_end = info[i]['time_end']
        text = f"""第{i + 1}条：
举办展会：{Info_title}
活动名称：{Info_name}
活动举办状态：{Info_state}
活动举办地点：{Info_address}
举办时间：【{Info_time_start}~{Info_time_end}】"""
        make_text = await utils.batch_get(text, Info_image, event.self_id, nickname)
        List.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)
