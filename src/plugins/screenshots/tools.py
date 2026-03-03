import os
import platform
import subprocess
import asyncio
import textwrap
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
    """
    改进版：支持自动换行，动态计算高度
    """
    # 基础配置
    font_size = 16
    line_spacing = 4
    char_width_limit = 95  # 每行最多容纳的字符数（根据 900px 宽度估算）
    padding = 20
    header_height = 35

    # 1. 自动换行处理
    # 将原始文本按行拆分，对每一行进行 wrap，防止超出右侧
    wrapped_lines = []
    raw_lines = text.splitlines()
    if not raw_lines:
        raw_lines = ["(No Output / Session Empty)"]

    for line in raw_lines:
        # 去除非打印字符
        clean_line = "".join(c for c in line if c.isprintable() or c == '\t').replace('\t', '    ')
        if clean_line.strip() == "":
            wrapped_lines.append("")
            continue
        # 使用 textwrap 将长行切分成多行
        wrapped_lines.extend(textwrap.wrap(clean_line, width=char_width_limit))

    # 2. 动态计算高度
    # 图片总高度 = 标题头 + (行数 * (行高 + 间距)) + 上下边距
    line_total_height = font_size + line_spacing
    content_height = len(wrapped_lines) * line_total_height
    img_w = 900
    img_h = header_height + content_height + (padding * 2)

    # 限制最大高度，防止图片过大导致发送失败（QQ限制）
    img_h = min(img_h, 5000)

    # 3. 绘图
    image = Image.new("RGB", (img_w, img_h), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)

    # 尝试加载等宽字体 (等宽字体对对齐至关重要)
    try:
        # Linux 路径示例
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # 绘制装饰性标题栏
    draw.rectangle([0, 0, img_w, 30], fill=(55, 55, 55))
    draw.text((15, 7), f"CONSOLE OUT: {title}", fill=(0, 255, 0), font=font)

    # 4. 逐行绘制
    y = header_height + 5
    for line in wrapped_lines:
        if y > img_h - padding:  # 超过最大高度停止绘制
            draw.text((15, y), "... (Output Truncated) ...", fill=(150, 150, 150), font=font)
            break
        draw.text((15, y), line, fill=(240, 240, 240), font=font)
        y += line_total_height

    return image


async def capture_linux_screen(keyword: str) -> Image.Image:
    """
    改进版 Linux 捕获：先尝试扩大虚拟终端宽度，再截取
    """
    txt_path = os.path.join(LINUX_LOG_DIR, f"{keyword}.txt")
    if os.path.exists(txt_path): os.remove(txt_path)

    # 技巧：在 hardcopy 前尝试发送指令让 screen 调整宽度 (可选)
    # subprocess.run(["screen", "-S", keyword, "-X", "width", "120"])

    cmd = ["screen", "-S", keyword, "-p", "0", "-X", "hardcopy", txt_path]
    subprocess.run(cmd)

    await asyncio.sleep(0.4)

    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return text_to_image(content, title=keyword)

    return text_to_image(f"Error: 无法找到 Session {keyword} 的输出文件。", title=keyword)


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