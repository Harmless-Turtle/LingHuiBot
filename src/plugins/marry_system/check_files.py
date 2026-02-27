from pathlib import Path

from ..utils import ensure_files_exist

# 定义Data存放路径并作为全局变量使用
marry_json_path = Path.cwd() / "data" / "marry_system" / 'marry_data.json'

ensure_files_exist(
    [
        marry_json_path,
    ],
    "结婚系统自检",
    [{}]
)
