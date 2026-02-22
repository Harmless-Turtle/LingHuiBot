from pathlib import Path

from ..utils import ensure_files_exist

ALL_MENU_MD = Path() / 'markdown' / 'all_menu.md'
FURRY_MENU_MD = Path() / 'markdown' / 'furry_system.md'
MAIN_MENU_MD = Path() / 'markdown' / 'main_system.md'
SERVICE_MENU_MD = Path() / 'markdown' / 'user_agreement.md'
MARRY_MENU_MD = Path() / 'markdown' / 'marry_system.md'
ADMIN_MENU_MD = Path() / 'markdown' / 'admin_system.md'

ALL_MENU_PIC_DATA = Path() / 'data' / 'Menu' / 'All_Menu.png'
FURRY_MENU_PIC_DATA = Path() / 'data' / 'Menu' / 'Furry_Menu.png'
MAIN_MENU_PIC_DATA = Path() / 'data' / 'Menu' / 'Main_Menu.png'
SERVICE_MENU_PIC_DATA = Path() / 'data' / 'Menu' / 'Service_Menu.png'
MARRY_MENU_PIC_DATA = Path() / 'data' / 'Menu' / 'Marry_Menu.png'
ADMIN_MENU_PIC_DATA = Path() / 'data' / 'Menu' / 'Admin_Menu.png'

ensure_files_exist(
    [
        ALL_MENU_MD,
        FURRY_MENU_MD,
        MAIN_MENU_MD,
        SERVICE_MENU_MD,
        MARRY_MENU_MD,
        ADMIN_MENU_MD,
    ],
    "菜单模块自检",
    [None, None, None, None, None, None]
)
