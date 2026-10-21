from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel

driver = get_driver()


class Config(BaseModel):
    """天气模块配置（和风天气 JWT 鉴权）。

    五项都没有默认业务值：未配置时 API Key 为空字符串，相关命令会提示不可用。
    """

    WEATHER_API_KEY: str = ""
    WEATHER_PROJECT_ID: str = ""
    WEATHER_EXPIRED_TIME: int = 30
    WEATHER_JWT_ID: str = ""
    WEATHER_API_BASEURL: str = ""


@driver.on_startup
async def print_weather_config() -> None:
    config = get_plugin_config(Config)
    logger.info(
        f"[Weather] BASEURL={config.WEATHER_API_BASEURL or '(未配置)'} "
        f"PROJECT_ID={config.WEATHER_PROJECT_ID or '(未配置)'} "
        f"EXPIRED_TIME={config.WEATHER_EXPIRED_TIME}"
    )
    if not config.WEATHER_API_KEY:
        logger.warning("未配置 WEATHER_API_KEY，天气查询功能将不可用。")
