from nonebot.plugin import on_command

menu = on_command("菜单", aliases={"凌辉菜单"}, priority=98, block=True)
main_menu = on_command("菜单01", aliases={"基本菜单"}, priority=99, block=True)
furry_menu = on_command("菜单02", aliases={"Furry菜单", "furry菜单"}, priority=99, block=True)
marry_menu = on_command("菜单03", aliases={"娱乐菜单"}, priority=99, block=True)
admin_menu = on_command("菜单04",aliases={"管理菜单"},priority=99, block=True)
service_menu = on_command("服务条款", aliases={"用户协议"}, block=True)