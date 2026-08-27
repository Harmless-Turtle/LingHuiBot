from nonebot.plugin import on_command  # 导入事件响应器

birthday_switch = on_command("生日祝贺")
birthday_add = on_command("生日设置", aliases={"我的生日是"})
birthday_del = on_command("删除生日")
