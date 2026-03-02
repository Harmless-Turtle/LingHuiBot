import platform
import base64

from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent
from nonebot import logger
from nonebot.exception import FinishedException

from .commands import *
from .tools import *


@screenshot_cmd.handle()
async def handle_screenshot(event:MessageEvent):
    system = platform.system()
    # 确保使用绝对路径
    temp_img = Path("cache_console.png").absolute()

    logger.info(f"正在尝试截屏，保存路径: {temp_img}")

    success = False
    if system == "Windows":
        success = capture_windows(temp_img, TARGET_KEYWORDS)
    elif system == "Linux":
        success = capture_linux_screen(temp_img, TARGET_KEYWORDS)

    if success and temp_img.exists():
        file_size = temp_img.stat().st_size
        logger.info(f"截图成功，文件大小: {file_size} bytes")

        if file_size > 0:
            # --- 核心改进：将图片转为 Base64 发送 ---
            try:
                with open(temp_img, "rb") as f:
                    img_data = f.read()
                    base64_str = base64.b64encode(img_data).decode()

                # 使用 base64 协议头发送
                await screenshot_cmd.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(f"base64://{base64_str}"))
            except FinishedException:
                pass
            except Exception as e:
                logger.error(f"发送图片失败: {e}")
                await screenshot_cmd.finish(f"发送图片出错: {e}")
        else:
            await screenshot_cmd.finish("截屏失败：截取到的图片内容为空。")
    else:
        logger.error("截屏失败，未生成文件或捕获函数返回 False")
        await screenshot_cmd.finish("截屏失败：无法获取窗口，请检查窗口标题是否匹配。")