import nonebot

_ = nonebot.require("nonebot_plugin_orm")

from . import models

__all__ = ["models"]
