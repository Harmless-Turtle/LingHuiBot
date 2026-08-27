from ...Exceptions import EntertainmentError


class CurrencyError(EntertainmentError):
    module = "Currency"
    message = "货币系统发生异常，请稍后再试。"


class CurrencyBalanceNotEnough(CurrencyError):
    message = "操作失败，墨辉币余额不足"


class CurrencyInvalidAmount(CurrencyError):
    message = "金额必须大于0"
