import os
import shutil
import time
from pathlib import Path

import httpx
from PIL import ImageFont
from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message,
    Bot
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command

from src.plugins import utils
from src.plugins.utils import get_api_httpx,ensure_files_exist

# 定义全局变量
login_cookie = {}
timeout = None
count = 0
set_count = 0
API_BASE_URL = "https://cloud.foxtail.cn/api"

# 定义Data存放路径并作为全局变量使用
opendata = Path.cwd()
data_path = opendata / 'data' / 'furry_system' / 'upload'
font_path = opendata / 'data' / 'MiSans-Demibold.ttf'
temp_image_path = opendata / 'data' / 'furry_system' / 'temp.jpg'
allin_pic_prerequisite_path = opendata / 'data' / 'furry_system' / 'processed_images'

# 校验文件
ensure_files_exist(
    file_path=[
        data_path,
        font_path,
        temp_image_path,
        allin_pic_prerequisite_path
    ],
    description="furry_pic模块"
)


# 定义事件响应器

# Foxtail-Furry 兽云祭服务
furry_random = on_command(
    "来只兽兽", aliases={"来只毛", "来只", "来只兽"}, priority=10, block=True)  # 随机兽图
furry_picture = on_command("指定", aliases={"指定#"}, priority=10, block=True)  # 指定兽图
furry_list = on_command(
    "查列表", aliases={"查列表#", "查兽兽"}, priority=10, block=True)  # 获取列表
furry_status = on_command(
    "兽图状态", aliases={"兽图状态#"}, priority=10, block=True)  # 兽图状态
service_status = on_command(
    "服务器状态", aliases={"兽云祭信息", "兽云祭状态", "服务状态"}, priority=10, block=True)  # 获取服务器信息
# See_Furry = on_command("鉴毛")
# 投图审核系统->仅NoneBot SUPERUSER组可用
check_upload = on_command(
    "待审核列表", aliases={"审核列表", "上传列表"}, priority=100, block=True, permission=SUPERUSER)  # 获取审核列表
check_upload_decide = on_command(
    "同意上传#", aliases={"同意上载#", "拒绝上传#", "拒绝上载#"}, priority=99, block=True,
    permission=SUPERUSER)  # 决定是否上传
# Batch_Check = on_command("批量审核",aliases={"批量上传"},priority=98,block=True,permission=SUPERUSER)
upload_clear = on_command("清空上传数据", aliases={"清除上传"}, permission=SUPERUSER)


# login_account = on_command("登录Fur",permission=SUPERUSER)

@furry_random.handle()
@utils.handle_errors
async def random_furry_image(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    if args == "":
        data = await get_api_httpx("function/random", service="furry")
    else:
        try:
            data = await get_api_httpx(f"function/pictures?picture={int(args)}&model=1", service="furry")
        except ValueError:
            data = await get_api_httpx(f"function/random?name={args}", service="furry")
    code = data["code"]  # 获取数据中的code变量，即状态码
    msg = data["msg"]  # 获取数据中的msg变量，即信息
    if code == "20600":
        url = data['url']
        name = data['name']
        suggest = data['suggest']  # 获取download字段中suggest变量，即该图片的留言信息。
        if suggest != "":  # 如果留言不为空
            suggest = f"它的留言是“{suggest}”\n"
        pic_id = data['id']  # 获取download字段中的id变量，即该图片的数字id
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"这只兽兽叫“{name}”~\n{suggest}图片码为：{pic_id}\n" + MessageSegment.image(url))
    elif code != "20900":  # 如果状态码不为20900（即获取失败）
        await matcher.finish(MessageSegment.reply(event.message_id) + f"好像哪里不对...？\n错误信息：{msg}[code:{code}]")
    data = data['picture']  # 获取data中的picture变量，即图片详细信息
    picture = data['picture']  # 获取data字段中的picture变量，即图片唯一识别码
    # 发起POST请求以获取数据，将数据传入给download变量，转为Json格式
    download = await get_api_httpx(f"function/pictures?picture={picture}&model=", service="furry", request_mode="post")
    name = download['name']  # 获取download字段中的name变量，即该兽兽的名字
    pic_id = download['id']  # 获取download字段中的id变量，即该图片的数字id
    url = download['url']  # 获取download字段中的url变量，即该图片的临时URL
    suggest = download['suggest']  # 获取download字段中suggest变量，即该图片的留言信息。
    if suggest != "":  # 如果留言不为空
        suggest = f"它的留言是：“{suggest}”\n"
    # 输出正常的信息。
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"这只兽兽叫“{name}”~\n{suggest}图片码为：{pic_id}\n" + MessageSegment.image(url))


