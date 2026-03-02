import io
from .commands import screenshot_cmd
from .tools import SYSTEM, capture_linux_screen, capture_windows_window
from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image


@screenshot_cmd.handle()
async def handle_screenshot():
    # 注意：这里的关键字要匹配你 CMD 窗口标题栏显示的文字
    # 比如你的 Napcat 窗口标题可能是 "NapCat.Shell"
    targets = ["napcat", "nonebot"]
    images = []

    for target in targets:
        if SYSTEM == "Windows":
            img = await capture_windows_window(target)
        else:
            img = await capture_linux_screen(target)
        images.append(img)

    # 垂直拼接
    total_width = max(i.width for i in images)
    total_height = sum(i.height for i in images)
    combined_img = Image.new("RGB", (total_width, total_height), (50, 50, 50))

    y_offset = 0
    for img in images:
        combined_img.paste(img, (0, y_offset))
        y_offset += img.height

    img_byteArr = io.BytesIO()
    combined_img.save(img_byteArr, format='PNG')

    await screenshot_cmd.finish(MessageSegment.image(img_byteArr.getvalue()))