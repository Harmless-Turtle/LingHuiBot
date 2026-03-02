from nonebot import on_command
from nonebot.rule import to_me

# 定义命令
screenshot_cmd = on_command("截屏", aliases={"截图"}, priority=10)