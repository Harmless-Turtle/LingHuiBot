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
bottle_path = path_header / "entertainment"/ "drift_bottle" / 'bottle.json'
auto_path = path_header / "entertainment"/ "drift_bottle" / "auto_switch.json"
utils.ensure_files_exist(
    [
        bottle_path,
        auto_path
    ],
    "漂流瓶文件自检",
    [{},{}]
)

wolf_kill_path = Path.cwd() / "data" / "entertainment" / "wolfkill"
utils.ensure_files_exist(
    [
        wolf_kill_path,
    ],
    "狼人杀文件自检",
    [{}]
)

guess_number_path = Path.cwd() / "data" / "entertainment" / "guess_number" / "guess_number.json"
utils.ensure_files_exist(
    [
        guess_number_path,
    ],
    "猜数字文件自检",
    [{}]
)