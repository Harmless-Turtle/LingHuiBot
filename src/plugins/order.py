import httpx
import json
import os
import random
from pathlib import Path

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message,
)
from nonebot.params import CommandArg
from nonebot.plugin import on_command


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


@Order.handle()
async def order_function(event: MessageEvent):
    with open(f"{Data_Path}/List.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    key, value = list(data.keys()), list(data.values())
    select = random.randint(0, len(key) - 1)
    text, picture = key[select], value[select]
    await Order.finish(
        MessageSegment.reply(event.message_id) + f"您好~您的饮品是{text}，请慢用~\n" + MessageSegment.image(picture))


@Upload_Order.handle()
async def upload_order_function(event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    data = args.split("#")
    if len(data) != 3:
        await Upload_Order.finish(MessageSegment.reply(
            event.message_id) + "输入格式不正确，请重新上传\n正确的格式应该是：上传饮品#饮品名字#饮品图片")
    name = data[1]
    msg_group = event.get_message()
    url = msg_group["image"]
    pic_url = list(url)[-1].data["url"]
    with open(f"{Data_Path}/Picture/{name}.jpg", 'wb') as f, open(f"{Data_Path}/List.json", 'r', encoding='utf-8') as F:
        f.write(httpx.get(pic_url).content)
        data = json.load(F)
    data[f"{name}"] = f"{Data_Path}/Picture/{name}.jpg"
    with open(f"{Data_Path}/List.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    await Upload_Order.finish(MessageSegment.reply(event.message_id) + "操作成功完成。")


@Delete_Order.handle()
async def delete_order_function(event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    with open(f"{Data_Path}/List.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    if data.get(args, None):
        await Delete_Order.finish(MessageSegment.reply(event.message_id) + f"遇到问题：在饮品列表里没有找到{args}")
    del data[f'{args}']
    os.remove(f"{Data_Path}/Picture/{args}.jpg")
    with open(f"{Data_Path}/List.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    await Delete_Order.finish(MessageSegment.reply(event.message_id) + "操作成功完成。")
