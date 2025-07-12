from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import on_command
from nonebot.permission import SUPERUSER

echo = on_command("echo",permission=SUPERUSER)
@echo.handle()
async def echo_escape(message: Message = CommandArg()):
    await echo.send(message=f"{message}")