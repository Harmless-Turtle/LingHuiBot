from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel, model_validator

driver = get_driver()


class Config(BaseModel):
    """狼人杀子模块配置。"""

    # 狼人杀人数限制配置（未填则不启动该子模块）
    LRS_MIN_PLAYER: int | None = None
    LRS_MAX_PLAYER: int | None = None

    @model_validator(mode="after")
    def validate_player_range(self) -> "Config":
        if self.LRS_MIN_PLAYER is not None and self.LRS_MAX_PLAYER is not None:
            if self.LRS_MIN_PLAYER <= 0 or self.LRS_MAX_PLAYER <= 0:
                raise ValueError("狼人杀人数限制必须大于 0")
            if self.LRS_MIN_PLAYER > self.LRS_MAX_PLAYER:
                raise ValueError(
                    f"狼人杀最小人数 ({self.LRS_MIN_PLAYER}) 不能大于最大人数 ({self.LRS_MAX_PLAYER})"
                )
        return self


@driver.on_startup
async def print_wolfkill_config() -> None:
    config = get_plugin_config(Config)

    if config.LRS_MIN_PLAYER is not None and config.LRS_MAX_PLAYER is not None:
        logger.info(
            f"狼人杀人数范围配置已加载: {config.LRS_MIN_PLAYER}~{config.LRS_MAX_PLAYER}"
        )
    else:
        logger.warning(
            "狼人杀配置不完整，该功能未启用！"
        )
