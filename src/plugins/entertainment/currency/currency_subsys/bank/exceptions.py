from ...exceptions import CurrencyError


class BankError(CurrencyError):
    module = "bank"
    message = "银行系统发生异常，请稍后再试。"


class BankBalanceNotEnough(BankError):
    message = "银行墨辉币余额不足。"


class InvalidBankOperation(BankError):
    message = "未知的银行操作类型。"


class InvalidTransferAmount(BankError):
    message = "转账金额必须大于0。"


class InvalidTransferTarget(BankError):
    message = "转账对象无效，无法完成转账。"


__all__ = [
    "BankError",
    "BankBalanceNotEnough",
    "InvalidBankOperation",
    "InvalidTransferAmount",
    "InvalidTransferTarget",
]
