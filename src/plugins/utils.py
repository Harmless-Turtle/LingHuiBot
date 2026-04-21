import json
import os
import time
import traceback
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpcore
import httpx
from PIL import Image, ImageDraw, ImageFont
from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment, GroupMessageEvent
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

FONT_PATH = Path() / 'data' / 'SarasaFixedSlabJ-SemiBoldItalic.ttf'
FURRY_FUSION_BG_PATH = Path() / 'data' / 'furry_system' / 'bg.png'
ERROR_DIR = Path() / "logs"

# 验证字体包是否存在
if os.path.exists(FONT_PATH):
    logger.info(f"已找到字体文件: {FONT_PATH}")
else:
    FONT_PATH = None
    logger.warning(f"未找到字体文件: {FONT_PATH}，将使用默认字体，可能导致错误日志图片显示异常。请确保 {FONT_PATH} 存在以获得最佳体验。")

# 捕获并处理函数执行中的异常，生成错误日志并构造用户友好的反馈
def handle_errors(func):
    """
    装饰一个函数以捕获异常（除了 MatcherException），提供统一的错误处理逻辑，使用该装饰器需要填写 matcher 和 event 参数。
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
            error_script = traceback.extract_tb(error.__traceback__)[-1].filename
            times = lambda x: time.strftime(x)
            error_msg = (
                f"脚本：{error_script}\n"
                f"在“{times('%Y-%m-%d %a %H:%M:%S')}”时返回了异常错误。内容如下：\n\n"
                f"{traceback.format_exc()}\n"
                "---------------------异常错误截止---------------------\n"
            )

            # 追加到工作目录的 ERROR_DIR/error.log
            ERROR_DIR.mkdir(parents=True, exist_ok=True)
            with open(ERROR_DIR / "error.log", 'a', encoding='utf-8') as filestream:
                filestream.write(error_msg)

            # 按时间戳生成并保存报错图片到 logs/error_****.png
            error_image = generate_text_image(error_msg, FONT_PATH)
            error_image.save(ERROR_DIR / f"error_{times('%Y%m%d%H%M%S')}.png", format="PNG")

            # 如果事件是消息类型，则尝试回复用户报错图片和消息
            event = next((x for x in args if isinstance(x, MessageEvent)), kwargs.get("event"))
            matcher = next((x for x in args if isinstance(x, Matcher)), kwargs.get("matcher"))

            if isinstance(event, MessageEvent) and matcher:
                buffer_image = BytesIO()
                error_image.save(buffer_image, format="PNG")
                buffer_image.seek(0)
                error_response = create_error_reply(error, event, buffer_image)
                await matcher.finish(error_response + "\nTips:您可以通过发送“bug反馈”来将此错误日志直接反馈给开发者")
            else:
                logger.warning(
                    f"{__name__}捕获到错误，但由于被装饰的函数没有填写 matcher 和 event 参数，无法告知用户")
                logger.error(error_msg)

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
def generate_text_image(error_msg, font_path):
    font = ImageFont.truetype(font_path, size=30) if font_path.exists() else ImageFont.load_default()
    lines = error_msg.split('\n')
    padding = 20
    line_spacing = 5

    default_height = font.getbbox("A")[3] - font.getbbox("A")[1]
    line_sizes = [font.getbbox(line) for line in lines]
    line_widths = [bbox[2] - bbox[0] for bbox in line_sizes]
    line_heights = [
        (bbox[3] - bbox[1]) if line.strip() else default_height  # 有空行时用“A”的行高
        for line, bbox in zip(lines, line_sizes)
    ]

    width = int(max(line_widths) + padding * 2)
    height = int(sum(line_heights) + line_spacing * (len(lines) - 1) + padding * 2)

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    y = padding
    for i, line in enumerate(lines):
        draw.text((padding, y), line, fill=(0, 0, 0), font=font)
        y += line_heights[i] + line_spacing

    return image


# json加载函数
def handle_json(json_path: Path, mode: str, data: Optional[dict | list] = None) -> dict:
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
    img_resized = img.resize(target_size, Image.Resampling.LANCZOS)
    img_resized.paste(
        overlay_image,
        (0, 0),
        alpha
    )
    img_resized = img_resized.convert("RGB")
    output_dir = Path.cwd() / 'data' / 'Furry_System' / "processed_images"
    os.makedirs(output_dir, exist_ok=True)

    draw = ImageDraw.Draw(img_resized)
    font_path = Path.cwd() / 'data' / 'SourceHanSansSC-VF.ttf'
    font = ImageFont.truetype(str(font_path), size=95)

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


# ========= 工具函数：异步请求 API =========
async def get_api_httpx(endpoint: str, service: str = "None", request_mode: str = "get") -> dict:
    """
    统一的异步 API 请求工具。

    参数:
        endpoint (str): API 路径（如 'service/screen'）。
        params (dict | None): 查询参数字典，可选，默认为 None。
        service (str): 服务名称，用于区分不同api的请求。
        request_mode (str): 请求方式，'get' 或 'post'，默认为 'get'。
    返回:
        dict: 成功时返回解析后的 JSON 数据；发生错误时抛出 Exception。
    """
    if service == "furryfusion":
        url = f"https://api.furryfusion.net/{endpoint}"
    elif service == "furry":
        url = f"https://cloud.foxtail.cn/api/{endpoint}"
    else:
        raise ValueError("未填写服务url，工具运行失败。")
    async with httpx.AsyncClient() as client:
        if request_mode == "post":
            response = await client.post(url, timeout=10.0)
        else:
            response = await client.get(url, timeout=10.0)
        # 如果状态码不是 2xx，抛出异常
        response.raise_for_status()
        return response.json()


def ensure_files_exist(file_path: list[Path], description: str, normal_data: list) -> None:
    """
    文件与路径校验函数

    :param file_path: 需要校验的 Path 对象列表
    :param description: 当前校验模块的描述名称，用于 logger 输出
    :param normal_data: 与 file_path 一一对应的默认数据列表
    """
    # 健壮性检查：确保路径和数据数量一一对应
    if len(file_path) != len(normal_data):
        logger.error(f"[{description}] 校验异常：file_path 和 normal_data 列表长度不一致！")
        return

    for path, data in zip(file_path, normal_data):
        if path.suffix != "":
            # ======= 处理文件 =======
            # 1. 如果文件的父目录不存在，先创建父目录
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)

            # 2. 如果文件实体不存在，则尝试创建并写入默认数据
            if not path.exists():
                logger.info(f"[{description}] {path}不存在，尝试创建")
                try:
                    # 判断数据和文件类型进行安全写入
                    if isinstance(data, (dict, list)) and path.suffix.lower() == ".json":
                        # 专门为 json 文件写入标准 JSON 格式数据
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                    elif isinstance(data, str):
                        # 如果是字符串，直接写入（如txt文本等）
                        path.write_text(data, encoding="utf-8")
                    else:
                        # 对于 .jpg / .ttf 等非文本文件，或 data 未指定时，只创建空文件实体
                        path.touch()

                    logger.success(f"[{description}] 文件创建成功")
                except Exception as e:
                    logger.error(f"[{description}] {path} 创建失败 | Error: {e}")

        else:
            # ======= 处理目录 =======
            if not path.exists():
                logger.info(f"[{description}] {path}不存在，尝试创建")
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logger.error(f"[{description}] {path} 创建失败 | Error: {e}")

    logger.info(f"[{description}] 所有的文件及路径自检完毕。")


async def at_is_true(
        event: GroupMessageEvent,
        args:Message = CommandArg()
):
    """

    Args:
        event: 注入依赖项：GroupMessageEvent
        args: 注入依赖项：Message = CommandArg()

    Returns:
        str:
         可能的情况：

        返回“finish”[str]：指用户提供的文本既无真实AT消息段，纯文本也没有包含“@”符号 -> 直接结束事件即可。

        返回"illegal"[str]：用户提供的文本中没有真实AT消息段，但纯文本包含了“@”符号 -> 可能是用户复制了别人的AT指令但未正确使用，提示用户指令不合法。

        返回用户id[str]：有效的AT段，返回的是被AT用户的id
    """
    plain_text = args.extract_plain_text().strip()
    # 检查消息段中是否包含真实的 AT
    has_real_at = any(seg.type == "at" for seg in args)
    # 拦截逻辑：既没有真实 AT，也没有包含 "@" 符号的文本
    if not (has_real_at or "@" in str(plain_text)):
        return "finish"
    target_id = None
    # 获取at的用户
    for msg_seg in event.original_message:
        if msg_seg.type == 'at':
            target_id = msg_seg.data['qq']
            break
    # 检查是否存在 at
    if not target_id and "@" in (str(event.raw_message)):
        return "illegal"
    return str(target_id)