# 使用PicFurry响应器的handle装饰器装饰函数PicFur_handle_function

@furry_picture.handle()
@utils.handle_errors
async def pic_fur_handle_function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    sid = str(args)
    if sid == "":
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"凌辉似乎没有获取到要查找的图片qwq...麻烦你再看看有没有正确使用呢owo")
    else:
        # 发起Get请求获取一张指定sid的毛图
        data = await get_api_httpx(f"function/pictures?picture={sid}&model=1", service="furry", request_mode="get")
        code = data["code"]  # 获取数据中的code变量，即状态码
        msg = data["msg"]  # 获取数据中的msg变量，即信息
        if code != "20600":  # 如果状态码不为20600（即获取失败）----->↓
            # 则输出错误
            await matcher.finish(
                MessageSegment.reply(event.message_id) + f"好像哪里不对...？\n错误信息：{msg}[code:{code}]")
        else:  # 如果状态码为20600（即获取成功），则执行else下命令（处理数据）
            url = data['url']  # 获取data中的picture变量，即图片详细信息
            pic_id = data['id']  # 获取data字段中的picture变量，即图片唯一识别码
            name = data['name']  # 获取data字段中的name变量，即图片名称
            suggest = data['suggest']
            if suggest != "":  # 如果留言不为空
                suggest = f"它的留言是：“{suggest}”\n"
            # 输出正常的信息。
            await matcher.finish(MessageSegment.reply(
                event.message_id) + f"这只兽兽叫“{name}”~\n{suggest}图片码为：{pic_id}\n" + MessageSegment.image(url))


@furry_list.handle()
@utils.handle_errors
async def furry_list(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    name = str(args)
    original_data = await get_api_httpx(f"function/pulllist?type=&name={name}", service="furry", request_mode="get")
    msg = original_data['msg']
    code = original_data['code']
    data = original_data['open']
    list_length = len(data)
    items = []
    if code != "20700":
        await matcher.finish(MessageSegment.reply(event.message_id) + f"错误，{msg}[code={code}]")
    else:
        if list_length == 0:
            await matcher.finish(
                MessageSegment.reply(event.message_id) + f"服务器回报：{msg}。但并没有获取到任何数据，请检查名称是否正确")
        text = ""
        user_qq = event.user_id
        stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        items.append(await utils.batch_get(f"共获取到了{list_length}条消息，下面为列表。", None, event.self_id, nickname))
        for i in range(0, list_length):
            now_data = data[i]
            name = now_data['name']
            pic_id = now_data['id']
            suggest = now_data['suggest']
            if suggest == "":
                suggest = "该图片暂无留言"
            temp = f"名字：{name}\nid：{pic_id}\n留言：{suggest}\n=======================\n"
            make_text = await utils.batch_get(temp, None, event.self_id, nickname)
            items.append(make_text)
            text += temp
        if list_length < 100:
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=items, time_noend=True)
            await matcher.finish()
        await bot.call_api("send_group_forward_msg", group_id=event.group_id,
                           message=f"{MessageSegment.reply(event.message_id)}获取到的信息数量过多，将使用图片输出。",
                           time_noend=True)

        # 优化后的图片生成部分
        try:
            font = ImageFont.truetype(font_path, size=30)
        except (OSError,ValueError):
            font = ImageFont.load_default()

        text_lines = [line for line in text.split('\n') if line.strip() != '']
        image = utils.generate_text_image(text_lines, font)
        image.save(temp_image_path)
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"共获取到了{list_length}条消息：" + MessageSegment.image(
                temp_image_path))


