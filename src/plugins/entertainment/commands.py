from nonebot import get_driver
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot
from nonebot.plugin import on_command  # 导入事件响应器


async def is_admin(bot: Bot, event: GroupMessageEvent) -> bool:
    member_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    superusers = get_driver().config.superusers
    # 角色为 admin 或 owner，或者属于超级用户
    return member_info['role'] in ('admin', 'owner') or str(event.user_id) in superusers


#########################
#                    结婚系统 触发器                   #
#########################
marry_random = on_command("结婚", block=True)
finish_marry = on_command("离婚", block=True)
marry_propose = on_command("求婚", priority=10, block=True)
marry_time_check = on_command("结婚时间", block=True, aliases={"结婚时长"})
marry_select = on_command("同意求婚", aliases={"拒绝求婚", "取消求婚"}, block=True)
marry_check = on_command("查看对象", aliases={"我的对象"}, block=True)
marry_chek_others = on_command("群友对象", block=True)
marry_switch = on_command("换老婆")

#########################
#                     漂流瓶 触发器                      #
#########################
add_battle = on_command("扔漂流瓶", aliases={"丢漂流瓶", "投漂流瓶"})
pick_battle = on_command("捡漂流瓶", aliases={"捞漂流瓶"})
auto_switch_battle = on_command("漂流模式")

#########################
#                     狼人杀 触发器                      #
#########################

# wolf_kill_new = on_command("创建狼人杀", aliases={'lrsadd'})
# wolf_kill_join = on_command("加入狼人杀", aliases={'lrsjoin'})
# wolf_kill_start = on_command("开始狼人杀", aliases={'lrsstart'})
# wolf_kill_over = on_command("结束狼人杀", aliases={"强制结束", "解散房间"})
# wolf_kill_up_people = on_command("狼人杀房间人数上限", aliases={"房间上限"})
# wolf_kill_down_people = on_command("狼人杀房间人数下限", aliases={"房间下限"})

#########################
#                      货币 触发器                        #
#########################

add_coin = on_command("添加货币", aliases={"加钱"}, block=True, permission=is_admin)
check_coin = on_command("我的余额", aliases={"余额"}, block=True)
ranking_coin = on_command("墨辉币排行")

#########################
#             货币子系统<银行> 触发器               #
#########################
robbery = on_command("抢劫", aliases={"打劫"}, block=True)
guess_number = on_command("猜数字", aliases={"猜数"}, block=True)
bank_transfer = on_command("转账", block=True)
bank_save = on_command("存钱", block=True)
bank_remove = on_command("取钱", aliases={"取款"}, block=True)
bank_money = on_command("存款", aliases={"我的存款"}, block=True)
bank_robbery = on_command("抢银行", block=True)

#########################
#             货币子系统<钓鱼> 触发器               #
#########################
fishing_downswing = on_command("钓鱼", block=True)
buy_fishing_hook = on_command("购买鱼钩")
buy_fishing_rod = on_command("购买鱼竿")
buy_fishing_bait = on_command("购买饵料")
fishing_hook_attribute = on_command("鱼钩属性")

#########################
#                 表情包制作 触发器                   #
#########################
meme_matcher = on_command("制作表情", aliases={"表情制作", "摸"})
meme_list_matcher = on_command("表情列表", aliases={"meme列表", "memelist"})

#########################
#                 塔罗牌制作 触发器                   #
#########################
tarot = on_command("塔罗牌", priority=10, block=True)
divine = on_command(cmd="占卜", priority=10, block=True)
