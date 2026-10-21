from typing import Optional

from ..Exceptions import ModuleError


class OrderError(ModuleError):
    message = "点单模块发生异常，请稍后再试。"


class OrderMenuEmptyError(OrderError):
    message = "当前菜单还没有任何饮品哦，请管理员先上传饮品~"


class OrderItemNotFoundError(OrderError):
    def __init__(self, name: str = ""):
        self.message = f"遇到问题：在饮品列表里没有找到{name}"
        super().__init__(self.message)


class OrderImageDownloadError(OrderError):
    def __init__(self, status_code: Optional[int] = None):
        if status_code is not None:
            self.message = f"图片下载失败：[HTTP {status_code}]，请稍后重试~"
        else:
            self.message = "下载饮品图片失败，请稍后重试。"
        super().__init__(self.message)


class OrderImageSaveError(OrderError):
    message = "保存饮品图片或数据失败，请稍后重试。"


__all__ = [
    "OrderError",
    "OrderMenuEmptyError",
    "OrderItemNotFoundError",
    "OrderImageDownloadError",
    "OrderImageSaveError",
]
