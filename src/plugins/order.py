import json
import random
from pathlib import Path

import httpx
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message,
)
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import on_command

from .utils import ensure_files_exist


async def chek_rule_at(event: GroupMessageEvent):
    s = event.user_id
    if s == 1815984076 or s == 1097740481:
        return True
    else:
        return False


Order = on_command("点菜", aliases={"点餐"}, priority=20)
Upload_Order = on_command("上传饮品", aliases={"添加饮品"}, rule=chek_rule_at, priority=20)
Delete_Order = on_command("删除饮品", rule=chek_rule_at, priority=20)

opendata = Path.cwd()
Data_Path = opendata / 'data/Order_System'

# 启动自检：数据目录、图片目录、饮品列表。原来全靠用户先手动建好，
# 全新部署下“点菜”会直接 FileNotFoundError。
ensure_files_exist(
    file_path=[Data_Path, Data_Path / 'Picture', Data_Path / 'List.json'],
    description="点菜模块自检",
    normal_data=[None, None, {}]
)


@Order.handle()
async def order_function(event: MessageEvent):
    with open(f"{Data_Path}/List.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not data:
        await Order.finish(
            MessageSegment.reply(event.message_id) + "饮品列表还是空的呢，先让管理员用“上传饮品”加几个吧~")

    key, value = list(data.keys()), list(data.values())
    select = random.randint(0, len(key) - 1)
    text, picture = key[select], value[select]
    await Order.finish(
        MessageSegment.reply(event.message_id) + f"您好~您的饮品是{text}，请慢用~\n" + MessageSegment.image(picture))


@Upload_Order.handle()
async def upload_order_function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    data = args.split("#")
    if len(data) != 3:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + "输入格式不正确，请重新上传\n正确的格式应该是：上传饮品#饮品名字#饮品图片")
    name = data[1]
    # name 会直接拼进文件路径，禁止空名与路径分隔符，避免把文件写出 Picture 目录
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        await Upload_Order.finish(MessageSegment.reply(
            event.message_id) + "饮品名称不能为空，也不能包含路径分隔符哦~")
    msg_group = event.get_message()
    # 没附带图片时 msg_group["image"] 返回空 Message，后续 list(...)[-1] 会 IndexError
    if not msg_group["image"]:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + "没有检测到图片，请在命令后附带一张饮品图片~")
    url = msg_group["image"]
    if not url:
        await Upload_Order.finish(MessageSegment.reply(
            event.message_id) + "没有检测到图片，请在命令后附带一张饮品图片~")
    pic_url = list(url)[-1].data["url"]
    # 原实现用同步 httpx.get 下载，会阻塞整个事件循环（项目规范要求异步）
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(pic_url)
    if response.status_code != 200:
        await Upload_Order.finish(MessageSegment.reply(
            event.message_id) + f"图片下载失败：[HTTP {response.status_code}]，请稍后重试~")
    with open(f"{Data_Path}/Picture/{name}.jpg", 'wb') as f, open(f"{Data_Path}/List.json", 'r', encoding='utf-8') as F:
        f.write(response.content)
        data = json.load(F)
    data[f"{name}"] = f"{Data_Path}/Picture/{name}.jpg"
    with open(f"{Data_Path}/List.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    await matcher.finish(MessageSegment.reply(event.message_id) + "操作成功完成。")


@Delete_Order.handle()
async def delete_order_function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    name = args.extract_plain_text().strip()
    with open(f"{Data_Path}/List.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 原实现写反了：存在时提示“没有找到”并直接 finish，导致删除永远不执行；
    # 不存在时又会在 del 处抛 KeyError。
    if name not in data:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"遇到问题：在饮品列表里没有找到{name}")

    picture_path = Path(data.pop(name))
    if picture_path.exists():
        picture_path.unlink()
    with open(f"{Data_Path}/List.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    await matcher.finish(MessageSegment.reply(event.message_id) + "操作成功完成。")
