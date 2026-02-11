from nonebot import get_driver
from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
from nonebot.adapters.onebot.v11 import (
    Event,
)
from pathlib import Path
from src.plugins import utils


path = Path.cwd() / 'data'
black_list_path = path / "blacklist" / "black_list.json"

utils.ensure_files_exist([black_list_path],"黑名单插件")

@event_preprocessor
def black_processor(event:Event):
    user_id = event.user_id
    superusers = get_driver().config.superusers
    if event.post_type=='notice':
        return
    if(uid := str(vars(event).get('user_id',None))) in superusers:
        return
    black_list = utils.handle_json(black_list_path, 'r')
    if user_id in black_list:
        raise IgnoredException("黑名单用户，忽略请求。")