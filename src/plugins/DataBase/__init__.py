from nonebot import require
from .commands import (
    add_item,
    del_item,
    update_item,
    get_item,
    list_items
)
require("nonebot_plugin_localstore")  # 若不需要可删除

# 只导入即可让命令注册到 NoneBot

__all__ = [
    "add_item",
    "del_item",
    "update_item",
    "get_item",
    "list_items"
]