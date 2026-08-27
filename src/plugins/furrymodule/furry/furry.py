import os
import random as rd
import shutil
import time
from pathlib import Path

import httpx
import jwt
from httpx import NetworkError
from nonebot import logger, get_driver
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message,
    Bot
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..check_file import (
    FONT_PATH,
    temp_image_path,
    DATA_PATH
)
from ..commands import (
    see_furry,
    furry_random,
    furry_picture,
    furry_list,
    furry_status,
    service_status,
    check_upload,
    check_upload_decide,
    upload_clear
)
from ...utils import (
    get_api_httpx,
    batch_get,
    handle_errors,
    handle_json,
    generate_text_image
)

# 定义全局变量
login_cookie = {}
timeout = None
count = 0
set_count = 0
API_BASE_URL = "https://cloud.foxtail.cn/api"
try:
    see_furry_baseURL = get_driver().config.furry_see_furry
    secret_key = get_driver().config.furry_see_furry_key
except AttributeError:
    see_furry_baseURL = None
    logger.warning("未读取到鉴毛API，鉴毛功能可能不可用！")


@furry_random.handle()
@handle_errors
async def random_furry_image(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    user_message = str(args)
    if user_message == "":
        data = await get_api_httpx("function/random", service="furry")
    else:
        try:
            data = await get_api_httpx(f"function/pictures?picture={int(user_message)}&model=1", service="furry")
        except ValueError:
            data = await get_api_httpx(f"function/random?name={user_message}", service="furry")
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
@handle_errors
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
@handle_errors
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
        items.append(await batch_get(f"共获取到了{list_length}条消息，下面为列表。", None, event.self_id, nickname))
        for i in range(0, list_length):
            now_data = data[i]
            name = now_data['name']
            pic_id = now_data['id']
            suggest = now_data['suggest']
            if suggest == "":
                suggest = "该图片暂无留言"
            temp = f"名字：{name}\nid：{pic_id}\n留言：{suggest}\n=======================\n"
            make_text = await batch_get(temp, None, event.self_id, nickname)
            items.append(make_text)
            text += temp
        if list_length < 100:
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=items, time_noend=True)
            await matcher.finish()
        await bot.call_api("send_group_forward_msg", group_id=event.group_id,
                           message=f"{MessageSegment.reply(event.message_id)}获取到的信息数量过多，将使用图片输出。",
                           time_noend=True)

        # 优化后的图片生成部分
        image = generate_text_image(text, FONT_PATH)
        image.save(temp_image_path)
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"共获取到了{list_length}条消息：" + MessageSegment.image(
                temp_image_path))


@furry_status.handle()
@handle_errors
async def furry_status_function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    data = str(args)
    get_resp = await get_api_httpx(f"function/pictures?picture={data}&model=1", service="furry", request_mode="get")
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
@handle_errors
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
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{see_furry_baseURL}/{splice_url}",
                                         json={"qq": payload["qq"], "token": token},
                                         params=params_data,
                                         timeout=timeout)
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


@check_upload.handle()
@handle_errors
async def check_upload_list(matcher: Matcher, event: GroupMessageEvent, bot: Bot):
    data_list, items = [], []
    data_list = handle_json(Path(DATA_PATH) / "upload_data.json", 'r')
    if not data_list:
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前投图待审核列表是空的")
    data_len = len(data_list)
    type_text = ['设定', '毛图', '插画']
    for i in range(data_len):
        name = data_list[i]['name']
        pic_type = int(data_list[i]['type'])
        picture_url = data_list[i]['picture_url']
        suggest = data_list[i]['suggest']
        if suggest == '':
            suggest = "未填写留言"
        upload_account = data_list[i]['upload_account']
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
        make_text = await batch_get(text, picture_url, event.self_id, nickname)
        items.append(make_text)
    logger.info(items)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=items, time_noend=True)


@check_upload_decide.handle()
@handle_errors
async def check_upload_decision(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    await matcher.send("将通过凌辉Bot内置账户进行处理")
    data_message = event.get_message()
    user_message = str(args)
    user_message = user_message.split("#")
    temp_args = user_message
    user_message = int(user_message[0])
    items = handle_json(Path(DATA_PATH) / "upload_data.json", 'r')
    logger.info(items)
    logger.info(temp_args)
    if user_message > len(items):
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "错误：输入的值超出列表项目\n请确认列表项目后重试。")
    if not items:
        await matcher.finish(MessageSegment.reply(event.message_id) + "遇到问题：似乎没有待审核的图片。")
    data_normal = items[int(str(user_message)) - 1]
    pic_url = data_normal['picture_url']
    time_wait = data_normal['time']
    upload_time = time.localtime(int(time_wait))
    name = data_normal['name']
    pic_type = int(data_normal['type'])
    type_list = ["设定", "毛图", "插画"]
    type_value = type_list[pic_type]
    suggest = data_normal['suggest']
    group_id = int(data_normal['group_id'])
    account = data_normal['upload_account']
    if suggest == "":
        suggest = "未填写"
    del data_normal['picture_url'], data_normal['group_id'], data_normal['upload_account'], data_normal['time']
    if "拒绝" in str(data_message):
        del items[int(str(user_message)) - 1]
        handle_json(Path(DATA_PATH) / "upload_data.json", 'w', items)

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
        del items[int(str(user_message)) - 1]
        handle_json(Path(DATA_PATH) / "upload_data.json", 'w', items)
        if event.group_id != group_id:
            await bot.call_api("send_group_msg", group_id=group_id, message=f"""凌辉Bot管理员已经同意了来自{account}的投图请求，请等待兽云祭管理员进行审核
上载图片：""" + MessageSegment.image(f"{pic_url}") + f"""数字id：{pic_id}
【上传时间戳：{time.strftime("%Y-%m-%d %H:%M:%S", upload_time)}】""", time_noend=True)
        await bot.call_api("send_group_msg", group_id=event.group_id,
                           message=f"{text}\n上载图片：" + MessageSegment.image(f"{pic_url}"), time_noend=True)
        os.remove(f"{pic_url}")


@upload_clear.handle()
async def clear_upload_data(matcher: Matcher):
    temp_path = DATA_PATH / "upload_data.json"
    dir_path = DATA_PATH / "Batch"
    if os.path.exists(temp_path):
        os.remove(temp_path)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write("[]")
    await matcher.finish("操作已完成。")
