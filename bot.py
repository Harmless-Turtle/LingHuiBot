import nonebot
from nonebot import require
from nonebot.adapters.onebot.v11 import Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

# 加载插件
require("nonebot_plugin_orm")
require("nonebot_plugin_apscheduler")
require("nonebot_plugin_picmcstat")
require("nonebot_plugin_multincm")
require("nonebot_plugin_datastore")
require("nonebot_plugin_localstore")
require("nonebot_plugin_mc_server_status")
require("nonebot_plugin_htmlrender")
nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run()
