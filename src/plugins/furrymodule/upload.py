# 标准库
import os
import time
from pathlib import Path

# 第三方库
import httpx
from nonebot import logger, on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

# 本地模块
from src.plugins import utils
from src.plugins.utils import get_config_item,ensure_files_exist

# ================= 配置与常量 =================

# 定义全局常量
API_BASE = "https://cloud.foxtail.cn/api"
OPENDATA = Path.cwd()
DATA_PATH = OPENDATA / "data" / "furry_system" / "upload"
FONT_PATH = OPENDATA / "data" / "MiSans-Demibold.ttf"
json_path = DATA_PATH / "upload_data.json"
batch_path = DATA_PATH / "batch"


ensure_files_exist(
    [DATA_PATH],
    "furry_upload"
)

# 定义全局变量
LOGIN_COOKIE = {}
TIMEOUT = None  # 建议设置具体的超时时间，例如 30

# 读取配置项
TOKEN = get_config_item("furry_token", default="未获取到数据", required=True, desc="Foxtail API Token")
ACCOUNT = get_config_item("furry_user", default="未获取到数据", required=True, desc="Foxtail 账号")
PASSWORD = get_config_item("furry_password", default="未获取到数据", required=True, desc="Foxtail 密码")

# 检查配置
if all([TOKEN != "未获取到数据",ACCOUNT != "未获取到数据",PASSWORD != "未获取到数据"]):
    logger.success("✅已成功加载Furry模块的相关配置！")
    logger.info(f"获取到的信息：\ntoken：{TOKEN}\naccount：{ACCOUNT}\npassword：{PASSWORD}\napi_base：{API_BASE}")
else:
    logger.warning("请注意，当前功能受限制！")
    logger.warning("您没有填写token/account/password，这将导致“投图”功能不可用！")

# ================= 命令注册 =================

upload_furry = on_command("一键上传", aliases={"投图", "管理员上传"}, priority=10, block=True)
batch_upload = on_command("批量投图", aliases={"批量上传"}, block=True)
batch_set = on_command("定义#", aliases={"定义"}, priority=10, block=True)
debugger_upload = on_command("调试", aliases={"上传调试", "上图调试"}, priority=1, permission=SUPERUSER)
modify_furry = on_command("修改图片", priority=99, block=True, permission=SUPERUSER)

# ================= 处理函数 =================


@upload_furry.handle()
@utils.handle_errors
async def upload_furry_image(
    matcher: Matcher,
    event: MessageEvent,
    bot: Bot,
    group: GroupMessageEvent,
    args: Message = CommandArg(),
):
    data = str(args).split("#")
    
    # 路径检查
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)

    error_msg_format = (
        "错误：请按照#名字#类型#留言#图片的格式重新上传\n"
        "（类型：数字0为设定，1为毛图，2为插画）"
    )

    if len(data) != 5:
        await matcher.finish(MessageSegment.reply(event.message_id) + error_msg_format)
    
    name = data[1]
    pic_type = data[2]
    suggest = data[3]
    pic = data[4]

    # 参数校验
    if name == "":
        await matcher.finish(MessageSegment.reply(event.message_id) + "错误：您似乎并没有填写名字，" + error_msg_format)
    elif pic_type == "":
        await matcher.finish(MessageSegment.reply(event.message_id) + "错误：您似乎并没有填写类型，" + error_msg_format)
    elif pic == "":
        await matcher.finish(MessageSegment.reply(event.message_id) + "错误：您似乎并没有发送图片，请按照#名字#类型#留言#图片的格式重新上传")
    
    if not pic_type.isdigit():
        await matcher.finish(MessageSegment.reply(event.message_id) + "遇到问题：类型并非纯数字（0为设定，1为毛图，2为插画）")

    # 图片下载逻辑
    msg_group = event.get_message()
    url = msg_group["image"]
    upload_account_number = event.user_id
    group_number = group.group_id
    timestamp = int(time.time())
    file_path = DATA_PATH / f"{timestamp}.jpg"

    async with httpx.AsyncClient(http2=True, timeout=TIMEOUT) as client:
        # 注意：这里假设 list(url)[-1] 是正确的图片对象逻辑，保持原样
        resp = await client.get(list(url)[-1].data["url"])
        with open(file_path, "wb") as f:
            f.write(resp.content)

    # 文件大小检查
    file_size = os.stat(file_path)
    if file_size.st_size >= 20000000:  # 20MB
        os.remove(file_path)
        await matcher.finish(MessageSegment.reply(event.message_id) + "上传失败：文件过大！（大于20MB）")

    # 构造数据
    data_dict = {
        "name": f"{name}",
        "type": f"{pic_type}",
        "power": 1,
        "suggest": f"{suggest}",
        "model": 1,
        "token": f"{TOKEN}",
        "token_user": f"{ACCOUNT}",
        "token_key": f"{PASSWORD}",
        "time": f"{timestamp}",
        "picture_url": str(file_path),
        "upload_account": f"{upload_account_number}",
        "group_id": f"{group_number}",
    }

    upload_list = []

    
    if os.path.exists(json_path):
        upload_list = utils.handle_json(json_path, "r")

    upload_list.append(data_dict)
    utils.handle_json(json_path, "w", upload_list)
    
    count = len(upload_list)
    # 管理员通知
    await bot.call_api(
        "send_private_msg",
        message=f"有人投图，请审核\n当前共有{count}张图片待审核",
        user_id="1097740481",
        time_noend=True,
    )
    await matcher.finish(
        MessageSegment.reply(event.message_id) + "您的投图请求已提交给凌辉Bot管理员并进入等待审核状态。"
    )


