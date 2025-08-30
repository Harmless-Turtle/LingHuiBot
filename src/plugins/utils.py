import io

from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    Message
)
from functools import wraps
from nonebot.exception import MatcherException
import time, traceback, os, json, httpx, httpcore
from nonebot import logger, get_driver
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

FONT_PATH = Path() / 'data' / 'MiSans-Demibold.ttf'
FURRY_FUSION_BG_PATH = Path() / 'data' / 'Furry_System' / 'bg.png'
ERROR_DIR = Path() / "logs"


# 捕获并处理函数执行中的异常，生成错误日志并构造用户友好的反馈
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
            times = lambda x: time.strftime(x)
            error_msg = (
                f"脚本：{__file__}\n"
                f"在“{times('%Y-%m-%d %a %H:%M:%S')}”时返回了异常错误。内容如下：\n\n"
                f"{traceback.format_exc()}\n"
                "---------------------异常错误截止---------------------\n\n"
            )

            # 追加到工作目录的 ERROR_DIR/error.log
            ERROR_DIR.mkdir(parents=True, exist_ok=True)
            with open(ERROR_DIR / "error.log", 'a', encoding='utf-8') as filestream:
                filestream.write(error_msg)

            # 按时间戳生成并保存报错图片到 logs/error_****.png
            font = ImageFont.truetype(FONT_PATH, size=30) if FONT_PATH.exists() else ImageFont.load_default()
            text_lines = [line for line in error_msg.split('\n') if line.strip() != '']
            error_image = generate_text_image(text_lines, font)
            error_image.save(ERROR_DIR / f"error_{times("%Y%m%d%H%M%S")}.png", format="PNG")

            # 如果事件是消息类型，则回复用户错误图片和消息
            event = next((x for x in args if isinstance(x, MessageEvent)), kwargs.get("event"))
            matcher = next((x for x in args if isinstance(x, Matcher)), kwargs.get("matcher"))

            if isinstance(event, MessageEvent) and matcher:
                buffer_image = io.BytesIO()
                error_image.save(buffer_image, format="PNG")
                buffer_image.seek(0)
                error_response = create_error_reply(error, event, buffer_image)
                await matcher.finish(error_response)
            else:
                logger.warning(
                    f"{__name__}捕获到错误，但由于被装饰的函数没有正确注入 matcher 或 event 实例，无法告知用户")

    return wrapper


# 根据异常类型生成对应的错误回复消息
def create_error_reply(error: Exception, event: MessageEvent, buffer_image: BytesIO) -> Optional[Message]:
    """
    根据异常类型生成用户友好的错误响应消息。

    Args:
        error: 捕获的异常对象
        buffer_image: 传入报错图片，用于回复用户
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
            + MessageSegment.image(buffer_image))


# 根据多行文本和字体生成一张自动排版的图片
# TODO: 需要重构，有乱码问题，格式欠佳
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
def handle_json(json_path: Path, mode: str, data: Optional[dict] = None) -> dict | None:
    """
    根据用户提供的路径操作json文件，仅支持读取和覆盖写入操作。

    Args:
        json_path (Path): JSON 文件的路径。
        mode (Literal["r", "w"]): 操作模式。'r' 表示读取，'w' 表示覆盖写入。
        data (Optional[dict]): 要写入的 JSON 数据，仅在 mode 为 'w' 时填写。

    Raises:
        ValueError: 如果 mode 非法、 data 为空或 JSON 解码失败。
        FileNotFoundError: 如果指定的 JSON 文件不存在。

    Returns:
        dict | None: 读取时返回 JSON 数据（字典），写入成功时返回 None。
    """
    try:
        if mode == "r":
            path_obj = Path(json_path)
            content = path_obj.read_text(encoding="utf-8")
            return json.loads(content)
        elif mode == "w":
            if data is None:
                raise ValueError("未找到应写入的 data！")
            path_obj = Path(json_path)
            content = json.dumps(data, ensure_ascii=False, indent=4)
            path_obj.write_text(content, encoding="utf-8")
            return None
        else:
            raise ValueError(f"非法的 mode 参数: {mode}")
    except FileNotFoundError as e:
        logger.exception(f"未找到 JSON 文件: {json_path}")
        raise FileNotFoundError(f"未找到 JSON 文件: {json_path}") from e
    except json.JSONDecodeError as e:
        logger.exception(f"JSON 解码失败: {e}")
        raise ValueError(f"JSON 解码失败: {e}") from e
    except Exception as e:
        logger.exception(f"处理 JSON 文件时发生未知错误: {e}")
        raise


# 批量转发内容构建函数
async def batch_get(text: str, picture: Optional[str], qq: int, name: str) -> MessageSegment:
    if picture is not None:
        make_information = MessageSegment.text(text) + MessageSegment.image(picture)
    else:
        make_information = MessageSegment.text(text)
    make_text = MessageSegment.node_custom(
        user_id=qq,
        nickname=f"{name}",
        content=Message(make_information))
    return make_text


def time_handle(datetime_input):
    """
    根据用户提供的时间戳，计算与当前时间的时间差，并以“年月日时分秒”的格式返回。
    Args:
        datetime_input (int): 用户提供的 Unix 时间戳（秒级）。
    Returns:
        str: 时间差的字符串表示，例如“1年2个月3天4小时5分钟6秒”。
    """
    # 将时间戳转换为 datetime 对象
    time_obj = datetime.fromtimestamp(datetime_input)
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


# TODO: 需要重构
async def furry_fusion_picture_handle(picture: str, name: str, text: str) -> str:
    # --------
    response = httpx.get(picture)
    if response.status_code != 200:
        raise Exception(f"图片下载失败，状态码: {response.status_code}")
    img = Image.open(BytesIO(response.content))
    overlay_image = Image.open(FURRY_FUSION_BG_PATH).convert("RGBA")
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
    font_path = Path.cwd() / 'data' / 'SourceHanSansSC-VF.ttf'
    font = ImageFont.truetype(font_path, size=95)

    text_color = (255, 255, 255)
    draw.text((10, 50), text, font=font, fill=text_color)

    # 生成唯一文件名
    unique_filename = f"image_{name}.png"
    output_path = os.path.join(output_dir, unique_filename)
    img_resized.save(output_path, format="PNG")
    return os.path.abspath(output_path)
    # --------


# 配置项读取函数
def get_config_item(key: str, default=None, required=False, desc=None):
    config = get_driver().config
    try:
        value = getattr(config, key)
        if value:
            return value
    except AttributeError:
        pass
    if required:
        logger.warning(f"[Furry模块] 缺少必要配置项: {key} ，{desc or ''}")
    return default
