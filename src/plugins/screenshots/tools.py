import os
import platform
import subprocess
import asyncio
import re
import io
from PIL import Image, ImageDraw, ImageFont

SYSTEM = platform.system()

# Windows 特定支持
if SYSTEM == "Windows":
    import win32gui
    import win32ui
    import win32con
    import win32com.client
    from ctypes import windll, byref, sizeof
    from ctypes import wintypes

# --- 基础配置 ---
# Linux 下日志存放绝对路径 (请根据实际情况修改)
LINUX_LOG_DIR = "/home/LingHui/NoneBot/LingHuiBot/data/screenlogs"
if SYSTEM != "Windows" and not os.path.exists(LINUX_LOG_DIR):
    os.makedirs(LINUX_LOG_DIR)


def text_to_image(text: str, title: str = "") -> Image.Image:
    """将终端文本渲染为图片 (针对 Linux 或错误提示)"""
    lines = text.splitlines()
    if not lines: lines = ["(No Output)"]

    font_size = 16
    line_height = font_size + 4
    img_w = 900
    img_h = max(len(lines) * line_height + 40, 150)

    # 终端配色：背景深灰，文字浅灰
    image = Image.new("RGB", (img_w, img_h), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)

    # 尝试加载 Linux 常见等宽字体
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # 绘制标题头
    draw.rectangle([0, 0, img_w, 25], fill=(50, 50, 50))
    draw.text((10, 5), f"> Terminal: {title}", fill=(200, 200, 200))

    y = 35
    for line in lines:
        clean_line = "".join(c for c in line if c.isprintable() or c == '\t')
        draw.text((10, y), clean_line, fill=(240, 240, 240), font=font)
        y += line_height
    return image


async def capture_linux_screen(keyword: str) -> Image.Image:
    """Linux: 通过 screen -X hardcopy 获取内容"""
    txt_path = os.path.join(LINUX_LOG_DIR, f"{keyword}.txt")
    if os.path.exists(txt_path): os.remove(txt_path)

    # 完整的 screen 命令
    cmd = ["screen", "-S", keyword, "-p", "0", "-X", "hardcopy", txt_path]
    subprocess.run(cmd)

    await asyncio.sleep(0.5)  # 等待 IO 写入

    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return text_to_image(content, title=keyword)
    return text_to_image(f"Error: 无法获取 {keyword} 会话内容，请确认 screen 正在运行。", title=keyword)


async def capture_windows_window(keyword: str) -> Image.Image:
    """Windows: 使用 Win32 API 强行置顶并截取窗口内容"""
    try:
        hwnds = []
        win32gui.EnumWindows(lambda h, l: l.append(h) if keyword.lower() in win32gui.GetWindowText(h).lower() else None,
                             hwnds)
        if not hwnds: return text_to_image(f"Window '{keyword}' not found.")

        hwnd = hwnds[0]
        # 强行激活并置顶窗口
        if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(hwnd)
        await asyncio.sleep(0.3)

        # 获取精准坐标 (排除阴影)
        rect = wintypes.RECT()
        windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, byref(rect), sizeof(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top

        # 截图逻辑
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        # PrintWindow 参数 3 代表抓取整个窗口包括非客户区
        windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        return img
    except Exception as e:
        return text_to_image(f"Windows Error: {str(e)}")