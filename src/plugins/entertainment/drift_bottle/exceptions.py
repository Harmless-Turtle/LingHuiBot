from ...Exceptions import EntertainmentError


class DriftBottleError(EntertainmentError):
    module = "DriftBottle"
    message = "漂流瓶功能发生异常，请稍后再试。"
