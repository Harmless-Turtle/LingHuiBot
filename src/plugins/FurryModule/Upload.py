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


# 定义全局变量
login_cookie = {}
timeout = None
count = 0
set_count = 0
api_base = "https://cloud.foxtail.cn/api"

opendata = Path.cwd()
Data_Path = opendata / 'data' / 'Furry_System' / 'Upload'
Font_Path = opendata / 'data' / 'MiSans-Demibold.ttf'
token = get_config_item('furry_token', default="未获取到数据", required=True, desc="Foxtail API Token")

UploadFurry = on_command(
    "一键上传", aliases={"投图", "管理员上传"}, priority=10, block=True)  # 上传图片
Batch_Upload = on_command("批量投图", aliases={"批量上传"}, block=True)  # 批量投图图片
Batch_Set = on_command("定义#", aliases={"定义"}, priority=10, block=True)
Debugger_Upload = on_command("调试", aliases={"上传调试", "上图调试"}, priority=1, permission=SUPERUSER)

@UploadFurry.handle()
@utils.handle_errors
async def upload_furry_image(matcher: Matcher, event: MessageEvent, bot: Bot, group: GroupMessageEvent,
                             args: Message = CommandArg()):
    data = str(args).split("#")
    if not os.path.exists(Data_Path):
        os.makedirs(Data_Path)
    if len(data) != 5:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + "错误：请按照#名字#类型#留言#图片的格式重新上传\n（类型：数字0为设定，1为毛图，2为插画")
    else:
        name = data[1]
        type = data[2]
        suggest = data[3]
        pic = data[4]
        # 对传入参数进行判定
        if name == "":
            await matcher.finish(MessageSegment.reply(
                event.message_id) + "错误：您似乎并没有填写名字，请按照#名字#类型#留言#图片的格式重新上传\n（类型：数字0为设定，1为毛图，2为插画")
        elif type == "":
            await matcher.finish(MessageSegment.reply(
                event.message_id) + "错误：您似乎并没有填写类型，请按照#名字#类型#留言#图片的格式重新上传\n（类型：数字0为设定，1为毛图，2为插画")
        elif pic == "":
            await matcher.finish(MessageSegment.reply(
                event.message_id) + "错误：您似乎并没有发送图片，请按照#名字#类型#留言#图片的格式重新上传")
        if not type.isdigit():
            await matcher.finish(
                MessageSegment.reply(event.message_id) + "遇到问题：类型并非纯数字（0为设定，1为毛图，2为插画")
        msggroup = event.get_message()
        url = msggroup["image"]
        upload_account_number = event.user_id
        group_number = group.group_id
        up_load_list = []
        Time = int(time.time())
        with open(f"{Data_Path}/{Time}.jpg", 'wb') as f:
            async with httpx.AsyncClient(http2=True, timeout=timeout) as client:
                Data = await client.get(list(url)[-1].data["url"])
                f.write(Data.content)
        file_size = os.stat(f"{Data_Path}/{Time}.jpg")
        if file_size.st_size >= 20000000:
            os.remove(f"{Data_Path}/{Time}.jpg")
            await matcher.finish(MessageSegment.reply(event.message_id) + "上传失败：文件过大！（大于20MB）")
        data = {
            "name": f"{name}",
            "type": f"{type}",
            "power": 1,
            "suggest": f"{suggest}",
            "model": 1,
            "token": f"{token}",
            "token_user": f"{account}",
            "token_key": f"{password}",
            "time": f"{Time}",
            "Picturl_URL": f"{Data_Path}/{Time}.jpg",
            "Upload_account": f"{upload_account_number}",
            'Group_id': f"{group_number}"
        }
        if os.path.exists(f'{Data_Path}/Upload_Data.json'):
            up_load_list = utils.handle_json(Path(Data_Path) / "Upload_Data.json", 'r')

        up_load_list.append(data)
        utils.handle_json(Path(Data_Path) / "Upload_Data.json", 'w', up_load_list)
        count = len(up_load_list)
        await bot.call_api("send_private_msg", message=f"有人投图，请审核\n当前共有{count}张图片待审核",
                           user_id='1097740481', time_noend=True)
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"您的投图请求已提交给凌辉Bot管理员并进入等待审核状态。")

# 定义获取批量投图图片列表函数
async def get_batch_pic_list(user_qq, bot):
    pic_url = utils.handle_json(Path(opendata) / "data/Furry_System/Upload/Batch" / user_qq / "Upload.json", 'r')
    list = []
    logger.debug(f'debug message:{type(pic_url)}')
    for i in range(0, len(pic_url)):
        image = pic_url[i]
        text = f"这是第{i + 1}张图片，通过命令“定义”来定义开始该图片的信息。"
        data = await utils.batch_get(text, image, user_qq, "凌辉Bot")
        list.append(data)
    return list


@Batch_Upload.got("Upload",
                  prompt="请一次性发送您要上传的图片。\n当您在发送上传图片时，请在聊天框键入一个空格以将所有图片包含进1个Message中。")
