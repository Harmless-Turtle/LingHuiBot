from nonebot import get_plugin_config

from . import check_files, config
from .config import Config

_config = get_plugin_config(Config)

if _config.is_ai_configured:
    from . import furry_ai

if _config.is_con_configured:
    from . import furry_con

if _config.is_suit_configured:
    from . import furry_suit


