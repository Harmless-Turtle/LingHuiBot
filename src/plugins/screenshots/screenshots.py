import io
from .commands import screenshot_cmd
from .tools import SYSTEM, capture_linux_screen, capture_windows_window
from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image


@screenshot_cmd.handle()
async def handle_screenshot():
    # 需要截取的窗口关键字或 screen 名
    targets = ["napcat", "nonebot"]
    images = []

    for target in targets:
        if SYSTEM == "Windows":
            img = await capture_windows_window(target)
        else:
            img = await capture_linux_screen(target)
        images.append(img)

    # 垂直拼接多张图
    total_width = max(i.width for i in images)
    total_height = sum(i.height for i in images)
    combined = Image.new("RGB", (total_width, total_height), (40, 40, 40))

    y = 0
    for img in images:
        combined.paste(img, (0, y))
        y += img.height

    # 输出到字节流
    output = io.BytesIO()
    combined.save(output, format='PNG')
    await screenshot_cmd.finish(MessageSegment.image(output.getvalue()))