async def get_batch_pic_list(user_qq):
    """辅助函数：获取批量图片列表"""
    batch_data_path = batch_path / str(user_qq) / "upload.json"
    pic_url = utils.handle_json(batch_data_path, "r")
    pic_list = []
    logger.debug(f"debug message:{pic_url}")
    logger.debug(f"picture count:{len(pic_list)}")
    
    for i in range(0, len(pic_url)):
        image = pic_url[i]
        text = f"这是第{i + 1}张图片，通过命令“定义”来定义开始该图片的信息。"
        # 注意：这里调用了 utils.batch_get，需要确保该函数存在
        data = await utils.batch_get(text, image, user_qq, "凌辉Bot")
        pic_list.append(data)
    
    logger.debug(f"Return:{pic_list}")
    return pic_list


@batch_upload.got(
    "Upload",
    prompt="请一次性发送您要上传的图片。\n当您在发送上传图片时，请在聊天框键入一个空格以将所有图片包含进1个Message中。",
)
@utils.handle_errors
async def get_upload_mode(matcher: Matcher, event: MessageEvent, bot: Bot):
    args = str(event.get_message())
    msg_group = event.get_message()
    url = msg_group["image"]
    url_list = []
    temp_path = batch_path / str(event.user_id)
    cycle_count = 0
    
    if not os.path.exists(temp_path):
        os.makedirs(temp_path)

    if os.path.exists(json_path):
        data = utils.handle_json(json_path, "r")
        cycle_count = len(data)
        for i in data:
            url_list.append(i)
    
    j = 0
    for i in range(cycle_count, len(url) + cycle_count):
        pic_url = list(url)[j].data["url"]
        j += 1
        file_path = temp_path / f"Upload_{i + 1}.jpg"
        
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            data = await client.get(pic_url)
            with open(file_path, "wb") as f:
                f.write(data.content)

        url_list.append(str(file_path))
        file_size = os.stat(file_path)
        if file_size.st_size >= 20000000:
            await matcher.send(f"第{i + 1}张图片被拒绝上传：文件过大，拒绝处理。")
            os.remove(file_path)
            url_list.remove(str(file_path))
            
    if not url_list:
        count = 0
        if "取消" in args or "退出" in args:
            await matcher.finish(MessageSegment.reply(event.message_id) + "已退出批量投图。")
        else:
            if count == 0:
                await matcher.reject(
                    MessageSegment.reply(event.message_id) + "输入有误，请重新输入。\n取消上传请发送“取消”或“退出”"
                )
            else:
                await matcher.finish(MessageSegment.reply(event.message_id) + "已退出批量投图。")
    
    utils.handle_json(json_path, "w", url_list)

    forward_msg_list = await get_batch_pic_list(event.user_id)
    await bot.call_api(
        "send_group_forward_msg", group_id=event.group_id, message=forward_msg_list, time_noend=True
    )
    await matcher.finish(
        MessageSegment.reply(event.message_id) + "生成图片链接列表已完成，但图片对应信息尚未设置\n请通过命令“定义”来定义对应图片的信息。"
    )


