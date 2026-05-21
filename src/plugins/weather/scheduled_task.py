from nonebot import require, get_bot
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from nonebot.log import logger
from nonebot_plugin_orm import get_session
from sqlalchemy import select

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from .models import TyphoonSubscribe
from .utils import check_and_get_new_typhoon_card


@scheduler.scheduled_job("cron", day="*/1", hour=7, minute=0, id="typhoon_push")
async def check_typhoon():
    logger.info("[Typhoon Task] 触发晚间台风订阅轮询...")

    async with get_session() as session:
        stmt = select(TyphoonSubscribe.group_id).where(TyphoonSubscribe.enable == True)
        result = await session.scalars(stmt)
        subscribed_groups = list(result)

    if not subscribed_groups:
        logger.info("[Typhoon Task] 当前没有任何群聊开启台风订阅，任务结束。")
        return

    logger.info(f"[Typhoon Task] 当前检测到开启订阅的群有: {subscribed_groups}")

    try:
        img_bytes = await check_and_get_new_typhoon_card()
        if img_bytes is None:
            logger.info("[Typhoon Task] 未检测到新台风数据，不执行推送。")
            return
        img_segment = MessageSegment.image(img_bytes)
        # 获取 Bot 实例并广播
        bot: Bot = get_bot()
        for group_id in subscribed_groups:
            try:
                await bot.send_group_msg(
                    group_id=group_id,
                    message=f"{img_segment}"
                )
                logger.info(f"[Typhoon Task] 已成功向群 {group_id} 推送台风动态卡片捏！")
            except Exception as group_err:
                logger.error(f"[Typhoon Task] 向群 {group_id} 推送失败，原因: {group_err}")

    except Exception as e:
        logger.error(f"[Typhoon Task] 定时任务执行期间发生异常: {e}")