@utils.handle_errors
async def get_upload_mode(matcher: Matcher, event: MessageEvent, bot: Bot):
    args = str(event.get_message())
    msg_group = event.get_message()
    url = msg_group["image"]
    url_list = []
    temp_path = opendata / "data" / "Furry_System" / "Upload" / "Batch" / str(event.user_id)
    cycle_count = 0
    if not os.path.exists(temp_path):
        os.makedirs(temp_path)
    if os.path.exists(f"{temp_path}/Upload.json"):
        data = utils.handle_json(Path(temp_path) / "Upload.json", 'r')
        cycle_count = len(data)
        for i in data:
            url_list.append(i)
    j = 0
    for i in range(cycle_count, len(url) + cycle_count):
        pic_url = list(url)[j].data["url"]
        j += 1
        with open(f"{temp_path}/Upload_{i + 1}.jpg", 'wb') as f:
            async with httpx.AsyncClient(timeout=timeout) as client:
                data = await client.get(pic_url)
                f.write(data.content)

        url_list.append(f"{temp_path}/Upload_{i + 1}.jpg")
        file_size = os.stat(f"{temp_path}/Upload_{i + 1}.jpg")
        if file_size.st_size >= 20000000:
            await matcher.send(f"第{i + 1}张图片被拒绝上传：文件过大，拒绝处理。")
            os.remove(f"{temp_path}/Upload_{i + 1}.jpg")
            url_list.remove(f"{temp_path}/Upload_{i + 1}.jpg")
    if url_list == []:
        global Count
        if "取消" in args or "退出" in args:
            await matcher.finish(MessageSegment.reply(event.message_id) + "已退出批量投图。")
        else:
            if Count == 0:
                Count += 1
                await matcher.reject(
                    MessageSegment.reply(event.message_id) + "输入有误，请重新输入。\n取消上传请发送“取消”或“退出”")
            else:
                Count = 0
                await matcher.finish(MessageSegment.reply(event.message_id) + "已退出批量投图。")
    utils.handle_json(Path(temp_path) / "Upload.json", 'w', url_list)

    list = await get_batch_pic_list(event.user_id, Bot)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=list, time_noend=True)
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"生成图片链接列表已完成，但图片对应信息尚未设置\n请通过命令“定义”来定义对应图片的信息。")


@Batch_Set.got("Set_Message", prompt="请定义图片信息（定义实例：定义#1#名字#类别#留言）\n结束定义可发送“取消”或“退出”")
@utils.handle_errors
async def Receive_Batch(matcher: Matcher, bot: Bot, event: MessageEvent):
    global Set_Count
    Temp_Path = f"{opendata}/data/Furry_System/Upload/Batch/{event.user_id}/Upload.json"
    if not os.path.exists(Temp_Path):
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "遇到问题：未找到文件\n请检查是否已经批量投图图片。")
    List = utils.handle_json(Path(Temp_Path), 'r')
    Message = str(event.get_message())
    if "取消" in Message or "退出" in Message:
        await matcher.finish(MessageSegment.reply(event.message_id) + "已退出批量投图。")
    if Message.count("#") == 0:
        if Set_Count == 0:
            Set_Count += 1
            await matcher.reject(MessageSegment.reply(
                event.message_id) + "输入了一个错误的图片张数，请重新输入（仅接受数字）。\n取消上传请发送“取消”或“退出”")
        else:
            Set_Count = 0
            await matcher.finish(MessageSegment.reply(event.message_id) + "多次非法请求，已自动退出批量投图。")
    Message = Message.split("#")
    if len(Message) != 5:
        if Set_Count == 0:
            Set_Count += 1
            await matcher.reject(
                MessageSegment.reply(event.message_id) + "输入有误，请重新输入。\n取消上传请发送“取消”或“退出”")
        else:
            Set_Count = 0
            await matcher.finish(MessageSegment.reply(event.message_id) + "多次非法请求，已自动退出批量投图。")
    Pic_id, Name, Class, suggest = Message[1], Message[2], Message[3], Message[4]
    if not Pic_id.isdigit():
        if Set_Count == 0:
            Set_Count += 1
            await matcher.reject(
                MessageSegment.reply(event.message_id) + "输入的数据长度有误，请重新输入。\n取消上传请发送“取消”或“退出”")
        else:
            Set_Count = 0
            await matcher.finish(MessageSegment.reply(event.message_id) + "多次非法请求，已自动退出批量投图。")
    if int(Pic_id) > len(List):
        await matcher.finish(MessageSegment.reply(event.message_id) + "遇到问题：似乎超出了列表长度\n已自动退出")
    Pic_id = int(Pic_id) - 1
    Upload_account_Number = event.user_id
    Group_Number = event.group_id
    data = {
        "name": f"{Name}",
        "type": f"{Class}",
        "power": 1,
        "suggest": f"{suggest}",
        "model": 1,
        "token": f"{token}",
        "token_user": f"{account}",
        "token_key": f"{password}",
        "time": 0,
        "Picturl_URL": f"{List[Pic_id]}",
        "Upload_account": f"{Upload_account_Number}",
        'Group_id': f"{Group_Number}"
    }
    logger.info(data)
    del List[Pic_id]
    if len(List) + 1 != 0:
        Upload_Data = utils.handle_json(Path(Data_Path) / "Upload_Data.json", 'r')
        Upload_Data.append(data)
        utils.handle_json(Path(Temp_Path), 'w', List)
        List = await get_batch_pic_list(event.user_id, Bot)
        utils.handle_json(Path(Data_Path) / "Upload_Data.json", 'w', Upload_Data)

        logger.info(List)
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)
        await Batch_Set.reject(MessageSegment.reply(event.message_id) + "写入文件完成，请根据列表继续修改图片信息")
    else:
        await matcher.finish("定义图片列表已为空，这意味着你已经定义完了全部的图片\n事件处理结束。")
