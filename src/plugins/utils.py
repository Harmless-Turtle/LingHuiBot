import json
import os
import tempfile
import time
import traceback
from datetime import datetime, timedelta, timezone
from functools import wraps
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpcore
import httpx
from PIL import Image, ImageDraw, ImageFont
from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    GroupMessageEvent,
    MessageEvent,
)
from nonebot.exception import MatcherException
from nonebot.matcher import current_bot, current_event, current_matcher
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

from .Exceptions import LingHuiError

FONT_PATH = Path() / 'data' / 'SarasaFixedSlabJ-SemiBoldItalic.ttf'
ERROR_DIR = Path() / "logs"

# 验证字体包是否存在（空文件视为缺失，避免 truetype 打开 0 字节字体崩溃）
if os.path.exists(FONT_PATH):
    logger.info(f"已找到字体文件: {FONT_PATH}")
else:
    FONT_PATH = None
    logger.warning(
        f"未找到字体文件: {FONT_PATH}，将使用默认字体，可能导致错误日志图片显示异常。请确保 {FONT_PATH} 存在以获得最佳体验。")


# 捕获并处理函数执行中的异常，生成错误日志并构造用户友好的反馈
def handle_errors(func):
    """
    装饰一个事件函数以捕获异常，提供统一的错误处理逻辑。
        - 业务异常（LingHuiError）会自动回滚事务并直接回复用户友好的提示文案
        - 系统异常会自动回滚事务，记录详细错误日志并发送带图反馈

    Args:
        func: 被装饰的异步函数，通常是一个事件处理函数。

    Raises:
        MatcherException: 这类异常会被直接抛出，不会被捕获处理。
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        bot = current_bot.get()
        event = current_event.get()
        matcher = current_matcher.get()
        session = next((x for x in (*args, *kwargs.values())
                        if isinstance(x, (async_scoped_session, AsyncSession))), None)

        try:
            return await func(*args, **kwargs)
        except MatcherException:
            raise
        # 预期异常
        except LingHuiError as biz_err:
            if session: await session.rollback()

            if isinstance(event, MessageEvent):
                await matcher.finish(MessageSegment.reply(event.message_id) + biz_err.message)
            # 对非交互事件如群通知之类的异常则直接通知超级管理员
            else:
                await notify_superusers(bot, f"事件类型：{event.get_event_name()}\n提示内容：{biz_err.message}")
                await matcher.finish()

        # 非预期异常
        except Exception as error:
            if session: await session.rollback()

            error_msg, buffer_image = _record_error_snapshot(error)

            if isinstance(event, MessageEvent):
                error_response = create_error_reply(error, event, buffer_image)
                await matcher.finish(
                    error_response
                    + "\nTips:您可以通过发送“bug反馈”来将此错误日志直接反馈给开发者"
                )
            else:
                logger.error(error_msg)
                await notify_superusers(bot, f"LingHuiBot 事件异常告警\n{error_msg}")
                await matcher.finish()

    return wrapper


async def notify_superusers(bot, text: str):
    for su_id in getattr(get_driver().config, "superusers", set()):
        try:
            await bot.send_private_msg(user_id=int(su_id), message=text)
        except Exception as e:
            logger.warning(f"向超级管理员 {su_id} 推送私聊失败: {e}")


def _record_error_snapshot(error: Exception) -> tuple[str, BytesIO]:
    """格式化错误栈，写入 error.log，并保存一份错误图片到磁盘，返回日志文本与图片字节流"""
    error_script = traceback.extract_tb(error.__traceback__)[-1].filename
    times = lambda x: time.strftime(x)
    error_msg = (
        f"脚本：{error_script}\n"
        f"在“{times('%Y-%m-%d %a %H:%M:%S')}”时返回了异常错误。内容如下：\n\n"
        f"{traceback.format_exc()}\n"
        "---------------------异常错误截止---------------------\n"
    )

    ERROR_DIR.mkdir(parents=True, exist_ok=True)
    with open(ERROR_DIR / "error.log", 'a', encoding='utf-8') as filestream:
        filestream.write(error_msg)

    error_image = generate_text_image(error_msg, FONT_PATH)
    error_image.save(ERROR_DIR / f"error_{times('%Y%m%d%H%M%S')}.png", format="PNG")

    buffer_image = BytesIO()
    error_image.save(buffer_image, format="PNG")
    buffer_image.seek(0)
    return error_msg, buffer_image


# 根据异常类型生成对应的错误回复消息
def create_error_reply(error: Exception, event: MessageEvent, buffer_image: BytesIO) -> Message:
    """
    根据异常类型生成用户友好的错误响应消息。

    Args:
        error: 捕获的异常对象
        buffer_image: 传入报错图片，用于回复用户
        event: 事件对象，用于构建回复引用

    Returns:
        构建的错误响应消息
    """
    reply_part = MessageSegment.reply(event.message_id)

    # 根据异常类型构建不同的响应消息
    if isinstance(error, httpx.ReadTimeout):
        return reply_part + "请求超时了呢qwq...可能是网络波动，请稍后再试哦～"
    if isinstance(error, httpcore.RemoteProtocolError):
        return reply_part + "服务器断开了连接且未发送任何数据给凌辉qwq...请稍后再试"

    # 默认错误消息
    return (
            reply_part
            + f"没有正确处理请求呢qwq...请联系管理员[{get_admin_qq()}]协助解决哦"
            + MessageSegment.image(buffer_image)
    )


# 根据多行文本和字体生成一张自动排版的图片
def generate_text_image(error_msg, font_path):
    font = (ImageFont.truetype(str(font_path), size=30)
            if font_path and font_path.exists() and font_path.stat().st_size > 0
            else ImageFont.load_default())
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
def handle_json(json_path: Path, mode: str, data: Optional[dict | list] = None) -> dict | None:
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
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            # 先写临时文件再原子替换，避免进程中断把原 JSON 写坏
            fd, tmp_name = tempfile.mkstemp(
                prefix=f"{path_obj.name}.", suffix=".tmp", dir=str(path_obj.parent)
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fp:
                    fp.write(content)
                os.replace(tmp_name, path_obj)
            except BaseException:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise
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
async def batch_get(text: str, picture: Optional[str] | bytes, qq: int, name: str) -> MessageSegment:
    if picture is not None:
        make_information = MessageSegment.text(text) + MessageSegment.image(picture)
    else:
        make_information = MessageSegment.text(text)
    make_text = MessageSegment.node_custom(
        user_id=qq,
        nickname=f"{name}",
        content=Message(make_information))
    return make_text


def image_segment_or_empty(path: str | Path) -> MessageSegment:
    """图片文件存在且非空时返回图片段，否则返回空文本段。

    背景图这类二进制资源缺失（或自检留下了 0 字节占位）时，直接
    MessageSegment.image 会让协议端上传失败、整条消息发不出去；
    这里统一降级成“不带图”，保证文字部分仍然送达。
    """
    picture = Path(path)
    if picture.exists() and picture.stat().st_size > 0:
        return MessageSegment.image(picture)
    return MessageSegment.text("")


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


DEFAULT_ADMIN_QQ = 1097740481


def get_admin_qq() -> int:
    """Bot 管理员 QQ，用于私聊告警 / bug 反馈等通知目标。

    优先读取配置项 BOT_ADMIN_QQ；未配置时回落到历史硬编码值，行为保持不变。
    自建部署者可以通过该配置把告警发给自己，而不是原仓库作者。
    """
    value = get_config_item("bot_admin_qq", default=DEFAULT_ADMIN_QQ)
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning(f"BOT_ADMIN_QQ 配置不是合法数字：{value!r}，已回落到 {DEFAULT_ADMIN_QQ}")
        return DEFAULT_ADMIN_QQ


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


async def at_is_true(event: GroupMessageEvent):
    """
    检测消息中是否存在真实的 AT 段，并返回被 AT 的 QQ（或特殊状态）。

    Returns:
        str: "finish" 表示无需响应（无任何 AT 或 @ 文本）

             "illegal" 表示纯文本含 "@" 但非真实 AT（疑似复制）

             用户 id（str）表示有效的真实 AT
    """
    # 获取完整消息（含所有段）
    full_message = event.original_message
    plain_text = full_message.extract_plain_text().strip()

    # 检查是否存在真实的 AT 段
    has_real_at = any(seg.type == "at" for seg in full_message)

    # 如果既无真实 AT，纯文本也不含 "@"，则无需处理
    if not has_real_at and "@" not in plain_text:
        return "finish"

    # 尝试获取第一个真实 AT 的 QQ
    target_id = None
    for seg in full_message:
        if seg.type == "at":
            target_id = seg.data.get("qq")
            break

    # 有真实 AT 则直接返回 QQ
    if target_id is not None:
        return target_id

    # 没有真实 AT，但纯文本包含 "@"视为非法复制
    if "@" in plain_text:
        return "illegal"


def utc_now() -> datetime:
    """当前标准 UTC 时间（naive datetime），时区由业务层决定（默认硬编码 UTC+8）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
