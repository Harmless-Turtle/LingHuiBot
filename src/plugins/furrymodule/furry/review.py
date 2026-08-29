


from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot
from pathlib import Path
from nonebot.matcher import Matcher

from ..commands import check_upload
from src.plugins.utils import handle_errors,handle_json
from .upload import UPLOAD_CACHE_DIR
from ...utils import batch_get


@check_upload.handle()
@handle_errors
async def check_upload_function(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot
):
    """
    处理待审核列表命令，获取待审核的图片列表并发送给用户。
    """
    # 获取待审核的图片列表
    upload_list = handle_json(UPLOAD_CACHE_DIR / "manifest.json", 'r')
    if not upload_list:
        await matcher.finish("当前没有待审核的图片。")
    final_list = []
    for index, item in enumerate(upload_list, start=1):
        message = f"""{index}. 
名称: {item['furryname']}
文件名: {item['filename']}
类型: {item['type']}
时间戳：{item['timestamp']}
上传者: {item['user_id']}
上传群聊：{item['group_id']}
"""
        batch_text = await batch_get(message,item['file_path'],item['user_id'],"待审核图片")
        final_list.append(batch_text)

    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)
    await matcher.finish()