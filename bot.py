import nonebot
from nonebot.adapters.onebot.v11 import Adapter

nonebot.init(dotenv_path=".env")

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(Adapter)

# 加载插件
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()