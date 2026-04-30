class LingHuiError(Exception):
    """凌辉 Bot 的统一异常基类。"""
    message = "操作失败，请稍后再试。"
    module = ""

    def __init__(self, message: str = None):
        self.message = message or self.message
        super().__init__(self.message)


class UserVisibleError(LingHuiError):
    message = "操作失败，请稍后再试。"


class BusinessRuleError(LingHuiError):
    message = "当前操作不符合规则。"


class ConfigError(LingHuiError):
    message = "配置项缺失或有误，请联系管理员。"


class DataError(LingHuiError):
    message = "数据处理失败，请稍后再试。"


class ExternalServiceError(LingHuiError):
    message = "外部服务暂时不可用，请稍后再试。"


class ModuleError(LingHuiError):
    message = "模块运行异常，请稍后再试。"


class MainError(ModuleError):
    message = "主功能模块发生异常，请稍后再试。"


class EntertainmentError(ModuleError):
    message = "娱乐功能模块发生异常，请稍后再试。"


class CurrencyError(EntertainmentError):
    message = "货币系统发生异常，请稍后再试。"


class BlacklistError(ModuleError):
    message = "黑名单模块发生异常，请稍后再试。"


class FurryModuleError(EntertainmentError):
    message = "Furry 功能模块发生异常，请稍后再试。"