@batch_set.got(
    "Set_Message", prompt="请定义图片信息（定义实例：定义#1#名字#类别#留言）\n结束定义可发送“取消”或“退出”"
)
@utils.handle_errors
async def receive_batch(matcher: Matcher, bot: Bot, event: MessageEvent):
    # 注意：matcher state 管理 set_count 会更合适，此处保持局部变量逻辑可能导致死循环 reject
    set_count = 0
    temp_path = batch_path / str(event.user_id) / "upload.json"
    
    if not os.path.exists(temp_path):
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "遇到问题：未找到文件\n请检查是否已经批量投图图片。"
        )
        
    items = utils.handle_json(temp_path, "r")
    message_text = str(event.get_message())
    
    if "取消" in message_text or "退出" in message_text:
        await matcher.finish(MessageSegment.reply(event.message_id) + "已退出批量投图。")
        
    if message_text.count("#") == 0:
        if set_count == 0:
            await matcher.reject(
                MessageSegment.reply(event.message_id) + "输入了一个错误的图片张数，请重新输入（仅接受数字）。\n取消上传请发送“取消”或“退出”"
            )
        else:
            await matcher.finish(MessageSegment.reply(event.message_id) + "多次非法请求，已自动退出批量投图。")
            
    message_text = message_text.split("#")
    if len(message_text) != 5:
        if set_count == 0:
            await matcher.reject(
                MessageSegment.reply(event.message_id) + "输入有误，请重新输入。\n取消上传请发送“取消”或“退出”"
            )
        else:
            await matcher.finish(MessageSegment.reply(event.message_id) + "多次非法请求，已自动退出批量投图。")
            
    pic_id, name, field_type, suggest = message_text[1], message_text[2], message_text[3], message_text[4]
    
    if not pic_id.isdigit():
        if set_count == 0:
            await matcher.reject(
                MessageSegment.reply(event.message_id) + "输入的数据长度有误，请重新输入。\n取消上传请发送“取消”或“退出”"
            )
        else:
            await matcher.finish(MessageSegment.reply(event.message_id) + "多次非法请求，已自动退出批量投图。")
            
    if int(pic_id) > len(items):
        await matcher.finish(MessageSegment.reply(event.message_id) + "遇到问题：似乎超出了列表长度\n已自动退出")
        
    pic_id = int(pic_id) - 1
    upload_account_number = event.user_id
    group_number = event.group_id
    
    data = {
        "name": f"{name}",
        "type": f"{field_type}",
        "power": 1,
        "suggest": f"{suggest}",
        "model": 1,
        "token": f"{TOKEN}",
        "token_user": f"{ACCOUNT}",
        "token_key": f"{PASSWORD}",
        "time": int(time.time()),
        "picture_url": f"{items[pic_id]}",
        "upload_account": f"{upload_account_number}",
        "group_id": f"{group_number}",
    }
    
    logger.info(data)
    del items[pic_id]
    
    if len(items) != 0:
        upload_data = utils.handle_json(json_path, "r")
        upload_data.append(data)
        
        utils.handle_json(temp_path, "w", items)
        # 更新 forward message list
        new_items = await get_batch_pic_list(event.user_id)
        utils.handle_json(json_path, "w", upload_data)

        logger.info(new_items)
        await bot.call_api(
            "send_group_forward_msg", group_id=event.group_id, message=new_items, time_noend=True
        )
        await batch_set.reject(MessageSegment.reply(event.message_id) + "写入文件完成，请根据列表继续修改图片信息")
    else:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "唔...您似乎已经成功为全部的图片提供了信息\n您全部的图片均已提交给凌辉Bot管理员进行审核，请您耐心等待~"
        )


@modify_furry.handle()
@utils.handle_errors
async def modify_furry_image(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    files = None
    message = str(args)
    after_message = message.split("#")
    modify_id = int(after_message[1])
    pic_value = after_message[2]
    field_type = after_message[3]
    data = {
        "picture": f"{modify_id}",
        "type": "1",
        "model": "1",
        "token": f"{TOKEN}",
        "token_user": f"{ACCOUNT}",
        "token_key": f"{PASSWORD}",
    }
    try:
        if field_type == "名字":
            pic_value = str(pic_value)
            data.update({"name": f"{pic_value}", "type": "0"})
        elif field_type == "留言":
            pic_value = str(pic_value)
            data.update({"suggest": f"{pic_value}", "type": "3"})
        elif field_type == "类型":
            pic_value = int(pic_value)
            data.update({"form": f"{pic_value}", "type": "2"})
        else:
            group = event.get_message()
            url = group["image"]
            pic_url = list(url)[-1].data["url"]
            logger.info(pic_url)
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                image_resp = await client.get(pic_url)
                image_content = image_resp.content
            files = {"file": ("Modify.png", image_content, "image/png")}
            data.update({"type": "1"})
            
    except Exception as e:
        # 建议打印 e 以便调试
        logger.error(f"Modification error: {e}")
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "在获取数据时遇到问题，请按照“修改图片#id#名字/留言/类型>#修改类型/图片”的格式重新调用命令。"
        )

    # 逻辑优化：统一发送请求
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 如果 files 存在（即修改图片的情况）
        if files:
            resp = await client.post(f"{API_BASE}/function/modify", data=data, files=files)
        else:
            resp = await client.post(f"{API_BASE}/function/modify", data=data)
            
        if resp.status_code != 200:
            await matcher.finish(
                MessageSegment.reply(event.message_id) + f"请求图片信息失败，服务器回报状态码：{resp.status_code}"
            )
        
        resp_json = resp.json()

    code, msg = resp_json["code"], resp_json["msg"]
    await matcher.finish(MessageSegment.reply(event.message_id) + f"平台返回：{msg}[Code:{code}]")