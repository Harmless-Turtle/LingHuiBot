from nonebot.adapters.onebot.v11 import (
    Bot,
    Message
)
from nonebot.internal.matcher import Matcher

from .commands import (
    add_battle
)



@add_battle.handle()
async def _add_battle(matcher:Matcher,bot:Bot,event,message: Message):
    pass