from pathlib import Path
from src.plugins import utils

# 定义Data存放路径并作为全局变量使用
path_header = Path.cwd() / "data" / "marry_system"
# 定义全局变量方便处理
marry_json_path = path_header / 'marry.json'
marry_count_path = path_header / 'marry_count.json'


utils.ensure_files_exist(
    [
        marry_json_path,
        marry_count_path,
    ],
    "结婚系统自检",
    [{},{}]
)