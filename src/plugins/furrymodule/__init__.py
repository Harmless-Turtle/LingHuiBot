from .furryfusion.furryfusion import (
    furryfusion_list,
    furryfusion_check,
    furryfusion_countdown,
    furryfusion_quick_information,
    furryfusion_information
)
from .furrybar import (
    furrybar,
    change_config,
    reset_furrybar,
    clear,
    latest
)
from .furry import (
    furry_random,
    furry_picture,
    furry_list,
    furry_status,
    service_status,
    check_upload,
    check_upload_decide,
    upload_clear
)

from .upload import (
    upload_furry,
    batch_upload,
    batch_set,
    debugger_upload,
    modify_furry,
)

# 导出处理器以便NoneBot自动加载
__all__ = [
    furryfusion_list,
    furryfusion_check,
    furryfusion_countdown,
    furryfusion_quick_information,
    furryfusion_information,
    furrybar,
    change_config,
    reset_furrybar,
    clear,
    latest,
    furry_random,
    furry_picture,
    upload_furry,
    batch_upload,
    batch_set,
    debugger_upload,
    furry_list,
    modify_furry,
    furry_status,
    service_status,
    check_upload,
    check_upload_decide,
    upload_clear
]




