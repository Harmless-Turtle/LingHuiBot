import os

from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot,MessageSegment
from nonebot.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session

from ..check_file import furry_pic_data_path
from ..commands import check_upload, check_upload_decide, check_modify_decide
from src.plugins.utils import handle_errors,handle_json
from .upload import UPLOAD_CACHE_DIR
from ...utils import batch_get
from .models import add_furry_picture,FurryPictureData,update_furry_picture


@check_upload.handle()
@handle_errors
async def check_upload_function(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        bot: Bot,
):
    """
    处理待审核列表命令，获取待审核的图片列表并发送给用户。
    """
    # 获取待审核的图片列表
    upload_list = handle_json(UPLOAD_CACHE_DIR / "manifest.json", 'r')
    modify_list = handle_json(UPLOAD_CACHE_DIR / "modify.json", 'r')
    if not upload_list and not modify_list:
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前没有待审核的图片。")
    final_list = []
    for index, item in enumerate(modify_list, start=1):
        text = f"""第{index}张图片 -> 图片修改请求
修改图片码：{item['id']}
修改的属性： {item['attr']}
新属性：{item['new_value']}
时间戳：{item['timestamp']}
上传者: {item['user_id']}
上传群聊：{item['group_id']}
管理员可通过命令“同意修改#{index}”或“拒绝修改#{index}”进行审核。
"""
        if item["attr"] == "图片":
            picture = item["file_path"]

            # 修改名字/图片类型时，从 SQL 获取原图片
        else:
            db_picture = await session.get(
                FurryPictureData,
                int(item["id"])
            )

            if db_picture is None:
                picture = None
            else:
                picture = db_picture.file_path
        batch_text = await batch_get(text, picture, item['user_id'], "待审核图片")
        final_list.append(batch_text)
    for index, item in enumerate(upload_list, start=1):
        message = f"""第{index}张图片 -> 新图片上传请求
名称: {item['furryname']}
文件名: {item['filename']}
类型: {item['type']}
时间戳：{item['timestamp']}
上传者: {item['user_id']}
上传群聊：{item['group_id']}
管理员可通过命令“同意上传#{index}”或“拒绝上传#{index}”进行审核。
"""
        batch_text = await batch_get(message,item['file_path'],item['user_id'],"待审核图片")
        final_list.append(batch_text)

    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)
    await matcher.finish()

@check_upload_decide.handle()
@handle_errors
async def check_upload_decide_function(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        bot: Bot
):
    status = True
    if "拒绝" in str(event.original_message):
        status = False
    # 读取json文件
    review_list = handle_json(UPLOAD_CACHE_DIR / "manifest.json", 'r')
    args = str(event.get_message()).split("#")
    review_id = int(args[1]) - 1
    # 判断列表是否已清空
    if not review_list:
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前没有待审核的图片。")
    # 根据status的值进行相应的处理
    if not status:
        del_review = review_list.pop(review_id)
        picture_path = del_review['file_path']
        user_id = del_review['user_id']
        group_id = del_review['group_id']
        handle_json(UPLOAD_CACHE_DIR / "manifest.json", 'w', review_list)
        reason = "管理员拒绝上传。"
        if len(args) > 2:
            reason = args[2]
        await bot.call_api(
            "send_group_msg",
            group_id=group_id,
            message=MessageSegment.at(user_id)+
f" 您的图片“{del_review['furryname']}”已被管理员拒绝上传。拒绝理由：{reason}"+
            MessageSegment.image(f"file:///{picture_path}"))
        os.remove(picture_path)
        if not group_id == event.group_id:
            await matcher.finish(MessageSegment.reply(event.message_id) + f"已拒绝上传第{review_id + 1}张图片，文件已删除。已告知上传者。")
        await matcher.finish()
    # 生成临时目录与正式目录
    original_file_path = review_list[review_id]['file_path']
    new_save_data = furry_pic_data_path / os.path.basename(original_file_path)
    # 写入SQL
    await add_furry_picture(
        session,
        file_name=review_list[review_id]['filename'],
        file_path=new_save_data,
        furry_name=review_list[review_id]['furryname'],
        type=review_list[review_id]['type'],
        uploader_id=review_list[review_id]['user_id'],
        group_id=review_list[review_id]['group_id']
    )
    # 移动文件到正式目录
    os.rename(original_file_path, new_save_data)
    # 更新manifest.json
    review_list.pop(review_id)
    handle_json(UPLOAD_CACHE_DIR / "manifest.json", 'w', review_list)
    await matcher.finish(MessageSegment.reply(event.message_id) + f"已同意上传第{review_id + 1}张图片，文件已移动到正式目录。")

@check_modify_decide.handle()
@handle_errors
async def check_modify_decide_function(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        bot: Bot
):
    status = True
    if "拒绝" in str(event.original_message):
        status = False
    # 读取json文件
    review_list = handle_json(UPLOAD_CACHE_DIR / "modify.json", 'r')
    args = str(event.get_message()).split("#")
    review_id = int(args[1]) - 1
    # 判断列表是否已清空
    if not review_list:
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前没有待审核的图片。")
    # 根据status的值进行相应的处理
    del_review = review_list[review_id]
    picture = ""
    user_id = del_review['user_id']
    group_id = del_review['group_id']
    if del_review['attr'] == "图片":
        picture_path = del_review['file_path']
        picture = MessageSegment.image(f"file:///{picture_path}")
    # 检查status状态
    if not status:
        review_list.pop(review_id)
        handle_json(UPLOAD_CACHE_DIR / "modify.json", 'w', review_list)
        reason = "管理员拒绝修改。"
        if len(args) > 2:
            reason = args[2]
        await bot.call_api(
            "send_group_msg",
            group_id=group_id,
            message=MessageSegment.at(user_id) +
                    f" 您的图片修改请求已被管理员拒绝修改。\n修改图片码：{del_review['id']}\n拒绝理由：{reason}" +
                    picture)
        if event.group_id != group_id:
            await matcher.finish(MessageSegment.reply(event.message_id) + f"已拒绝修改第{review_id + 1}张图片，已告知上传者。")
        await matcher.finish()
    new_save_data,nb_picture = False, ""
    if del_review['attr'] == "图片":
        # 移动文件到正式目录
        original_file_path = del_review['file_path']
        new_save_data = furry_pic_data_path / os.path.basename(del_review['new_value'])
        os.rename(original_file_path, new_save_data)
        del_review['new_value'] = str(new_save_data)
        nb_picture = MessageSegment.image(f"file:///{new_save_data}")
    if del_review['attr'] == "图片类型":
        del_review['new_value'] = "毛照" if del_review['new_value'] == "1" else "稿子"
    success = await update_furry_picture(
        session,
        int(del_review["id"]),
        del_review["attr"],
        del_review["new_value"],
        new_save_data
    )
    if not success:
        if new_save_data and new_save_data.exists():
            os.rename(new_save_data, original_file_path)

        await matcher.finish("修改失败，找不到对应的图片记录。")
    review_list.pop(review_id)
    handle_json(UPLOAD_CACHE_DIR / "modify.json", 'w', review_list)
    await update_furry_picture(session, int(del_review["id"]), del_review["attr"], del_review["new_value"], new_save_data)
    await bot.call_api(
        "send_group_msg",
        group_id=group_id,
        message=MessageSegment.at(user_id) +
                f" 您的图片修改请求已被管理员同意修改。\n修改图片码：{del_review['id']}" +
                nb_picture)
    if event.group_id != group_id:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"已同意修改第{review_id + 1}张图片，已更新数据库记录。")