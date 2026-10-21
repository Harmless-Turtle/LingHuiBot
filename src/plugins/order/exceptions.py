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
    message = "下载饮品图片失败，请稍后重试。"


class OrderImageSaveError(OrderError):
    message = "保存饮品图片或数据失败，请稍后重试。"


__all__ = [
    "OrderError",
    "OrderMenuEmptyError",
    "OrderItemNotFoundError",
    "OrderImageDownloadError",
    "OrderImageSaveError",
]
