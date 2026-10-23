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
                    f"配置项 {info.field_name} 不是合法的 HTTP(S) URL: {v} ({e})"
                )
        return v

    @property
    def is_ai_configured(self) -> bool:
        return bool(
            self.FURRY_AI_KEY
            and self.FURRY_AI_BASE_URL
            and self.FURRY_AI_MODEL_LIST
        )

    @property
    def is_con_configured(self) -> bool:
        return bool(
            self.FURRY_CON_TOKEN
            and self.FURRY_CON_USER
            and self.FURRY_CON_PASSWORD
        )

    @property
    def is_suit_configured(self) -> bool:
        return bool(self.FURRY_SUIT_BASE_URL and self.FURRY_SUIT_KEY)


@driver.on_startup
async def print_furry_config():
    config = get_plugin_config(Config)

    # 1. FurryBar 状态
    if config.is_ai_configured:
        logger.info(
            f"FurryBar 配置已加载: BASE_URL={config.FURRY_AI_BASE_URL}, MODEL_LIST={config.FURRY_AI_MODEL_LIST}"
        )
    else:
        logger.warning(
            "FurryBar 配置不完整，该功能未启用！"
        )

    # 2. FurryCon 状态
    if config.is_con_configured:
        logger.info(
            f"兽聚 (FurryCon) 配置已加载: USER={config.FURRY_CON_USER}, SPECIAL_EVENTS={config.FURRY_CON_SPECIAL_EVENTS}"
        )
    else:
        logger.warning(
            "FurryCon 配置不完整，该功能未启用！"
        )

    # 3. FurrySuit (鉴毛) 状态
    if config.is_suit_configured:
        logger.info(
            f"鉴毛 (FurrySuit) 配置已加载: BASE_URL={config.FURRY_SUIT_BASE_URL}"
        )
    else:
        logger.warning(
            "FurrySuit 配置不完整，该功能未启用！"
        )
