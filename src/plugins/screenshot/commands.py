from nonebot import on_command
from nonebot.permission import SUPERUSER

screenshot_cmd = on_command("截屏", priority=5, block=True,permission=SUPERUSER)