from pathlib import Path
from src.plugins import utils

# data路径作为全局变量使用
path_header = Path.cwd() / "data"


########################
#      结婚系统自检      #
########################
# 定义路径变量
marry_json_path = path_header / "entertainment"/ "marry_system" / 'marry.json'
utils.ensure_files_exist(
    [
        marry_json_path,
    ],
    "结婚系统自检",
    [{}]
)


########################
#      漂流瓶自检        #
########################
# 定义路径变量
bottle_path = path_header / "entertainment"/ "drify_bottle" / 'bottle.json'
utils.ensure_files_exist(
    [
        bottle_path,
    ],
    "漂流瓶文件自检",
    [{}]
)