from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command, on_message
from nonebot.rule import to_me

# ================= 1. Furry AI 对话子模块 (furry_ai) =================
# AI 对话（@机器人触发）
cmd_ai_chat = on_message(rule=to_me(), priority=99, block=True)
# 模型列表
cmd_ai_model_list = on_command("模型列表", permission=SUPERUSER)
# 模型切换
cmd_ai_model_switch = on_command("更改模型", aliases={"更换模型", "模型切换", "切换模型"}, block=True)
# 查询当前用户模型
cmd_ai_model_current = on_command("当前模型", aliases={"我的模型"}, block=True)
# 重置对话
cmd_ai_chat_reset = on_command("Reset", aliases={"重置对话", "重置模型"})
# 上次对话
cmd_ai_chat_last = on_command("上次对话", aliases={"上次聊天", "最后对话", "最后记录"})
# 删除/清空信息
cmd_ai_chat_clear = on_command("删除信息", aliases={"重置fb", "清空数据"})
# 更改/定义个人预设
cmd_ai_user_config = on_command("更改用户信息", aliases={"创建用户信息", "定义个人信息"}, block=False)

# ================= 2. Furry 兽聚展会子模块 (furry_con) =================
# 兽聚列表
cmd_con_list = on_command("今年兽聚", aliases={"兽聚列表", "兽聚汇总"}, priority=10, block=True)
# 兽聚查询
cmd_con_check = on_command("兽聚查询", block=True)
# 兽聚详细信息
cmd_con_info = on_command("兽聚信息", aliases={"兽聚详情"}, block=True)
# 兽聚历史
cmd_con_history = on_command("兽聚历史", aliases={"历史兽聚"}, block=True)

# ================= 3. 鉴毛与毛照图库子模块 (furry_suit) =================
# 鉴毛
cmd_suit_see = on_command("鉴毛", aliases={"每日鉴毛"}, priority=10, block=True)
# 随机毛照/兽图
cmd_suit_random = on_command(
    "来只",
    aliases={"来只毛", "来只兽兽", "来只兽", "云来只", "云来只毛", "云来只兽兽", "云来只兽"},
    priority=10,
    block=True,
)
# 查看毛照列表
cmd_suit_list = on_command("查列表", aliases={"查列表#", "查兽兽"}, priority=10, block=True)
# 投图上传
cmd_suit_upload = on_command("上传", aliases={"投图"}, priority=10, block=True)
# 修改图片
cmd_suit_modify = on_command("修改图片", priority=99, block=True)
# 待审核列表 (仅 SUPERUSER)
cmd_suit_review_list = on_command(
    "待审核列表",
    aliases={"审核列表", "上传列表"},
    priority=100,
    block=True,
    permission=SUPERUSER,
)
# 审核上传决定 (仅 SUPERUSER)
cmd_suit_review_upload = on_command(
    "同意上传#",
    aliases={"同意下载#", "拒绝上传#", "拒绝下载#"},
    priority=99,
    block=True,
    permission=SUPERUSER,
)
# 审核修改决定 (仅 SUPERUSER)
cmd_suit_review_modify = on_command(
    "同意修改#",
    aliases={"拒绝修改#"},
    priority=99,
    block=True,
    permission=SUPERUSER,
)
cmd_suit_review_decide = cmd_suit_review_upload
cmd_suit_modify_decide = cmd_suit_review_modify

# ================= 兼容旧名称别名 =================
furrybar = cmd_ai_chat
fb_model_list = cmd_ai_model_list
user_model_switch = cmd_ai_model_switch
check_model = cmd_ai_model_current
reset_furrybar = cmd_ai_chat_reset
latest = cmd_ai_chat_last
clear = cmd_ai_chat_clear
change_config = cmd_ai_user_config

furryfusion_list = cmd_con_list
furryfusion_check = cmd_con_check
furryfusion_information = cmd_con_info
furryfusion_history = cmd_con_history

see_furry = cmd_suit_see
furry_random = cmd_suit_random
furry_list = cmd_suit_list
upload_furry = cmd_suit_upload
modify_furry = cmd_suit_modify
check_upload = cmd_suit_review_list
check_upload_decide = cmd_suit_review_upload
check_modify_decide = cmd_suit_review_modify
