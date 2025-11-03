# 标准库
import asyncio, os, shutil, time, httpx, math

from src.plugins import utils
# 第三方库
from types import SimpleNamespace
from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message,
    Bot,
)
from nonebot.matcher import Matcher
from nonebot.plugin import on_command
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from pathlib import Path
from PIL import Image, ImageFont

from src.plugins.utils import get_config_item

# FurryFusion 兽聚汇总服务
FurryFusion_List = on_command(
    "今年兽聚", aliases={"兽聚列表", "兽聚汇总"}, priority=10, block=True)
FurryFusion_Check = on_command("兽聚查询", block=True)
FurryFusion_countdown = on_command("兽聚倒计时", block=True)
FurryFusion_Quick_Information = on_command("兽聚快讯#", block=True)
FurryFusion_Information = on_command("兽聚信息", aliases={"兽聚详情"}, block=True)

