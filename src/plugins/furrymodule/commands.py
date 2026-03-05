from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command, on_message
from nonebot.rule import to_me

# ================= Foxtail-Furry 兽云祭服务 =================
# 随机兽图
furry_random = on_command("来只兽兽", aliases={"来只毛", "来只", "来只兽"}, priority=10, block=True)
# 指定兽图
furry_picture = on_command("指定", aliases={"指定#"}, priority=10, block=True)
# 获取列表
furry_list = on_command("查列表", aliases={"查列表#", "查兽兽"}, priority=10, block=True)
# 兽图状态
furry_status = on_command("兽图状态", aliases={"兽图状态#"}, priority=10, block=True)
# 获取服务器信息
service_status = on_command("服务器状态", aliases={"兽云祭信息", "兽云祭状态", "服务状态"}, priority=10, block=True)

# ================= 投图审核系统（仅SUPERUSER） =================
# 获取审核列表
check_upload = on_command(
    "待审核列表",
    aliases={"审核列表", "上传列表"},
    priority=100,
    block=True,
    permission=SUPERUSER
)
# 决定是否上传
check_upload_decide = on_command(
    "同意上传#", aliases={"同意上载#", "拒绝上传#", "拒绝上载#"},
    priority=99,
    block=True,
    permission=SUPERUSER
)
# 清空上传数据
upload_clear = on_command("清空上传数据", aliases={"清除上传"}, permission=SUPERUSER)

# ================= FurryPic.upload 兽云祭上传子模块 =================
# 一键上传
upload_furry = on_command("一键上传", aliases={"投图", "管理员上传"}, priority=10, block=True)
# 批量上传
batch_upload = on_command("批量投图", aliases={"批量上传"}, block=True)
# 定义批量上传
batch_set = on_command("定义#", aliases={"定义"}, priority=10, block=True)
# 上传调试（仅SUPERUSER）
debugger_upload = on_command("调试", aliases={"上传调试", "上图调试"}, priority=1, permission=SUPERUSER)
# 修改图片（仅SUPERUSER）
modify_furry = on_command("修改图片", priority=99, block=True, permission=SUPERUSER)

# ================= FurryFusion 兽聚汇总服务 =================
# 今年兽聚列表
furryfusion_list = on_command(
    "今年兽聚", aliases={"兽聚列表", "兽聚汇总"}, priority=10, block=True)
# 兽聚查询
furryfusion_check = on_command("兽聚查询", block=True)
# 兽聚倒计时
furryfusion_countdown = on_command("兽聚倒计时", block=True)
# 兽聚快讯
furryfusion_quick_information = on_command("兽聚快讯#", block=True)
# 兽聚详细信息
furryfusion_information = on_command("兽聚信息", aliases={"兽聚详情"}, block=True)

# ================= FurryBar =================
# AI对话（@机器人触发）
furrybar = on_message(rule=to_me(), priority=99, block=True)
# 模型切换
user_model_switch = on_command("更改模型",aliases={"更换模型","模型切换","切换模型"},block=True)
# 更改/创建用户信息
change_config = on_command("更改用户信息", aliases={"创建用户信息", "定义个人信息"}, block=False)
# 重置对话
reset_furrybar = on_command("Reset", aliases={"重置对话", "重置模型"})
# 查询当前的用户模型
check_model = on_command("当前模型",aliases={"我的模型"},block=True)
# 删除/清空信息
clear = on_command("删除信息", aliases={"重置fb", "清空数据"})
# 上次对话
latest = on_command("上次对话", aliases={"上次聊天", "最后对话", "最后记录"})
# 模型列表
fb_model_list = on_command("模型列表",permission=SUPERUSER)
