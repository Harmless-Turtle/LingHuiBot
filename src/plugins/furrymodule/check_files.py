from pathlib import Path

from ..utils import ensure_files_exist

BASE_DIR = Path.cwd()
FURRY_DATA_DIR = BASE_DIR / "data" / "furry_system"

# AI 相关数据路径
AI_USER_DATA_DIR = FURRY_DATA_DIR / "furrybar"

# 兽聚展会相关数据路径
CON_SESSION_FILE = FURRY_DATA_DIR / "furryfusion" / "login_session.json"
CON_TIMELINE_CACHE_FILE = FURRY_DATA_DIR / "furryfusion" / "furryfusion_timeline.png"

# 鉴毛与毛照图库相关数据路径
SUIT_UPLOAD_DIR = FURRY_DATA_DIR / "upload"
SUIT_UPLOAD_JSON = SUIT_UPLOAD_DIR / "upload_data.json"
SUIT_BATCH_DIR = SUIT_UPLOAD_DIR / "batch"
SUIT_PROCESSED_DIR = FURRY_DATA_DIR / "processed_images"
SUIT_PICTURE_DATA_DIR = FURRY_DATA_DIR / "furrypic_data"

# 兼容过渡别名
forward_path = AI_USER_DATA_DIR
furryfusion_login_session = CON_SESSION_FILE
furry_pic_data_path = SUIT_PICTURE_DATA_DIR
DATA_PATH = SUIT_UPLOAD_DIR
json_path = SUIT_UPLOAD_JSON
batch_path = SUIT_BATCH_DIR
allin_pic_prerequisite_path = SUIT_PROCESSED_DIR
OPENDATA = BASE_DIR

# 校验文件与目录结构
ensure_files_exist(
    file_path=[
        SUIT_UPLOAD_DIR,
        SUIT_UPLOAD_JSON,
        SUIT_BATCH_DIR,
        SUIT_PROCESSED_DIR,
        AI_USER_DATA_DIR,
        SUIT_PICTURE_DATA_DIR,
        CON_SESSION_FILE,
    ],
    description="furrymodule 模块自检",
    normal_data=[None, [], None, None, None, None, {}],
)
