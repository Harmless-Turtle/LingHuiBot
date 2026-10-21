from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel, HttpUrl, ValidationInfo, field_validator

driver = get_driver()


class Config(BaseModel):
    # Furry AI 对话 (FurryBar) 相关配置
    FURRY_AI_KEY: str | None = None
    FURRY_AI_BASE_URL: str | None = None
    FURRY_AI_MODEL_LIST: str | None = None

    # Furry 兽聚展会 (furry_con) 相关配置
    FURRY_CON_TOKEN: str | None = None
    FURRY_CON_USER: str | None = None
    FURRY_CON_PASSWORD: str | None = None
    FURRY_CON_SPECIAL_EVENTS: list[str] = []

    # 鉴毛 (Fursuit / furry_suit) 相关配置
    FURRY_SUIT_BASE_URL: str | None = None
    FURRY_SUIT_KEY: str | None = None

    @field_validator("FURRY_AI_BASE_URL", "FURRY_AI_MODEL_LIST", "FURRY_SUIT_BASE_URL")
    @classmethod
    def check_url(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v:
            try:
                HttpUrl(v)
            except Exception as e:
                logger.error(
                    f"[FurryModule] 配置项 {info.field_name} 不是合法的 HTTP(S) URL: {v} ({e})"
                )
        return v


@driver.on_startup
async def print_furry_config():
    config = get_plugin_config(Config)

    # 1. Furry AI 状态
    ai_fields = [config.FURRY_AI_KEY, config.FURRY_AI_BASE_URL, config.FURRY_AI_MODEL_LIST]
    if all(ai_fields):
        logger.info("[FurryModule] Furry AI (FurryBar) 配置已加载")
    elif any(ai_fields):
        logger.warning("[FurryModule] Furry AI 配置不完整（部分项缺失），该子功能未启用！")
    else:
        logger.info("[FurryModule] Furry AI 未配置（子功能未启用）")

    # 2. Furry Con (兽聚) 状态
    con_fields = [config.FURRY_CON_TOKEN, config.FURRY_CON_USER, config.FURRY_CON_PASSWORD]
    if all(con_fields):
        logger.info("[FurryModule] 兽聚 (FurryCon) 配置已加载")
    elif any(con_fields):
        logger.warning("[FurryModule] 兽聚 (FurryCon) 配置不完整（部分项缺失），该子功能未启用！")
    else:
        logger.info("[FurryModule] 兽聚 (FurryCon) 未配置（子功能未启用）")

    # 3. Furry Suit (鉴毛) 状态
    suit_fields = [config.FURRY_SUIT_BASE_URL, config.FURRY_SUIT_KEY]
    if all(suit_fields):
        logger.info("[FurryModule] 鉴毛 (FurrySuit) 配置已加载")
    elif any(suit_fields):
        logger.warning("[FurryModule] 鉴毛 (FurrySuit) 配置不完整（部分项缺失），该子功能未启用！")
    else:
        logger.info("[FurryModule] 鉴毛 (FurrySuit) 未配置（子功能未启用）")

