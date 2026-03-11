import random as rd

# 导入调度器
from nonebot import require, get_bot, logger

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from src.plugins.utils import handle_json
from src.plugins.entertainment.check_files import bottle_path,auto_path

@scheduler.scheduled_job("cron", day="*/1", hour=10, minute=0, id="bottle")
async def bottle_run():
    # 获取群聊开关数据
    auto_switch = handle_json(auto_path,'r')
    # 筛选出打开的群聊
    open_group_list = [group for group in auto_switch.keys() if auto_switch[group]]
    if not open_group_list:
        logger.info("空列表！")
    # 获取漂流瓶数据
    data = handle_json(bottle_path, 'r')
    # 获取 Bot实例
    bot = get_bot()
    # 过滤出所有真正有内容的用户 ID (排除空列表)
    valid_users = [uid for uid, bottles in data.items() if bottles]
    # 检测到有数据，随机取一个值
    user = rd.choice(valid_users)
    result = rd.choice(data[user])
    # 删除这个数据
    data[user].remove(result)
    # 如果该用户瓶子被捡光了，删除该 Key
    if not data[user]:
        del data[user]
    stranger_info = await bot.get_stranger_info(user_id=int(user))
    nickname = stranger_info.get('nickname', '来自远方的旅人')
    # 写入文件
    handle_json(bottle_path, 'w', data)
    # 循环发送
    for open_group in open_group_list:
        await bot.send_group_msg(group_id=open_group, message=f"在遥远的大海中飘来了一个小小的瓶子，它的里面写着：{result}\n署名是：“{nickname}”")