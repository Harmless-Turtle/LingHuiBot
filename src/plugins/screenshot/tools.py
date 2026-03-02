import subprocess
import os
import win32gui
import win32ui
import win32con
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import ctypes

# 配置需要监控的关键字（窗口名或 screen 名）
TARGET_KEYWORDS = ["napcat", "nonebot"]

try:
    import pygetwindow as gw
except ImportError:
    gw = None

def render_text_to_image(text: str, save_path: str):
    """将控制台文本渲染为黑底绿字的图片"""
    font_size = 14
    # 尝试加载等宽字体
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)
    except:
        font = ImageFont.load_default()

    lines = text.splitlines()
    # 自动计算高度
    width = 900
    height = len(lines) * (font_size + 4) + 40

    img = Image.new("RGB", (width, height), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        draw.text((20, 20 + i * (font_size + 4)), line, fill=(50, 255, 50), font=font)

    img.save(save_path)


# 预定义 ctypes 调用
user32 = ctypes.windll.user32

# --- 新增：处理 DPI 缩放 ---
try:
    # 告诉 Windows 这是一个 DPI 感知的应用，避免坐标偏移
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 1 = Process_System_DPI_Aware
except Exception:
    # 兼容老版本 Windows
    ctypes.windll.user32.SetProcessDPIAware()

user32 = ctypes.windll.user32


def capture_windows(save_path: Path, keywords: list) -> bool:
    target_hwnd = None

    def callback(hwnd, extra):
        nonlocal target_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if any(k.lower() in title.lower() for k in keywords):
                target_hwnd = hwnd

    win32gui.EnumWindows(callback, None)
    if not target_hwnd: return False

    try:
        if win32gui.IsIconic(target_hwnd):
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)

        # 这里的坐标现在是真实的物理像素坐标了
        left, top, right, bottom = win32gui.GetWindowRect(target_hwnd)
        width, height = right - left, bottom - top

        # 某些窗口（如 Windows Terminal）会有透明边框，导致截图带黑边
        # 如果需要剔除边框，可以稍微缩小 width 和 height，并偏移 left/top
        # width -= 10; height -= 10; left += 5; top += 5

        hwnd_dc = win32gui.GetWindowDC(target_hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        # 使用 PW_RENDERFULLCONTENT (2) 强制渲染内容
        result = user32.PrintWindow(target_hwnd, save_dc.GetSafeHdc(), 2)

        if result == 1:
            bmpinfo = save_bitmap.GetInfo()
            bmpstr = save_bitmap.GetBitmapBits(True)
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            # 如果截出来的图颜色反了，可以在这里转换
            # img = img.convert("RGB")
            img.save(save_path)

        # 释放资源
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(target_hwnd, hwnd_dc)
        return result == 1
    except Exception as e:
        print(f"截图出错: {e}")
        return False

def capture_linux_screen(save_path: Path, screen_names: list) -> bool:
    """Linux screen 进程文本抓取实现"""
    try:
        combined_text = ""
        for name in screen_names:
            dump_file = f"/tmp/screen_{name}.txt"
            # 发送指令让 screen 把当前窗口存入文件
            subprocess.run(["screen", "-S", name, "-X", "hardcopy", dump_file])

            if os.path.exists(dump_file):
                with open(dump_file, "r", encoding="utf-8") as f:
                    combined_text += f"\n[Session: {name}]\n" + "=" * 20 + "\n" + f.read()
                os.remove(dump_file)

        if not combined_text: return False
        render_text_to_image(combined_text, str(save_path))
        return True
    except Exception:
        return False