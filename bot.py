#                    _ooOoo_
#                   o8888888o
#                   88" . "88
#                   (| -_- |)
#                    O\ = /O
#                ____/`---'\____
#              .   ' \\| |// `.
#               / \\||| : |||// \
#             / _||||| -:- |||||- \
#               | | \\\ - /// | |
#             | \_| ''\---/'' | |
#              \ .-\\__ `-` ___/-. /
#           ___`. .' /--.--\ `. . __
#        ."" '< `.___\_<|>_/___.' >'"".
#       | | : `- \`.;`\ _ /`;.`/ - ` : | |
#         \ \ `-. \_ __\ /__ _/ .-` / /
# ======`-.____`-.___\\_____/___.-`____.-'======
#                    `=---='
#
# .............................................
#          佛祖保佑             永无BUG
#   孩子们不写注释你们看着办吧，下一版再加回来[doge]


import os
from pathlib import Path

# ==================== 1. 环境变量迁移 (Pre-flight) ====================
ENV_MIGRATIONS = {
    "FURRY_TOKEN": "FURRY_CON_TOKEN",
    "FURRY_USER": "FURRY_CON_USER",
    "FURRY_PASSWORD": "FURRY_CON_PASSWORD",
    "FURRY_AIKEY": "FURRY_AI_KEY",
    "FURRY_SPECIAL_EVENTS": "FURRY_CON_SPECIAL_EVENTS",
    "FURRY_AI_BASEURL": "FURRY_AI_BASE_URL",
    "FURRY_AI_MODELLIST": "FURRY_AI_MODEL_LIST",
    "FURRY_SEE_FURRY": "FURRY_SUIT_BASE_URL",
    "FURRY_SEE_FURRY_KEY": "FURRY_SUIT_KEY",
}


def migrate_env_file() -> None:
    for filename in (".env", ".env.prod"):
        path = Path(filename)
        if not path.is_file():
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        existing_keys = set()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _ = stripped.split("=", 1)
                existing_keys.add(k.removeprefix("export ").strip())

        modified = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, v = stripped.split("=", 1)
                k_clean = k.removeprefix("export ").strip()
                if k_clean in ENV_MIGRATIONS:
                    new_k = ENV_MIGRATIONS[k_clean]
                    # 若文件中已存在新键，直接移除旧行避免重复
                    if new_k in existing_keys:
                        modified = True
                        continue
                    prefix = "export " if k.strip().startswith("export ") else ""
                    new_lines.append(f"{prefix}{new_k}={v}")
                    existing_keys.add(new_k)
                    modified = True
                    continue
            new_lines.append(line)

        if modified:
            path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


migrate_env_file()

# ==================== 2. NoneBot 初始化与插件加载 ====================
import nonebot
from nonebot import require
from nonebot.adapters.onebot.v11 import Adapter
import bilichat_request

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

# 加载插件
require("nonebot_plugin_orm")
require("nonebot_plugin_apscheduler")
require("nonebot_plugin_multincm")
require("nonebot_plugin_datastore")
require("nonebot_plugin_localstore")
require("nonebot_plugin_htmlrender")
require("nonebot_plugin_kawaii_status")
require("nonebot_plugin_bilichat")
require("nonebot_plugin_mc_server_status")
nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run()
