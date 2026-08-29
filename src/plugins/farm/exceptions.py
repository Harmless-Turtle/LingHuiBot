from ..Exceptions import EntertainmentError


class FarmError(EntertainmentError):
    module = "farm"
    message = "种地系统发生异常，请稍后再试。"


class FarmBalanceNotEnough(FarmError):
    message = "墨辉币余额不足"


__all__ = ["FarmError", "FarmBalanceNotEnough"]
