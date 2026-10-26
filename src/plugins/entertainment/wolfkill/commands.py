from nonebot import on_command

wolf_kill_help = on_command("狼人杀帮助", aliases={"狼人杀说明", "狼人杀指南"})
wolf_kill_auto_check = on_command("自动判定胜负")
wolf_kill_vote = on_command("投票狼人杀", aliases={"狼人杀投票"})
wolf_kill_tally = on_command("结算狼人杀投票", aliases={"狼人杀结算"})
wolf_kill_check_win = on_command("判定狼人杀胜负", aliases={"狼人杀胜负"})
wolf_kill_new = on_command("创建狼人杀", aliases={"lrsadd"})
wolf_kill_join = on_command("加入狼人杀", aliases={"lrsjoin"})
wolf_kill_start = on_command("开始狼人杀", aliases={"lrsstart"})
wolf_kill_over = on_command("结束狼人杀", aliases={"强制结束", "解散房间"})
wolf_kill_up_people = on_command("狼人杀房间人数上限", aliases={"房间上限"})
wolf_kill_down_people = on_command("狼人杀房间人数下限", aliases={"房间下限"})
