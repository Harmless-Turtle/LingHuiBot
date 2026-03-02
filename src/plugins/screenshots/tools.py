import os
import platform
import subprocess
import asyncio
from PIL import Image, ImageDraw

SYSTEM = platform.system()

if SYSTEM == "Windows":
    import win32gui
    import win32ui
    import win32con
    import win32com.client
    from ctypes import windll


def text_to_image(text: str) -> Image.Image:
    """文字转图片逻辑保持不变"""
    font_size = 16
    lines = text.splitlines()
    img_w = 800
    img_h = max(len(lines) * (font_size + 4), 100)
    image = Image.new("RGB", (img_w, img_h), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)
    y_text = 10
    for line in lines:
        draw.text((10, y_text), line, fill=(240, 240, 240))
        y_text += font_size + 4
    return image


async def capture_linux_screen(session_name: str) -> Image.Image:
    """Linux Screen 逻辑保持不变"""
    temp_file = f"screen_dump_{session_name}.txt"
    subprocess.run(["screen", "-S", session_name, "-X", "hardcopy", temp_file])
    if os.path.exists(temp_file):
        with open(temp_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        os.remove(temp_file)
        return text_to_image(content)
    return text_to_image(f"Error: Session {session_name} not found.")


async def capture_windows_window(window_title_keyword: str) -> Image.Image:
    """使用 Win32 API 捕获特定窗口内容"""
    try:
        hwnd = win32gui.FindWindow(None, None)  # 占位

        # 遍历查找包含关键字的窗口
        def callback(h, extra):
            if window_title_keyword.lower() in win32gui.GetWindowText(h).lower():
                extra.append(h)

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)

        if not hwnds:
            return text_to_image(f"Window '{window_title_keyword}' not found.")

        hwnd = hwnds[0]

        # 1. 强制调出并显示窗口
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # 关键：解决普通 SetForegroundWindow 的权限限制
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')  # 发送一个 Alt 键释放焦点锁定
        win32gui.SetForegroundWindow(hwnd)

        # 给 Windows 一点渲染时间，防止截出黑色或旧内容
        await asyncio.sleep(0.5)

        # 2. 获取真正的窗口坐标（处理 DPI 缩放）
        # 使用 DwmGetWindowAttribute 获取排除阴影后的真实矩形
        import ctypes
        from ctypes import wintypes
        rect = wintypes.RECT()
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
        )

        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        w = right - left
        h = bottom - top

        # 3. 截取窗口
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        # 使用 PrintWindow API 抓取窗口内容
        # 0 表示抓取整个窗口，2 表示只抓取客户区
        windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )

        # 清理资源
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        return img
    except Exception as e:
        return text_to_image(f"Win32 Error: {str(e)}")