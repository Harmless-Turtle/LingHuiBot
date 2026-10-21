from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel

driver = get_driver()


class Config(BaseModel):
    """
    敏感词模块配置。

    SENSITIVEADMIN 为敏感词管理员 QQ 列表；未配置时默认为空列表。
    """

    SENSITIVEADMIN: list[str] = []


@driver.on_startup
async def print_sensitive_config() -> None:
    config = get_plugin_config(Config)

    # 敏感词管理员状态
    if config.SENSITIVEADMIN:
        logger.info(f"[SensitiveManager] 敏感词管理员配置已加载: {config.SENSITIVEADMIN}")
    else:
        logger.warning(
            "[SensitiveManager] 敏感词管理员 (SENSITIVEADMIN) 未配置，该功能未启用！"
        )