@furry_status.handle()
@utils.handle_errors
async def furry_status_function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    get_resp = await get_api_httpx(f"function/pictures?picture={args}&model=1", service="furry", request_mode="get")
    examine_number, type_number = get_resp['examine'], get_resp['power']
    examine_name_list, type_name_list = [
        "待审核", "已通过审核", "已被审核拒绝"], ['设定', '毛图', '插画']
    name, pic_id, examine, pic_type = get_resp['name'], get_resp["id"], examine_name_list[examine_number], \
        type_name_list[type_number]
    await matcher.finish(MessageSegment.reply(event.message_id) + f"""=========FurBot=========
您查询的id为{pic_id}的图片信息如下：
图片名字：{name}
审核结果：{examine}
图片类型：{pic_type}
=======LingHuiBot=======""")


@service_status.handle()
@utils.handle_errors
async def service_furry_status(matcher: Matcher, event: MessageEvent):
    response = await get_api_httpx("information/feedback", service="furry", request_mode="get")
    code, msg = response['code'], response['msg']
    if code != "40000":
        await matcher.finish(MessageSegment.reply(event.message_id) + f"平台返回：{msg}[code={code}]")
    else:
        running_time, examine, power, atlas, total = response['time']['count'], response['examine']['count'], response[
            'power']['count'], response['atlas']['count'], response['total']['count']
        await matcher.finish(MessageSegment.reply(event.message_id) + f"""平台返回：
==========FurBot==========
运行时长：{running_time}天
待审核图片数：{examine}
已公开图片数：{power}
已有图片数：{atlas}
总调用次数：{total}
-->由兽云祭API提供服务支持
========Service Status========""")


# @See_Furry.handle()
# async def See_Furry_Function(matcher:Matcher,bot:Bot,event: MessageEvent,args:Message = CommandArg()):
#     try:
#         a = httpx.get(
#             "https://atlas.foxtail.cn/api/function/obtain",timeout=timeout).json()
#         if args != None:
#             if str(args).isdigit():
#                 a = httpx.get(
#                 f"https://atlas.foxtail.cn/api/function/obtain?data={int(str(args))}",timeout=timeout).json()
#             else:
#                 await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=f"{MessageSegment.reply(event.message_id)}输入类型错误，将随机获取。", time_noend=True)
#         data = a['Data']
#         Number = data['Number']
#         name = data['name']
#         Atlas = data['Atlas']
#         await matcher.finish(MessageSegment.reply(event.message_id)+f"获取完成\nid：{Number}\n名字：{name}"+MessageSegment.image(Atlas))
#     except MatcherException:  # 执行完成，接住抛出的FinishedException异常以结束本次事件执行
#         # 注：此处必须要接住该异常，否则事件将无法正常结束。
#         raise  # 什么都不需要做，接住就行
#     except Exception as e:
#         e = str(e)
#         if "NetWorkError" in e:
#             raise
#         else:
#             Error()
#             await matcher.finish(f"在运行中遇到未知错误。\n错误已添加至错误日志中，请联系管理员进行检查或提供帮助。")


@check_upload.handle()
@utils.handle_errors
async def check_upload_list(matcher: Matcher, event: GroupMessageEvent, bot: Bot):
    data_list, items = [], []
    data_list = utils.handle_json(Path(data_path) / "Upload_Data.json", 'r')
    if data_list == []:
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前投图待审核列表是空的")
    data_len = len(data_list)
    type_text = ['设定', '毛图', '插画']
    for i in range(data_len):
        name = data_list[i]['name']
        pic_type = int(data_list[i]['type'])
        picture_url = data_list[i]['Picture_URL']
        suggest = data_list[i]['suggest']
        if suggest == '':
            suggest = "未填写留言"
        upload_account = data_list[i]['Upload_account']
        group_id = data_list[i]['group_id']
        text = f"""第{i + 1}条：
上传者：{upload_account}
上传群聊：{group_id}
图片名称：{name}
留言内容：{suggest}
图片类型：{type_text[pic_type]}"""
        user_qq = event.user_id
        stranger_info = await bot.call_api('get_stranger_info', user_id=user_qq, time_noend=True)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        make_text = await utils.batch_get(text, picture_url, event.self_id, nickname)
        items.append(make_text)
    logger.info(items)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=items, time_noend=True)


