from pathlib import Path

from ..utils import ensure_files_exist

OPENDATA = Path.cwd()
DATA_PATH = OPENDATA / "data" / "furry_system" / "upload"
json_path = DATA_PATH / "upload_data.json"
batch_path = DATA_PATH / "batch"
temp_image_path = OPENDATA / 'data' / 'furry_system' / 'temp.jpg'
allin_pic_prerequisite_path = OPENDATA / 'data' / 'furry_system' / 'processed_images'
forward_path = OPENDATA / "data" / "furry_system" / "furrybar"
furry_pic_data_path = OPENDATA / "data" / "furry_system" / "furrypic_data"
furryfusion_login_session = OPENDATA / "data" / "furry_system" / "furryfusion" / "login_session.json"

# 校验文件
# 注意：字体文件（data/SarasaFixedSlabJ-SemiBoldItalic.ttf）刻意不放进自检列表。
# 它不是“缺了就能自动生成”的配置：ensure_files_exist 会 touch 出 0 字节占位，
# 而空字体比没有字体更难排查（truetype 打开会抛 OSError）。字体缺失时由
# utils.FONT_PATH 判定为 None，各调用点回退默认字体即可。
ensure_files_exist(
    file_path=[
        DATA_PATH,
        json_path,
        batch_path,
        temp_image_path,
        allin_pic_prerequisite_path,
        forward_path,
        furry_pic_data_path,
        furryfusion_login_session
    ],
    description="furrymodule模块 自检",
    normal_data=[None, [], None, None, None, None, None, {}]
)
