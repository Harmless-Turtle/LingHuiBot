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
#              \ .-\__ `-` ___/-. /
#           ___`. .' /--.--\ `. . __
#        ."" '< `.___\_<|>_/___.' >'"".
#       | | : `- \`.;`\ _ /`;.`/ - ` : | |
#         \ \ `-. \_ __\ /__ _/ .-` / /
# ======`-.____`-.___\_____/___.-`____.-'======
#                    `=---='
#
# .............................................
#          佛祖保佑             永无BUG
#   孩子们不写注释你们看着办吧，下一版再加回来[doge]


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
# require("nonebot_plugin_mcserver_status_check")
nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run()
