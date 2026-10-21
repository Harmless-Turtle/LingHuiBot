from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel, Field

driver = get_driver()


class Config(BaseModel):
    """敏感词模块配置。

    SENSITIVEADMIN 为敏感词管理员 QQ 列表；未配置时沿用历史内置名单。
    """

    SENSITIVEADMIN: list[str] = Field(
        default_factory=lambda: ["1097740481", "1692719245"]
    )


@driver.on_startup
async def print_sensitive_config() -> None:
    config = get_plugin_config(Config)
    logger.info(f"[Sensitive] 敏感词管理员: {config.SENSITIVEADMIN}")
