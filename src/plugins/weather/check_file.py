from pathlib import Path

from src.plugins import utils

# data路径作为全局变量使用
path_header = Path.cwd() / "data"


# 定义路径变量
typhoon_id_path = path_header / "weather" / "typhoon_id.json"
utils.ensure_files_exist(
    [
        typhoon_id_path,
    ],
    "台风ID缓存",
    [{}]
)