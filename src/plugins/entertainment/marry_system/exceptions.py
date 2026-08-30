from ...Exceptions import EntertainmentError


class MarryError(EntertainmentError):
    module = "marry"
    message = "结婚系统发生异常，请稍后再试。"


class MarryNotMarried(MarryError):
    message = "你似乎还没有对象吧xwx"


class MarryAlreadyMarried(MarryError):
    message = "你似乎已经有对象了吧...？"


class MarryLimitReached(MarryError):
    message = "你已经结婚太多次了啦！第二天再结~"


class MarryNoCandidate(MarryError):
    message = "这个群好像没有其他人了呢..."


__all__ = [
    "MarryError",
    "MarryNotMarried",
    "MarryAlreadyMarried",
    "MarryLimitReached",
    "MarryNoCandidate",
]
