from pathlib import Path

from ..utils import ensure_files_exist

OPENDATA = Path.cwd()
DATA_PATH = OPENDATA / "data" / "furry_system" / "upload"
FONT_PATH = OPENDATA / "data" / "MiSans-Demibold.ttf"
json_path = DATA_PATH / "upload_data.json"
batch_path = DATA_PATH / "batch"
temp_image_path = OPENDATA / 'data' / 'furry_system' / 'temp.jpg'
allin_pic_prerequisite_path = OPENDATA / 'data' / 'furry_system' / 'processed_images'
forward_path = OPENDATA / "data" / "furry_system" / "furrybar"

# 校验文件
ensure_files_exist(
    file_path=[
        DATA_PATH,
        FONT_PATH,
        json_path,
        batch_path,
        temp_image_path,
        allin_pic_prerequisite_path,
        forward_path
    ],
    description="furrymodule模块 自检",
    normal_data=[None, None, [], None, None, None, None]
)
