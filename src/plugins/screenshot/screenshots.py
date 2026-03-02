import platform
import base64

from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent
from nonebot import logger
from nonebot.exception import FinishedException

from .commands import *
from .tools import *


@screenshot_cmd.handle()
async def handle_screenshot(event: MessageEvent):
    system = platform.system()
    # 建议保存到 data 目录下，避免权限问题
    temp_img = Path("data/cache_console.png").absolute()

    logger.info(f"收到截屏请求，系统: {system}")

    try:
        success = False
        if system == "Windows":
            success = capture_windows(temp_img, TARGET_KEYWORDS)
        elif system == "Linux":
            success = capture_linux_screen(temp_img, TARGET_KEYWORDS)

        if success and temp_img.exists() and temp_img.stat().st_size > 0:
            with open(temp_img, "rb") as f:
                img_data = f.read()
                base64_str = base64.b64encode(img_data).decode()

            # 发送图片
            await screenshot_cmd.send(
                MessageSegment.reply(event.message_id) +
                MessageSegment.image(f"base64://{base64_str}")
            )
            logger.info("截屏发送成功")
        else:
            await screenshot_cmd.send("截屏失败：未能抓取到内容，请检查进程名是否匹配。")

    except FinishedException:
        raise  # NoneBot 内部正常结束异常，必须抛出
    except Exception as e:
        logger.exception("截屏插件运行崩溃")
        await screenshot_cmd.send(f"运行出错: {type(e).__name__}")
    finally:
        # 无论成功失败，尝试清理缓存
        if temp_img.exists():
            temp_img.unlink(missing_ok=True)