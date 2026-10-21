from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel, HttpUrl, ValidationInfo, field_validator

driver = get_driver()


class Config(BaseModel):
    """天气模块配置（和风天气 JWT 鉴权）。"""

    WEATHER_API_KEY: str | None = None
    WEATHER_PROJECT_ID: str | None = None
    WEATHER_EXPIRED_TIME: int = 30
    WEATHER_JWT_ID: str | None = None
    WEATHER_API_BASEURL: str | None = None

    @field_validator("WEATHER_API_BASEURL")
    @classmethod
    def check_and_clean_base_url(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v:
            try:
                HttpUrl(v)
            except Exception as e:
                logger.error(
                    f"[Weather] 配置项 {info.field_name} 不是合法的 HTTP(S) URL: {v} ({e})"
                )
            return v.rstrip("/")
        return v


@driver.on_startup
async def print_weather_config() -> None:
    config = get_plugin_config(Config)

    # 和风天气 (Weather) 状态
    if (
        config.WEATHER_API_KEY
        and config.WEATHER_PROJECT_ID
        and config.WEATHER_JWT_ID
        and config.WEATHER_API_BASEURL
    ):
        logger.info("[Weather] 和风天气 (Weather) 配置已加载")
    else:
        logger.warning(
            "[Weather] 和风天气 (Weather) 配置不完整，该功能未启用！"
        )
