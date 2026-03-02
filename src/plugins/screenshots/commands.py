from nonebot import on_command
from nonebot.permission import SUPERUSER

# 定义命令
screenshot_cmd = on_command("截屏", aliases={"截图"}, priority=10,permission=SUPERUSER)