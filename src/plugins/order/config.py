from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel, Field

driver = get_driver()


class Config(BaseModel):
    ORDER_ADMIN: list = Field(default_factory=list)


@driver.on_startup
async def print_order_config():
    config = get_plugin_config(Config)
    logger.info(f"[Order] 当前配置项 ORDER_ADMIN: {config.ORDER_ADMIN}")
