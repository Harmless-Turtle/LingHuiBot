from .FurryFusion import (
    FurryFusion_List,
    FurryFusion_Check,
    FurryFusion_countdown,
    FurryFusion_Quick_Information,
    FurryFusion_Information
)
from .FurryBar import (
    FurryBar,
    change_config,
    Reset_FurryBar,
    Clear,
    latest
)
from .Furry import (
    RanFurry,
    PicFurry,
    UploadFurry，
    Batch_Upload,
    Batch_Set,
    Debugger_Upload,
    FurryList,
    Modify_Furry,
    Furry_status,
    Service_Status,
    Check_Upload,
    Check_Upload_Decide,
    Upload_Clear
)

__plugin_name__ = "Furry Module福瑞模块插件"
__plugin_usage__ = """
今年兽聚/兽聚列表/兽聚汇总    -查询当前登录在FurryFusion.net中，还未举办或正进行中的兽聚。
兽聚快讯<数字id>    -通过条数快速找到兽聚的信息，条数参考第一条命令。
兽聚倒计时    -获取自查询之日起，所有未举办或正进行中的兽聚。
兽聚查询<地区> -查询地区中的未举办或正进行中的兽聚。
兽聚详情<兽聚名称>/兽聚信息<兽聚名称>   -查询指定兽聚的信息以及其举办过/未举办/正进行中的全部兽聚。
"""

# 导出处理器以便NoneBot自动加载
__all__ = [
    FurryFusion_List,
    FurryFusion_Check,
    FurryFusion_countdown,
    FurryFusion_Quick_Information,
    FurryFusion_Information,
    FurryBar,
    change_config,
    Reset_FurryBar,
    Clear,
    latest,
    RanFurry,
    PicFurry，
    UploadFurry，
    Batch_Upload,
    Batch_Set,
    Debugger_Upload,
    FurryList,
    Modify_Furry,
    Furry_status,
    Service_Status,
    Check_Upload,
    Check_Upload_Decide,
    Upload_Clear
]

