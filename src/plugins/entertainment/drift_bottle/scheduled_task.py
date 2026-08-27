import random as rd
from pathlib import Path

# 导入调度器
from nonebot import require, get_bot
from nonebot.adapters.onebot.v11 import Bot
from nonebot_plugin_orm import get_session
from sqlalchemy.exc import SQLAlchemyError

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from ...utils import handle_json
from .exceptions import DriftBottleError
from .models import get_enabled_drift_bottle_group_ids, get_random_drift_bottle


@scheduler.scheduled_job("cron", day="*/1", hour=10, minute=0, id="bottle")
async def bottle_run():
    async with get_session() as session:
        try:
            scoped_session = session
            open_group_list = await get_enabled_drift_bottle_group_ids(scoped_session)
            if not open_group_list:
                return

            bottle = await get_random_drift_bottle(scoped_session)
            if bottle is None:
                aword_path = Path.cwd() / 'data' / 'main' / "aword.json"
                word_list = handle_json(aword_path, 'r')
                result = word_list[rd.randint(0, len(word_list) - 1)]
                bot: Bot = get_bot()
                for open_group in open_group_list:
                    try:
                        group_id = int(open_group)
                    except (TypeError, ValueError):
                        continue
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=f"大海里一眼望不到头，但就是没有看到漂流瓶呢qwq...\n"
                                f"但是有一个一言的瓶子，送给群友捏w\n"
                                f"“{result}”"
                    )
                return

            user = bottle.user_id
            result = bottle.data
            await session.commit()

        except DriftBottleError:
            raise
        except SQLAlchemyError as e:
            await session.rollback()
            raise DriftBottleError from e

    bot: Bot = get_bot()
    stranger_info = await bot.get_stranger_info(user_id=int(user))
    nickname = stranger_info.get('nickname', '来自远方的旅人')
    # 循环发送
    for open_group in open_group_list:
        try:
            group_id = int(open_group)
        except (TypeError, ValueError):
            continue
        await bot.send_group_msg(
            group_id=group_id,
            message=f"在遥远的大海中飘来了一个小小的瓶子，它的里面写着：{result}\n"
                    f"署名是：“{nickname}”"
        )