@check_upload_decide.handle()
@utils.handle_errors
async def check_upload_decision(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    await matcher.send("将通过凌辉Bot内置账户进行处理")
    data_message = event.get_message()
    args = str(args)
    args = args.split("#")
    temp_args = args
    args = int(args[0])
    items = utils.handle_json(Path(data_path) / "Upload_Data.json", 'r')
    logger.info(items)
    logger.info(temp_args)
    if args > len(items):
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "错误：输入的值超出列表项目\n请确认列表项目后重试。")
    if items == []:
        await matcher.finish(MessageSegment.reply(event.message_id) + "遇到问题：似乎没有待审核的图片。")
    data_normal = items[args - 1]
    pic_url = data_normal['Picture_URL']
    time_wait = data_normal['time']
    upload_time = time.localtime(int(time_wait))
    name = data_normal['name']
    pic_type = int(data_normal['type'])
    type_list = ["设定", "毛图", "插画"]
    type_value = type_list[pic_type]
    suggest = data_normal['suggest']
    group_id = int(data_normal['group_id'])
    account = data_normal['Upload_account']
    if suggest == "":
        suggest = "未填写"
    del data_normal['Picture_URL'], data_normal['group_id'], data_normal['Upload_account'], data_normal['time']
    if "拒绝" in str(data_message):
        del items[args - 1]
        utils.handle_json(Path(data_path) / "Upload_Data.json", 'w', items)

        data_message = str(data_message)
        if data_message.count("#") != 2:
            caution = "管理员没有填写"
        else:
            caution = temp_args[1]
        if event.group_id != group_id:
            await bot.call_api("send_group_msg", group_id=group_id, message=f"""凌辉Bot管理员已拒绝了来自{account}的投图请求
拒绝理由：{caution}
【上传时间戳：{time.strftime("%Y-%m-%d %H:%M:%S", upload_time)}】
下面是打回图片的详细信息：
图片名字：{name}
图片类型：{type_value}
图片留言：{suggest}
图片内容：""" + MessageSegment.image(f"{pic_url}"), time_noend=True)
        os.remove(f"{pic_url}")
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"拒绝上载的操作已完成\n传入拒绝理由参数：{caution}")

    with open(f"{pic_url}", 'rb') as f:
        async with httpx.AsyncClient(timeout=timeout) as client:
            a = await client.post(f"{API_BASE_URL}/function/upload", data=data_normal,
                                  files={'file': ('Upload.png', f, 'image/png')})
            a = a.json()
    logger.info(a)
    if a['code'] != '20000':
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"好像没有上传成功呢...？\n{a['msg']}[{a['code']}]")
    msg = a['msg']
    code = a['code']
    pic_id = a['id']
    picture = a['picture']
    if code != "20000":
        await matcher.finish(MessageSegment.reply(event.message_id) + f"错误：{msg}[code={code}]")
    else:
        text = f"""API返回信息：{msg}[code={code}]
======传入参数======
图片名字:{name}
图片类型:{type_value}
图片留言:{suggest}
======服务器数据=======
您的数字id：{pic_id}
您的图片码：{picture}"""
        del items[args - 1]
        utils.handle_json(Path(data_path) / "Upload_Data.json", 'w', items)
        if event.group_id != group_id:
            await bot.call_api("send_group_msg", group_id=group_id, message=f"""凌辉Bot管理员已经同意了来自{account}的投图请求，请等待兽云祭管理员进行审核
上载图片：""" + MessageSegment.image(f"{pic_url}") + f"""数字id：{pic_id}
【上传时间戳：{time.strftime("%Y-%m-%d %H:%M:%S", upload_time)}】""", time_noend=True)
        await bot.call_api("send_group_msg", group_id=event.group_id,
                           message=f"{text}\n上载图片：" + MessageSegment.image(f"{pic_url}"), time_noend=True)
        os.remove(f"{pic_url}")


@upload_clear.handle()
async def clear_upload_data(matcher: Matcher):
    temp_path = data_path / "Upload_Data.json"
    dir_path = data_path / "Batch"
    if os.path.exists(temp_path):
        os.remove(temp_path)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write("[]")
    await matcher.finish("操作已完成。")
