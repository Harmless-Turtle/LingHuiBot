from nonebot import get_plugin_config, on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .config import Config


def is_admin(event: GroupMessageEvent) -> bool:
    """判断当前消息发送者是否在配置文件设置的管理员列表里"""
    config = get_plugin_config(Config)
    return event.user_id in config.ORDER_ADMIN


order = on_command("点菜", aliases={"点餐"}, priority=20)
upload_order = on_command("上传饮品", aliases={"添加饮品"}, permission=is_admin, priority=20)
delete_order = on_command("删除饮品", permission=is_admin, priority=20)
list_order = on_command("饮品列表", aliases={"查看饮品"}, priority=20)
