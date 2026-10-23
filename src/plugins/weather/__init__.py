from nonebot import get_plugin_config

from . import config
from .config import Config

_config = get_plugin_config(Config)
if _config.is_configured:
    from . import scheduled_task, typhoon, weather