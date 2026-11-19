from nonebot import on_command

course_import = on_command("导入课表", aliases={"上传课表"}, priority=6, block=True)
course_week = on_command("本周课表", priority=6, block=True)
course_today = on_command("今日课表", priority=6, block=True)
course_clear = on_command("清除课表", priority=6, block=True)
