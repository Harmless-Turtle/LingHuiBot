# 标准库
import asyncio, os, shutil, time, httpx, math

from src.plugins import utils
# 第三方库
from types import SimpleNamespace
from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
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
from PIL import Image, ImageFont

from src.plugins.utils import get_config_item

# FurryFusion 兽聚汇总服务
FurryFusion_List = on_command(
    "今年兽聚", aliases={"兽聚列表", "兽聚汇总"}, priority=10, block=True)
FurryFusion_Check = on_command("兽聚查询", block=True)
FurryFusion_countdown = on_command("兽聚倒计时", block=True)
FurryFusion_Quick_Information = on_command("兽聚快讯#", block=True)
FurryFusion_Information = on_command("兽聚信息", aliases={"兽聚详情"}, block=True)

@FurryFusion_List.handle()
@utils.handle_errors
async def furry_meetup_list(matcher: Matcher, event: MessageEvent, bot: Bot):
    a = httpx.get(
        "https://api.furryfusion.net/service/activity", timeout=timeout).json()
    meetup_info = a['data']
    state_name_list = ['活动已结束', "活动正在预告中", "售票中", "活动正在举行", "活动已取消"]
    furry_fusion_results = []
    user_qq = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    try:
        img = f"{allin_pic_prerequisite_path}/image_1.png"
        file_stat = os.stat(img)
        if int(time.time()) - file_stat.st_mtime >= 86400:
            await bot.send(event, MessageSegment.reply(
                event.message_id) + "图库似乎已过期，本次操作将重新同步数据，所以将需要一些时间，请耐心等待。")
    except:
        await bot.send(event, MessageSegment.reply(
            event.message_id) + "图库似乎还没有生成，本次操作将重新同步数据，所以将需要一些时间，请耐心等待。")
    furry_fusion_results.append(await utils.batch_get(
        "通过命令“兽聚快讯#<这里输入要查询的兽聚信息条数，仅需要数字即可。>”可以获取指定项目的详细信息", None,
        event.self_id, nickname))
    for i in range(0, len(meetup_info)):
        title = meetup_info[i]['title']  # 兽聚主体名称
        name = meetup_info[i]['name']  # 当次兽聚的主题名称
        state = state_name_list[meetup_info[i]['state']]  # 获取展会动态
        address = meetup_info[i]['address']  # 当次兽聚的举办地址
        time_day = meetup_info[i]['time_day']
        time_start = meetup_info[i]['time_start']
        time_end = meetup_info[i]['time_end']
        image = meetup_info[i]['image']
        text = f"第{i + 1}条兽聚信息：\n展会举办者：{title}\n兽聚主题：{name}\n当前展会状态：{state}\n举办地点：{address}\n举办时间：共{time_day}天\n【{time_start}~{time_end}】"
        img = f"{allin_pic_prerequisite_path}/image_{i + 1}.png"
        try:
            file_stat = os.stat(img)
        except:
            file_stat = SimpleNamespace(st_mtime=0)
        if int(time.time()) - file_stat.st_mtime >= 86400:
            logger.warning(f"文件 image_{i + 1}.png 似乎已过期或未生成，重新生成中。")
            img = await utils.furry_fusion_picture_handle(image, i + 1, text)
            logger.info(f"第{i + 1}条兽聚信息已被处理。")
        make_text = await utils.batch_get(text, img, user_qq, nickname)

        furry_fusion_results.append(make_text)
    # 合并图片
    furryfusion_allin_pic_path = [f"{allin_pic_prerequisite_path}/image_{i}.png" for i in
                                  range(1, len(os.listdir(allin_pic_prerequisite_path)))]
    columns = 1  # 设置列数
    background_color = (255, 255, 255)  # 设置背景颜色为白色

    IMG_WIDTH, IMG_HEIGHT = 350, 130

    # 计算行列数
    image_count = len(furryfusion_allin_pic_path)
    rows = math.ceil(image_count / columns)

    # 创建空白画布 (RGBA模式支持透明背景)
    canvas = Image.new(
        mode='RGB',
        size=(columns * IMG_WIDTH, rows * IMG_HEIGHT),
        color=background_color
    )

    # 遍历并粘贴图片
    for index, img_path in enumerate(furryfusion_allin_pic_path):
        # 计算当前图片位置
        row = index // columns
        col = index % columns

        # 打开图片并确保为RGB模式
        with Image.open(img_path) as img:
            img = img.convert('RGB')
            if img.size != (IMG_WIDTH, IMG_HEIGHT):
                img = img.resize((IMG_WIDTH, IMG_HEIGHT), Image.LANCZOS)

            # 计算粘贴坐标
            x = col * IMG_WIDTH
            y = row * IMG_HEIGHT
            canvas.paste(img, (x, y))

    # 保存结果
    canvas.save(f"{allin_pic_prerequisite_path}/allin.jpg")
    logger.success(f"拼接完成! 生成图片: {allin_pic_prerequisite_path}/allin.jpg")
    logger.info(f"布局: {columns}列 x {rows}行 | 总分辨率: {canvas.size[0]}x{canvas.size[1]}")
    await matcher.finish(MessageSegment.reply(event.message_id) + "输出完毕~" + MessageSegment.image(
        f"{allin_pic_prerequisite_path}/allin.jpg"))


@FurryFusion_Check.handle()
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


@FurryFusion_countdown.handle()
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


@FurryFusion_Quick_Information.handle()
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


@FurryFusion_Information.handle()
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
