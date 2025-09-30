from nonebot import on_message
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_orm import async_scoped_session
from src.database.models.birthday_orm import UserProfile, UserGroupUsage

# TODO: 定时任务：每日为当天生日用户在其“最常用且已开启”的群发送祝福
@scheduler.scheduled_job("cron", hour=0, minute=10)
def user_favorite_groups_process(event, session: async_scoped_session):
    pass
