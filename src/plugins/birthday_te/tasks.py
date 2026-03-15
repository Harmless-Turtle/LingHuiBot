from datetime import date, timedelta,datetime

import nonebot
from nonebot.adapters.onebot.v11 import MessageSegment, Bot
from nonebot.matcher import Matcher
from nonebot_plugin_apscheduler import scheduler

from .models import GroupSettings, UserBirthdayData


driver = nonebot.get_driver()


@driver.on_startup
async def setup_birthday_scheduler():
    _ = scheduler.add_job(
        _init_birthday_jobs,
        "cron",
        hour=0,
        minute=0,
        id="birthday:init",
        misfire_grace_time=120,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )


async def _init_birthday_jobs(
        bot: Bot,
        matcher:Matcher,
        group_settings:GroupSettings,
        user_birthday:UserBirthdayData,
):
    if not group_settings.enable:
        await matcher.finish()
    date = user_birthday.birthday_date
    user_id = user_birthday.user_id
    dt = datetime.strptime(date, "%Y-%m-%d")
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    age_text = f"今天是群里小寿星 {nickname} 的生日嗷呜！"
    age = date.today().year - dt.year
    if dt.year != 1900 and age > 0:
        age_text = f"今天是小寿星 {nickname} 的{age}岁生日！"
    if dt.day == date.today().day and dt.month == date.today().month:
        await bot.send_group_msg(message=MessageSegment.at(user_id)+f"{age_text}\n祝{nickname}生日快乐呢~\n",group_id=int(group_settings.group_id))