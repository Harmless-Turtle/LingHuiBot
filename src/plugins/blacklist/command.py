from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command

add_group_blacklist = on_command("添加群聊黑名单", aliases={"群加黑", "拉黑群聊"}, priority=10, permission=SUPERUSER)
del_group_blacklist = on_command("删除群黑名单", aliases={"群删黑", "移出群黑"}, priority=10, permission=SUPERUSER)
add_user_blacklist = on_command("添加用户黑名单", aliases={"加用户黑", "拉黑用户"}, priority=10, permission=SUPERUSER)
del_user_blacklist = on_command("删除用户黑名单", aliases={"删用户黑", "移出用户黑名单"}, priority=10, permission=SUPERUSER)
check_user_blacklist = on_command("查看用户黑名单",aliases={"查黑用户"},priority=10,permission=SUPERUSER)
check_group_blacklist = on_command("查看群聊黑名单",aliases={"查群黑"},priority=10,permission=SUPERUSER)
check_su = on_command("凌辉su",priority=10)
