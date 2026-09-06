from ..Exceptions import ModuleError


class SensitiveError(ModuleError):
    module = "sensitive_manager"
    message = "敏感词功能发生异常，请稍后再试。"


class SensitivePermissionDenied(SensitiveError):
    message = "权限不足，只有敏感词管理员可以执行此操作"


class SensitiveWordExists(SensitiveError):
    message = "该敏感词已存在"


class SensitiveWordNotFound(SensitiveError):
    message = "该敏感词不存在"


class SensitiveGroupNotConfigured(SensitiveError):
    message = "该群组未设置敏感词"


__all__ = [
    "SensitiveError",
    "SensitivePermissionDenied",
    "SensitiveWordExists",
    "SensitiveWordNotFound",
    "SensitiveGroupNotConfigured",
]
