from nonebot.plugin import on_command  # 导入事件响应器




#########################
#     结婚系统 触发器      #
#########################
marry_random = on_command("结婚",block=True)
finish_marry = on_command("离婚",block=True)
marry_propose = on_command("求婚",priority=10,block=True)
marry_time_check = on_command("结婚时间",block=True, aliases={"结婚时长"})
marry_select = on_command("同意求婚",aliases={"拒绝求婚","取消求婚"},block=True)
marry_check = on_command("查看对象",aliases={"我的对象"},block=True)
marry_chek_others = on_command("群友对象",block=True)
marry_switch = on_command("换老婆")


#########################
#      漂流瓶 触发器       #
#########################
add_battle = on_command("扔漂流瓶",aliases={"丢漂流瓶","bottle"})
pick_battle = on_command("捡漂流瓶")
auto_switch_battle = on_command("漂流模式")