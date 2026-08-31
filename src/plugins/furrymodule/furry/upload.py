import asyncio
import json
from datetime import datetime
import hashlib
from pathlib import Path

import httpx
from PIL import Image
from nonebot import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, Bot, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.rule import Rule

from ..commands import upload_furry, modify_furry
from ..check_file import furry_pic_data_path
from src.plugins.utils import handle_errors,handle_json
from ...utils import ensure_files_exist
from .tools import download_image

# 用户输入 1 -> 毛照，输入 2 -> 稿子
FURRY_TYPE_MAP = {"1": "毛照", "2": "稿子"}

# 缓存目录
UPLOAD_CACHE_DIR = Path(__file__).parent / "upload"
UPLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
ensure_files_exist([UPLOAD_CACHE_DIR / "manifest.json"], normal_data=[[]],description="本地图床临时存放目录")

@upload_furry.handle()
@handle_errors
async def upload_furry_function(
        matcher: Matcher,
        event:GroupMessageEvent,
        args: Message = CommandArg()):
    """
    处理上传命令，接收用户输入的图片和类型，并将其保存到缓存目录中。
    """
    # 获取用户输入的消息内容
    user_input = args.extract_plain_text().split()

    # 检查是否有图片附件
    image_segments = [seg for seg in args if seg.type == "image"]

    # 检查用户是否提供了类型参数
    if len(user_input) < 2:
        await matcher.finish("请按照“投图 兽图名称 图片类型 ”格式输入。\n图片类型：（1: 毛照, 2: 稿子）")
    if user_input[1] not in FURRY_TYPE_MAP.keys():
        await matcher.finish("请提供图片类型（1: 毛照, 2: 稿子）。")
    # 获取图片类型
    furry_type = FURRY_TYPE_MAP[user_input[1]]
    matcher.set_arg("furryname", Message(user_input[0]))
    matcher.set_arg("image_type", Message(furry_type))
    if image_segments:
        matcher.set_arg("image", Message(image_segments))

@upload_furry.got("image", prompt="请发送图片，注意不要上传群文件。\n想要取消上传，请发送”结束“")
@handle_errors
async def upload_furry_image(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot:Bot
):
    # 取得Step1中获得的Arg
    upload_furry_data = handle_json(UPLOAD_CACHE_DIR / "manifest.json", 'r')
    furryname = matcher.get_arg("furryname").extract_plain_text()
    furry_type = matcher.get_arg("image_type").extract_plain_text()
    image_message = matcher.get_arg("image")
    text = image_message.extract_plain_text().strip()
    if text == "结束":
        await matcher.finish("已取消本次图片上传。")
    image_segments = [
        seg
        for seg in matcher.get_arg("image")
        if seg.type == "image"
    ]
    if not image_segments:
        await matcher.reject_arg("image", "请发送图片，注意不要上传群文件。\n想要取消上传，请发送”结束“")
    name_list,tasks = [],[]
    duplicate_sum = 0
    # 下载图片并保存到缓存目录
    async with httpx.AsyncClient() as client:
        for image_segment in image_segments:
            image_url = image_segment.data.get("url")
            file_md5 = Path(image_segment.data["file"]).stem.lower()
            if not image_url:
                await matcher.finish("无法获取图片 URL，请检查图片是否有效。")
            if any(UPLOAD_CACHE_DIR.glob(f"{file_md5}.*")):
                duplicate_sum += 1
                continue
            task = download_image(client, image_url,file_md5, UPLOAD_CACHE_DIR)

            tasks.append(task)
        results = await asyncio.gather(*tasks)

    for file_path,file_name in results:
        name_list.append(file_name)
        upload_info = {
            "furryname": furryname,
            "filename": file_name,
            "type": furry_type,
            "timestamp": datetime.now().isoformat(),
            "user_id": event.user_id,
            "group_id": event.group_id,
            "file_path": str(file_path)
        }
        upload_furry_data.append(upload_info)
    handle_json(UPLOAD_CACHE_DIR / "manifest.json", "w", upload_furry_data)
    format_str = '，文件名：' +  '、'.join(name_list)
    if len(name_list) >= 2:
        format_str = ""
    if duplicate_sum != 0:
        await matcher.send(f"本次上传中{duplicate_sum}张图片MD5重复，请确认图片是否已经上传。\n如果需要修改，请使用修改指令而不是重新上传。")
    if len(image_segments) == duplicate_sum:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"上传失败，所有图片均为重复图片")
    await matcher.finish(MessageSegment.reply(event.message_id)+f"已成功上传图片{format_str}")