import httpx
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment

from ..commands import (
    pet_head
)
from src.plugins.utils import handle_errors



@pet_head.handle()
@handle_errors
async def pet_head_func(
                        event:GroupMessageEvent,):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://oiapi.net/api/Face_Petpet?QQ={event.user_id}")
    await pet_head.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(response.content))