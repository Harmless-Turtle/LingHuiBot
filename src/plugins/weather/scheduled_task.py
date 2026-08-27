from nonebot import require
from nonebot.log import logger

# 注入并获取 APScheduler 实例
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

# 🌟 核心修改：导入在 utils.py 中重构好的、支持 batch_get 合并转发的全自动推送主控函数
from .utils import run_daily_typhoon_push


@scheduler.scheduled_job("cron", day="*/1", hour=7, minute=0, id="typhoon_push")
async def check_typhoon():
    logger.info("[Typhoon Task] 触发早间台风订阅轮询与全局推送...")
    try:
        # 直接调用闭环的主推控制函数
        await run_daily_typhoon_push()
        logger.info("[Typhoon Task] 台风订阅定时推送任务执行完毕捏！")
    except Exception as e:
        logger.error(f"[Typhoon Task] 定时任务执行期间发生异常: {e}")