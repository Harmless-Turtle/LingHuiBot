from ..Exceptions import MainError


class SignInError(MainError):
    module = "main"
    message = "签到功能发生异常，请稍后再试。"


class AlreadySignedToday(SignInError):
    message = "你今天已经在本群签到啦~"


__all__ = ["SignInError", "AlreadySignedToday"]
