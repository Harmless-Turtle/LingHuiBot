from nonebot import on_command

# 敏感词管理
cmd_add = on_command("添加敏感词", aliases={"敏感词添加"})
cmd_del = on_command("删除敏感词", aliases={"敏感词删除"})
cmd_list = on_command("敏感词列表", aliases={"list_words"})
cmd_group = on_command("敏感词检测", aliases={"敏感词开关"})
