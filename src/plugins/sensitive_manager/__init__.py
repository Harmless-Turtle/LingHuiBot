# your_bot/bots/sensitive_manager/__init__.py
from .sensitive_check import (
    sensitive_matcher,
    cmd_add,
    cmd_del,
    cmd_list,
    cmd_group
)

# 导出插件元数据
__plugin_name__ = "敏感词检测"
__plugin_usage__ = """
[!] 需要管理员权限的命令：
添加敏感词 [词语]    - 添加新敏感词
删除敏感词 [词语]    - 删除现有敏感词
列出敏感词          - 显示所有敏感词
敏感词开关 [开启/关闭] - 控制本群检测
"""

# 导出处理器以便NoneBot自动加载
__all__ = [
    "sensitive_matcher",
    "cmd_add",
    "cmd_del",
    "cmd_list",
    "cmd_group"
]