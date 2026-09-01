import asyncio
from datetime import datetime
from pathlib import Path

import httpx
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, Bot, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session, get_session
from sqlalchemy import select

from .models import FurryPictureData
from ..commands import upload_furry,modify_furry
from src.plugins.utils import handle_errors,handle_json
from ...utils import ensure_files_exist
from .tools import download_image

# 用户输入 1 -> 毛照，输入 2 -> 稿子
FURRY_TYPE_MAP = {"1": "毛照", "2": "稿子"}

# 缓存目录
UPLOAD_CACHE_DIR = Path(__file__).parent / "upload"
UPLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
ensure_files_exist([UPLOAD_CACHE_DIR / "manifest.json",UPLOAD_CACHE_DIR / "modify.json"], normal_data=[[],[]],description="图床临时存放目录")

@upload_furry.handle()
@handle_errors
async def upload_furry_function(
        matcher: Matcher,
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
        session:async_scoped_session
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
            # 检查图片是否已存在
            if any(UPLOAD_CACHE_DIR.glob(f"{file_md5}.*")):
                duplicate_sum += 1
                continue
            # 查表是否有重复值
            result = await session.execute(
                select(FurryPictureData.id)
                .where(FurryPictureData.file_name == file_md5)
                .limit(1)
            )

            if result.scalar_one_or_none() is not None:
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
    if len(image_segments) == duplicate_sum:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"上传失败，所有图片均为重复图片")
    if duplicate_sum != 0:
        await matcher.send(f"本次上传中{duplicate_sum}张图片MD5重复，请确认图片是否已经上传。\n如果需要修改，请使用修改指令而不是重新上传。")
    await matcher.finish(MessageSegment.reply(event.message_id)+f"已成功上传图片{format_str}")

@modify_furry.handle()
@handle_errors
async def modify_furry_function(
        matcher: Matcher,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    # 获取用户输入的消息内容
    user_input = args.extract_plain_text().split()
    # 检查是否有图片码参数
    if len(user_input) != 2:
        await matcher.finish(
            "请按照“修改图片 <图片码> <属性>”格式输入。\n"
            "可修改属性：\n"
            "0：名字\n"
            "1：图片类型（1是毛照，2是稿子）\n"
            "2：图片"
        )
    # 获取要修改图片的图片吗以及要修改的属性
    modify_id = user_input[0]
    modify_attr = user_input[1]
    # 判断属性输入是否合法
    if modify_attr not in {"0", "1", "2"}:
        await matcher.finish(
            "请重新使用此命令，并提供正确的属性编号。\n"
            "0：名字 1：图片类型 2：图片"
        )
    # 与SQL通信，确认图片码是否存在。
    picture_list = await session.get(FurryPictureData,modify_id)
    if picture_list is None:
        await matcher.finish(f"未找到图片码为{modify_id}的图片，请检查输入是否正确。")
    matcher.set_arg("modify_id", Message(modify_id))
    matcher.set_arg("modify_attr", Message(modify_attr))

@modify_furry.got("modify_content", prompt="请发送新的属性值。\n想要取消修改，请发送”结束“")
@handle_errors
async def modify_furry_attr(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
):
    modify_id = matcher.get_arg("modify_id").extract_plain_text()
    modify_attr = int(matcher.get_arg("modify_attr").extract_plain_text())
    modify_content = matcher.get_arg("modify_content").extract_plain_text().strip()
    if modify_content == "结束":
        await matcher.finish("已取消本次图片修改。")
    picture = await session.get(FurryPictureData, modify_id)
    if modify_attr != 2:
        modify_data = handle_json(UPLOAD_CACHE_DIR / "modify.json", 'r')
        modify_attr_text = ["名字", "图片类型"]
        if not modify_data:
            modify_data = []
        modify_info = {
            "id": modify_id,
            "attr": modify_attr_text[modify_attr],
            "new_value": modify_content,
            "timestamp": datetime.now().isoformat(),
            "user_id": event.user_id,
            "group_id": event.group_id
        }
        modify_data.append(modify_info)
        handle_json(UPLOAD_CACHE_DIR / "modify.json", "w", modify_data)
        await matcher.finish(MessageSegment.reply(event.message_id)+f"已成功修改图片码为 {modify_id} 的 {modify_attr_text[modify_attr]} 属性为 {modify_content}，请等待管理员审核。")
