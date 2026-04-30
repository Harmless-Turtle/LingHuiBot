from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message, Bot, MessageEvent, ActionFailed
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select

from .command import (
    add_group_blacklist,
    del_group_blacklist,
    add_user_blacklist,
    del_user_blacklist,
    check_user_blacklist,
    check_group_blacklist,
    check_su
)
from .model import GroupBlacklist, UserBlacklist


@add_group_blacklist.handle()
async def add_group(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    group_id = args.extract_plain_text().strip()
    if not group_id.isdigit():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "唔...请输入一个正确的数字才可以呢。"
        )

    obj = await session.get(GroupBlacklist, group_id)
    if obj is None:
        obj = GroupBlacklist(group_id=group_id)
        session.add(obj)
        await session.commit()
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"已成功将{group_id}添加进黑名单。"
        )
    else:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"唔...{group_id}已经在黑名单列表中了。"
        )


@del_group_blacklist.handle()
async def del_user(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    group_id = args.extract_plain_text().strip()
    if not group_id.isdigit():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "唔...请输入一个正确的数字才可以呢。"
        )

    obj = await session.get(GroupBlacklist, group_id)
    if obj is not None:
        await session.delete(obj)
        await session.commit()
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"已成功将{group_id}从黑名单中删除。"
        )
    else:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"唔...{group_id}似乎本来就不在黑名单列表中。"
        )


@add_user_blacklist.handle()
async def add_user(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    user_id = args.extract_plain_text().strip()
    if not user_id.isdigit():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "唔...请输入一个正确的数字才可以呢。"
        )

    if user_id == str(event.user_id):
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "唔...您不能拉黑自己，请检查参数是否正确输入了呢..."
        )

    obj = await session.get(UserBlacklist, user_id)
    if obj is None:
        obj = UserBlacklist(user_id=user_id)
        session.add(obj)
        await session.commit()
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"成功将{user_id}添加进黑名单。"
        )
    else:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"唔...{user_id}似乎本来就在黑名单中。"
        )


@del_user_blacklist.handle()
async def del_user(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    user_id = args.extract_plain_text().strip()
    if not user_id.isdigit():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "唔...请输入一个正确的数字才可以呢。"
        )

    if user_id == str(event.user_id):
        del_user_blacklist.finish("?")

    obj = await session.get(UserBlacklist, user_id)
    if obj is None:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"唔...{user_id}似乎本来就不在黑名单中。"
        )
    else:
        await session.delete(obj)
        await session.commit()
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"成功将{user_id}从黑名单中删除。"
        )


@check_user_blacklist.handle()
async def handle_check_user_blacklist(
        matcher: Matcher,
        bot: Bot,
        session: async_scoped_session,
        event: MessageEvent
):
    result = await session.execute(select(UserBlacklist))
    user_list = result.scalars().all()
    text = ""
    if not user_list:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "用户黑名单是空的"
        )
    for user in user_list:
        user_id = user.user_id
        user_info = await bot.get_stranger_info(user_id=int(user_id))
        user_name = user_info.get("nickname") or "<昵称获取失败>"
        text += f"{user_name}[{user_id}]\n"
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"下面是黑名单用户：\n{text}"
    )


@check_group_blacklist.handle()
async def handle_check_group_blacklist(
        matcher: Matcher,
        bot: Bot,
        session: async_scoped_session,
        event: MessageEvent
):
    result = await session.execute(select(GroupBlacklist))
    group_list = result.scalars().all()
    text = ""
    if not group_list:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "群聊黑名单是空的"
        )
    for group in group_list:
        group_id = group.group_id
        try:
            group_info = await bot.get_group_info(group_id=int(group_id))
            group_name = group_info.get("group_name")
        except ActionFailed:
            group_name = "<群昵称获取失败>"
        text += f"{group_name}[{group_id}]\n"
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"下面是黑名单群聊：\n{text}"
    )


@check_su.handle()
async def handle_chek_su(event: GroupMessageEvent):
    from nonebot import get_driver
    su_list = get_driver().config.superusers
    if str(event.user_id) in su_list:
        await check_su.finish(
            MessageSegment.reply(event.message_id) + "您已经是凌辉 Bot 的超级用户了。"
        )
    else:
        await check_su.finish(
            MessageSegment.reply(event.message_id) + "您不是凌辉 Bot 的超级用户。"
        )
