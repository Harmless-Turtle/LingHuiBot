import random as rd
from pathlib import Path

from nonebot import logger,get_driver
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    MessageSegment,
    Bot
)
from nonebot.internal.matcher import Matcher

from src.plugins.entertainment.commands import (
    add_battle,
    pick_battle,
    auto_switch_battle
)
from src.plugins.entertainment.check_files import bottle_path,auto_path
from src.plugins.utils import handle_json


@add_battle.handle()
async def _add_battle(matcher: Matcher, event: MessageEvent):
    data = handle_json(bottle_path, 'r')
    text = str(event.raw_message)
    text = text.split(" ")
    text.pop(0)
    if len(text) < 1:
        await matcher.finish(MessageSegment.reply(event.message_id) + "唔...切片失败了，请检查是否按照“bottle <这里输入你想说的话>”的格式使用呢")
    text_list = data.get(str(event.user_id),[])
    text = "\n".join(text)
    text_list.append(text)
    logger.info(text)
    data[str(event.user_id)] = text_list
    handle_json(bottle_path, 'w', data)
    await matcher.finish(MessageSegment.reply(event.message_id)+"你的漂流瓶已经投进了大海...\n让我们猜一下它会飘向何处吧~")


@pick_battle.handle()
async def _pick_battle(matcher: Matcher, bot: Bot, event: MessageEvent):
    data = handle_json(bottle_path, 'r')
    # 过滤出所有真正有内容的用户 ID (排除空列表)
    valid_users = [uid for uid, bottles in data.items() if bottles]
    # 如果没有数据了，就直接结束
    if not valid_users:
        aword_path = Path.cwd() / 'data' / 'main' / "aword.json"
        word_list = handle_json(aword_path, 'r')
        result = rd.choice(word_list)
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"大海里一眼望不到头，但就是没有看到漂流瓶呢awa\n但是~凌辉有一句一言哦w~\n“{result}”")
    # 检测到有数据，随机取一个值
    random_user = rd.choice(valid_users)
    result = rd.choice(data[random_user])
    # 删除这个数据
    data[random_user].remove(result)

    # 如果该用户瓶子被捡光了，删除该 Key
    if not data[random_user]:
        del data[random_user]
    handle_json(bottle_path, 'w', data)
    stranger_info = await bot.get_stranger_info(user_id=int(random_user))
    nickname = stranger_info.get('nickname', '来自远方的旅人')

    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"在遥远的大海中飘来了一个小小的瓶子，它的里面写着：{result}\n署名是：“{nickname}”")

@auto_switch_battle.handle()
async def _auto_switch_battle(bot:Bot,matcher: Matcher, event: MessageEvent):
    group_member = await bot.get_group_member_info(user_id=event.user_id, group_id=event.group_id)
    group_admin = group_member['role']
    superusers = get_driver().config.superusers
    if str(event.user_id) not in superusers and "member" == group_admin:
        await matcher.finish(MessageSegment.reply(event.message_id)+"唔...你不是凌辉su用户或者群管理员，没办法操控这个开关呢xwx")
    switch_data = handle_json(auto_path, 'r')
    mode = switch_data.get(str(event.group_id),{f"{event.group_id}":False})
    switch_data[str(event.group_id)] = not mode
    handle_json(auto_path, 'w', switch_data)
    text = "已开启随机漂流功能，漂流瓶会在随机的时间里被送到本群呢w" if not mode else "已关闭随机漂流功能"
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{text}")