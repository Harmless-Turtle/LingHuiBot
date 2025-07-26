# 导入所需要的第三方库
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    Message
)
from functools import wraps
from nonebot.exception import MatcherException
import time, traceback, os, json, httpx, httpcore
from nonebot import logger
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

FONT_PATH = Path() / 'data' / 'MiSans-Demibold.ttf'
FURRYFUSION_BG_PATH = Path() / 'data' / 'Furry_System' / 'bg.png'
ERROR_DIR = Path() / "logs"


# 定义处理函数
class Handler:
    """
    处理函数类，包含异常处理、图片合成、JSON 加载和批量转发内容构建等功能。
    """

    # 捕获并处理函数执行中的异常，生成错误日志并构造用户友好的反馈
    @staticmethod
    def handle_errors(func):
        """
        装饰一个函数以捕获异常（除了 MatcherException），提供统一的错误处理逻辑。
            - 记录详细的错误日志到文件
            - 提供用户友好的错误提示

        Args:
            func: 被装饰的异步函数，通常是一个事件处理函数。

        Raises:
            MatcherException: 这类异常会被直接抛出，不会被捕获处理。
        """

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except MatcherException:
                raise
            except Exception as error:
                # 追踪并格式化错误日志
                error_msg = (
                    f"脚本：{__file__}\n"
                    f"在“{time.strftime('%Y-%m-%d %a %H:%M:%S', time.localtime())}”时返回了异常错误。内容如下：\n\n"
                    f"{traceback.format_exc()}\n"
                    "---------------------异常错误截止---------------------\n\n"
                )

                # 追加到工作目录的 ERROR_DIR/error.log
                with open(ERROR_DIR / "error.log", 'a', encoding='utf-8') as filestream:
                    filestream.write(error_msg)
                logger.error(error_msg)

                # 按时间戳生成并保存报错图片到 logs/error_****.png
                try:
                    font = ImageFont.truetype(FONT_PATH, size=30)
                except OSError:
                    font = ImageFont.load_default()
                text_lines = [line for line in error_msg.split('\n') if line.strip() != '']
                error_image = Handler.generate_text_image(text_lines, font)
                timestamp = time.strftime("%Y%m%d%H%M%S")
                error_image.save(ERROR_DIR / f"error_{timestamp}.png", format="PNG")

                # 从参数中查找 matcher 和 event 用于构建用户回复
                matcher = next((arg for arg in args if isinstance(arg, Matcher)), kwargs.get("matcher"))
                event = next((arg for arg in args if isinstance(arg, MessageEvent)), kwargs.get("event"))

                # 生成错误响应并发送给用户
                error_response = Handler.create_error_reply(error, event, error_image)
                await matcher.finish(error_response)

        return wrapper

    # 根据异常类型生成对应的错误回复消息
    @staticmethod
    def create_error_reply(error: Exception, event, error_image) -> Optional[Message]:
        """
        根据异常类型生成用户友好的错误响应消息。

        Args:
            error: 捕获的异常对象
            error_image: 错误图片路径，用于回复用户
            event: 事件对象，用于构建回复引用

        Returns:
            构建的错误响应消息，如果无法构建则返回None
        """
        # 获取消息 ID 上下文
        reply_part = (MessageSegment.reply(event.message_id))

        # 根据异常类型构建不同的响应消息
        if isinstance(error, httpx.ReadTimeout):
            return reply_part + "请求超时了呢qwq...可能是网络波动，请稍后再试哦～"
        if isinstance(error, httpcore.RemoteProtocolError):
            return reply_part + "服务器断开了连接且未发送任何数据给凌辉qwq...请稍后再试"

        # 默认错误消息
        return (reply_part + "没有正确处理请求呢qwq...请联系管理员[1097740481]协助解决哦"
                + MessageSegment.image(error_image))

    # 根据多行文本和字体生成一张自动排版的图片
    @staticmethod
    def generate_text_image(lines, font):
        padding = 20  # 增加边距
        line_height = 0
        max_width = 0

        # 预先计算所有文本的尺寸
        for line in lines:
            # 使用 get bbox 获取文本边界框
            bbox = font.getbbox(line)
            # 计算实际宽度和高度
            line_width = bbox[2] - bbox[0]
            line_height = max(line_height, bbox[3] - bbox[1])
            max_width = max(max_width, line_width)

        # 添加边距
        total_width = int(max_width) + 2 * padding
        total_height = len(lines) * (line_height + 5) + 2 * padding

        # 创建画布
        image = Image.new("RGB", (total_width, total_height), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        # 绘制文字 - 居左显示
        y = padding
        for line in lines:
            # 获取文本尺寸
            bbox = font.getbbox(line)
            text_height = bbox[3] - bbox[1]

            # 居左显示 - 固定从左侧padding位置开始
            x = padding

            # 绘制文本
            draw.text((x, y), line, fill=(0, 0, 0), font=font)
            y += line_height + 5  # 行间距

        return image

    # json加载函数
    @staticmethod
    def load_json(json_path: Path, mode: str, data: Optional[dict] = None) -> dict:
        """
        根据用户提供的路径操作json文件
        Args:
            json_path (Path): JSON 文件的路径。
            mode (str): 操作模式，'r'表示读取，其他值表示写入。
            data (Optional[dict]): 要写入 JSON 文件的数据，仅在 mode 不是 'r' 时使用。
        Raises:
            ValueError: 如果 mode 不是 'r' 且 data 为 None。
        Returns:
            dict: 读取的 JSON 数据，仅在 mode 为 'r' 时返回。
        """
        with open(json_path, mode, encoding='utf-8') as f:
            if mode == 'r':
                return json.load(f)
            if mode != 'r' and data == None:
                logger.error("未找到应写入的data！")
            json.dump(data, f, ensure_ascii=False, indent=4)
            return None

    # 批量转发内容构建函数
    async def Batch_Get(Text: str, Picture: Optional[str], QQ: int, Name: str) -> MessageSegment:
        if Picture != None:
            Make_Information = MessageSegment.text(Text) + MessageSegment.image(Picture)
        else:
            Make_Information = MessageSegment.text(Text)
        make_text = MessageSegment.node_custom(
            user_id=QQ,
            nickname=f"{Name}",
            content=Message(Make_Information))
        return make_text

    def time_handle(time):
        """
        根据用户提供的时间戳，计算与当前时间的时间差，并以“年月日时分秒”的格式返回。
        Args:
            time (int): 用户提供的 Unix 时间戳（秒级）。
        Returns:
            str: 时间差的字符串表示，例如“1年2个月3天4小时5分钟6秒”。
        """
        # 将时间戳转换为 datetime 对象
        time_obj = datetime.fromtimestamp(time)
        now_time = datetime.now()

        # 计算年份差
        years = now_time.year - time_obj.year
        if (now_time.month, now_time.day) < (time_obj.month, time_obj.day):
            years -= 1

        # 调整时间（处理闰年）
        try:
            adjusted_time = time_obj.replace(year=time_obj.year + years)
        except ValueError:
            # 处理闰年 2 月 29 日的情况
            adjusted_time = time_obj.replace(year=time_obj.year + years, day=28)

        # 计算月份差
        months = 0
        current = adjusted_time
        while True:
            # 计算下个月的同一天
            if current.month == 12:
                next_month = 1
                next_year = current.year + 1
            else:
                next_month = current.month + 1
                next_year = current.year

            try:
                next_date = current.replace(year=next_year, month=next_month)
            except ValueError:
                # 处理无效日期（如 2 月 30 日），调整为月末最后一天
                next_date = (
                                    current.replace(day=1, month=next_month, year=next_year) +
                                    timedelta(days=32)
                            ).replace(day=1) - timedelta(days=1)

            if next_date > now_time:
                break
            months += 1
            current = next_date

        # 计算剩余时间差
        delta = now_time - current
        days = delta.days
        seconds = delta.seconds
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)

        # 构建时间差字符串
        time_components = [
            (years, '年'),
            (months, '月'),
            (days, '天'),
            (hours, '小时'),
            (minutes, '分'),
            (seconds, '秒')
        ]

        time_text = ''.join(
            f'{value}{unit}'
            for value, unit in time_components
            if value != 0
        ).strip() or '0秒'  # 处理全零情况

        return time_text

    async def furryfusion_picture_handle(picture: str, name: str, text: str) -> str:
        # --------
        response = httpx.get(picture)
        if response.status_code != 200:
            raise Exception(f"图片下载失败，状态码: {response.status_code}")
        img = Image.open(BytesIO(response.content))
        overlay_image = Image.open(FURRYFUSION_BG_PATH).convert("RGBA")
        _, _, _, alpha = overlay_image.split()
        target_size = (1920, 1080)  # 设置目标尺寸
        img_resized = img.resize(target_size, Image.LANCZOS)
        img_resized.paste(
            overlay_image,
            (0, 0),
            alpha
        )
        output_dir = Path.cwd() / 'data' / 'Furry_System' / "processed_images"
        os.makedirs(output_dir, exist_ok=True)

        draw = ImageDraw.Draw(img_resized)
        Font_Path = Path.cwd() / 'data' / 'SourceHanSansSC-VF.ttf'
        font = ImageFont.truetype(Font_Path, size=95)

        text_color = (255, 255, 255)
        draw.text((10, 50), text, font=font, fill=text_color)

        # 生成唯一文件名
        unique_filename = f"image_{name}.png"
        output_path = os.path.join(output_dir, unique_filename)
        img_resized.save(output_path, format="PNG")
        return os.path.abspath(output_path)
        # --------
