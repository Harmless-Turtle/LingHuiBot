from ..Exceptions import EntertainmentError


class FishingError(EntertainmentError):
    module = "fishing"
    message = "钓鱼系统发生异常，请稍后再试。"


class FishingBalanceNotEnough(FishingError):
    message = "墨辉币余额不足"


__all__ = ["FishingError", "FishingBalanceNotEnough"]
