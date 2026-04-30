from pathlib import Path

from src.plugins import utils

# data路径作为全局变量使用
path_header = Path.cwd() / "data"

########################
#      结婚系统自检      #
########################
# 定义路径变量
marry_json_path = path_header / "entertainment" / "marry_system" / 'marry.json'
utils.ensure_files_exist(
    [
        marry_json_path,
    ],
    "结婚系统自检",
    [{}]
)

########################
#      制作表情包自检        #
########################
memes_make_path = Path.cwd() / "data" / "entertainment" / "make_memes" / "resources"
utils.ensure_files_exist(
    [
        memes_make_path,
    ],
    "表情包制作路径自检",
    [None]
)

########################
#      漂流瓶自检        #
########################
# 定义路径变量
bottle_path = path_header / "entertainment" / "drift_bottle" / 'bottle.json'
auto_path = path_header / "entertainment" / "drift_bottle" / "auto_switch.json"
utils.ensure_files_exist(
    [
        bottle_path,
        auto_path
    ],
    "漂流瓶文件自检",
    [{}, {}]
)

########################
#      漂流瓶自检        #
########################
wolf_kill_path = Path.cwd() / "data" / "entertainment" / "wolfkill"
utils.ensure_files_exist(
    [
        wolf_kill_path,
    ],
    "狼人杀文件自检",
    [{}]
)

########################
#      抢劫功能自检        #
########################
bank_robbery_time_path = path_header / "entertainment" / "bank" / "bank_robbery.json"
robbery_time_path = path_header / "entertainment" / "bank" / "robbery_time.json"
utils.ensure_files_exist(
    [
        bank_robbery_time_path,
        robbery_time_path
    ],
    "抢银行计时器文件自检",
    [{}, {}]
)
