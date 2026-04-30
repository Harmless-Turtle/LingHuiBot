from pathlib import Path

from ..utils import ensure_files_exist

# 定义Data存放路径并作为全局变量使用
path = Path.cwd() / 'data' / 'main'
poke_path = path / "poke_text.json"
welcome_path = path / "welcome_system.json"
aword_path = path / "aword.json"
sign_in_path = path / "sign_in" / "sign_in.json"
sign_in_pic_true = path / "sign_in" / "Background_True.png"
sign_in_pic_false = path / "sign_in" / "Background_False.jpg"
add_group_check_path = path / "group_admin" / "add_group_switch.json"
check_group_member_path = path / "group_admin" / "GroupMemberChange.json"
friend_like_path = path / "friend_like.json"
group_join_flag_path = path / "group_admin" / "group_join_flags.json"

# 校验文件
ensure_files_exist(
    file_path=[
        poke_path,
        welcome_path,
        aword_path,
        sign_in_path,
        sign_in_pic_true,
        sign_in_pic_false,
        add_group_check_path,
        check_group_member_path,
        friend_like_path,
        group_join_flag_path
    ],
    description="main 模块自检",
    normal_data=[[], {}, [], {}, None, None, {}, {}, {}, {}]
)
