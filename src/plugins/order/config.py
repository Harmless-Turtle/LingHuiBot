from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel, Field

driver = get_driver()


class Config(BaseModel):
    ORDER_ADMIN: list = Field(default_factory=list)


@driver.on_startup
async def print_order_config():
    config = get_plugin_config(Config)
    if config.ORDER_ADMIN:
        logger.info(f"点单管理员配置已加载: {config.ORDER_ADMIN}")
    else:
        logger.warning("点单管理员配置不完整，该功能未启用！")
