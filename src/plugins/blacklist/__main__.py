from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment,Message,Bot
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command

from pathlib import Path

from src.plugins import utils
from .tools import check_number

path = Path.cwd() / 'data'
blacklist_path = path / "blacklist" / "black_list.json"

add_group_blacklist = on_command("添加群聊黑名单",aliases={"群加黑"},priority=10,permission=SUPERUSER)
@add_group_blacklist.handle()
async def add_group(matcher: Matcher,event:GroupMessageEvent,args:Message = CommandArg()):
    raw_args = args.extract_plain_text().strip()
    gid,text = check_number(str(event.group_id),'group')
    if raw_args:
        gid, text = check_number(raw_args,'group')
        if not gid:
            await matcher.finish(MessageSegment.reply(event.message_id)+"唔...请输入一个正确的数字才可以呢。")
    data = utils.handle_json(blacklist_path,'r')
    if gid in data["group"]:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"唔...{text}已经在黑名单列表中了。")
    data['group'].append(gid)
    utils.handle_json(blacklist_path,'w',data)
    await matcher.finish(MessageSegment.reply(event.message_id) + f"已成功将{text}添加进黑名单。")


del_group_blacklist = on_command("删除群黑名单",aliases={"群删黑"},priority=10,permission=SUPERUSER)
@del_group_blacklist.handle()
async def del_group(matcher: Matcher,event:GroupMessageEvent,args:Message = CommandArg()):
    raw_args = args.extract_plain_text().strip()
    gid, text = check_number(str(event.group_id),'group')
    if raw_args:
        gid, text = check_number(raw_args,'group')
        if not gid == "not is number":
            await matcher.finish(MessageSegment.reply(event.message_id) + "唔...请输入一个正确的数字才可以呢。")
    data = utils.handle_json(blacklist_path,'r')
    if gid not in data["group"]:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"唔...{text}似乎本来就不在黑名单列表中。")
    data['group'].pop(gid)
    utils.handle_json(blacklist_path,'w',data)
    await matcher.finish(MessageSegment.reply(event.message_id) + f"已成功将{text}从黑名单中删除。")


add_user_blacklist = on_command("添加用户黑名单",aliases={"加用户黑"},priority=10,permission=SUPERUSER)
@add_user_blacklist.handle()
async def _add_user(matcher: Matcher,event:GroupMessageEvent,args:Message = CommandArg()):
    raw_args = args.extract_plain_text().strip()
    uid, text = check_number(str(event.group_id),'user')
    if not raw_args:
        await matcher.finish(MessageSegment.reply(event.message_id) + "唔...您不能拉黑自己，请检查参数是否正确输入了呢...")
    data = utils.handle_json(blacklist_path,'r')
    if uid in data["group"]:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"唔...{text}似乎本来就在黑名单中。")
    data['user'].append(uid)
    utils.handle_json(blacklist_path,'w',data)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"成功将{text}添加进黑名单。")

del_user_blacklist = on_command("删除用户黑名单",aliases={"删用户黑"},priority=10,permission=SUPERUSER)
@del_user_blacklist.handle()
async def _del_user(matcher: Matcher,event:GroupMessageEvent,args:Message = CommandArg()):
    raw_args = args.extract_plain_text().strip()
    uid, text = check_number(str(event.group_id),'user')
    if not raw_args:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "唔...您本来就不能拉黑自己，请检查参数是否正确输入了呢...")
    data = utils.handle_json(blacklist_path,'r')
    if uid not in data["user"]:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"唔...{text}似乎本来就不在黑名单中。")
    data['user'].remove(uid)
    utils.handle_json(blacklist_path,'w',data)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"成功将{text}从黑名单中删除。")

check_user_blacklist = on_command("查看用户黑名单",aliases={"查用户黑"},priority=10,permission=SUPERUSER)
@check_user_blacklist.handle()
async def _chek_user(bot:Bot,matcher: Matcher,event:GroupMessageEvent):
    data = utils.handle_json(blacklist_path,'r')
    text = ""
    if not data['user']:
        await matcher.finish(MessageSegment.reply(event.message_id)+"用户黑名单是空的，")
    for user_id in data['user']:
        user_info = await bot.get_stranger_info(user_id=user_id)
        user_name = user_info.get("nickname","用户名称获取失败")
        text += f"{user_name}[{user_id}]\n"
    await matcher.finish(MessageSegment.reply(event.message_id)+f"下面是黑名单用户：\n{text}")


check_group_blacklist = on_command("查看群聊黑名单",aliases={"查群黑"},priority=10,permission=SUPERUSER)
@check_user_blacklist.handle()
async def _chek_group(bot:Bot,matcher: Matcher,event:GroupMessageEvent):
    data = utils.handle_json(blacklist_path,'r')
    text = ""
    if not data['group']:
        await matcher.finish(MessageSegment.reply(event.message_id)+"群聊黑名单是空的，")
    for group_id in data['group']:
        group_info = await bot.get_group_info(group_id=group_id)
        group_name = group_info.get("group_name","群名获取失败")
        text += f"{group_name}[{group_id}]\n"
    await matcher.finish(MessageSegment.reply(event.message_id)+f"下面是黑名单群聊：\n{text}")