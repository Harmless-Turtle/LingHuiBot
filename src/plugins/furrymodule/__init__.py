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
    furryrandom,
    furrypicture,
    furrylist,
    furry_status,
    service_status,
    check_upload,
    check_upload_decide,
    upload_clear
)

from .upload import (
    UploadFurry,
    Batch_Upload,
    Batch_Set,
    Debugger_Upload,
    Modify_Furry,
)

__plugin_name__ = "Furry Module福瑞模块插件"
__plugin_usage__ = """
FurryPic功能：
来只兽兽/来只毛/来只<兽兽名字/设定名>/来只兽       -随机兽图，或者指定兽兽名字/设定名字的随机一张图片
指定/指定#      -指定获取在云平台中id的图片
上传#名字#类型#留言#图片     -通过凌辉bot将图片上传到云平台（需经由凌辉bot管理员以及云平台管理员审核，严禁上传R18/R18G）
批量投图/批量上传       -一次性上传多张图片    ⚠未经验证的功能！
定义/定义#<数字id>      -定义批量上传的图片详细信息。      ⚠未经验证的功能！
查列表/查列表#/查兽兽     -查找对应名字的兽兽在云平台中的全部图片id及信息。
修改图片#id#名字/留言/类型>#修改类型/图片      -修改通过凌辉bot上传的图片的详细信息，需经由凌辉bot管理员以及云平台管理员审核。
兽图状态<数字id>/兽图状态#<数字id>        -查询指定id图片在云平台中的状态。
服务器状态       -验证凌辉bot与云平台通信是否畅通。
------------
FurryFusion功能：
今年兽聚/兽聚列表/兽聚汇总    -查询当前登录在FurryFusion.net中，还未举办或正进行中的兽聚。
兽聚快讯<数字id>    -通过条数快速找到兽聚的信息，条数参考第一条命令。
兽聚倒计时    -获取自查询之日起，所有未举办或正进行中的兽聚。
兽聚查询<地区> -查询地区中的未举办或正进行中的兽聚。
兽聚详情<兽聚名称>/兽聚信息<兽聚名称>   -查询指定兽聚的信息以及其举办过/未举办/正进行中的全部兽聚。
------------
FurryBar功能：
@凌辉bot <输入对话内容> -      -和FurryAI进行对话。
更改用户信息/创建用户信息/定义个人信息 <输入文字>       -让FurryAI认识你：记录个人设定
重置对话/重置模型    -清空聊天记录（不清除个人设定）
删除信息/清空数据    -清空聊天记录（清除个人设定）
上次对话/上次聊天/最后对话/最后记录     -重复与FurryAI的最后一次聊天
"""

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
    furryrandom,
    furrypicture,
    UploadFurry,
    Batch_Upload,
    Batch_Set,
    Debugger_Upload,
    furrylist,
    Modify_Furry,
    furry_status,
    service_status,
    check_upload,
    check_upload_decide,
    upload_clear
]




