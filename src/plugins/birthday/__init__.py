import nonebot

_ = nonebot.require("nonebot_plugin_orm")
_ = nonebot.require("nonebot_plugin_apscheduler")

from . import handlers, tasks

__all__ = ["handlers", "tasks"]
