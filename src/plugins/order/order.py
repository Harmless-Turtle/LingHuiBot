import os
import tempfile
from pathlib import Path

import httpx
from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from ..Exceptions import UserVisibleError
from ..utils import handle_errors
from .command import delete_order, list_order, order, upload_order
from .exceptions import (
    OrderImageDownloadError,
    OrderImageSaveError,
)
from .model import (
    add_or_update_order_item,
    delete_order_item,
    get_all_order_items,
    get_random_order_item,
)

PICTURE_DIR = Path.cwd() / "data" / "Order_System" / "Picture"


@order.handle()
@handle_errors
async def order_function(
        matcher: Matcher,
        event: MessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg(),
):
    if args.extract_plain_text(): await matcher.finish()

    item = await get_random_order_item(session)

    pic_path = Path(item.picture_path)
    reply_msg = (
            MessageSegment.reply(event.message_id)
            + f"您好~您的饮品是【{item.name}】，请慢用~"
    )
    if pic_path.exists():
        reply_msg += "\n" + MessageSegment.image(pic_path)

    await matcher.finish(reply_msg)


@upload_order.handle()
@handle_errors
async def upload_order_function(
        matcher: Matcher,
        event: MessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg(),
):
    args_str = str(args)
    data = args_str.split("#")
    if len(data) != 3:
        raise UserVisibleError(
            "输入格式不正确，请重新上传\n"
            "正确的格式应该是：上传饮品#饮品名字#饮品图片"
        )
    name = data[1].strip()
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise UserVisibleError("饮品名称不能为空，也不能包含路径分隔符哦~")

    msg_group = event.get_message()
    if not msg_group["image"]:
        raise UserVisibleError("没有检测到图片，请在命令后附带一张饮品图片~")
    url = msg_group["image"]
    pic_url = list(url)[-1].data["url"]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(pic_url)
            if resp.status_code != 200:
                raise OrderImageDownloadError(resp.status_code)
            img_content = resp.content
    except httpx.HTTPError as e:
        raise UserVisibleError("图片下载超时或网络错误，请稍后重试~") from e

    if len(img_content) > 10 * 1024 * 1024:
        raise UserVisibleError("图片太大了，请上传 10MB 以内的图片呢xwx")

    tmp_path: Path | None = None
    try:
        PICTURE_DIR.mkdir(parents=True, exist_ok=True)
        pic_path = PICTURE_DIR / f"{name}.jpg"
        fd, tmp_name = tempfile.mkstemp(prefix=f"{name}.", suffix=".tmp", dir=str(PICTURE_DIR))
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "wb") as f:
            f.write(img_content)

        await add_or_update_order_item(
            session=session,
            name=name,
            picture_path=str(pic_path),
            uploader_id=str(event.user_id),
        )
        await session.commit()
        # 提交成功后再替换，避免 DB 写失败时把旧图覆盖掉
        os.replace(tmp_path, pic_path)
        tmp_path = None
    except Exception as e:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise OrderImageSaveError() from e

    await matcher.finish(
        MessageSegment.reply(event.message_id)
        + "操作成功完成。"
    )


@delete_order.handle()
@handle_errors
async def delete_order_function(
        matcher: Matcher,
        event: MessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg(),
):
    name = args.extract_plain_text().strip()
    if not name:
        raise UserVisibleError("请输入要删除的饮品名称，例如：删除饮品 珍珠奶茶")

    pic_path_str = await delete_order_item(session, name)
    await session.commit()

    # 提交事务成功后再清理磁盘图片文件
    try:
        pic_file = Path(pic_path_str)
        if pic_file.exists():
            pic_file.unlink(missing_ok=True)
    except OSError as e:
        logger.warning(f"[Order] 清理本地图片文件失败 ({pic_path_str}): {e}")

    await matcher.finish(
        MessageSegment.reply(event.message_id)
        + "操作成功完成。"
    )


@list_order.handle()
@handle_errors
async def list_order_function(
        matcher: Matcher,
        event: MessageEvent,
        session: async_scoped_session,
):
    items = await get_all_order_items(session)
    if not items:
        raise UserVisibleError("当前菜单还没有任何饮品哦~")

    names = "、".join(item.name for item in items)
    await matcher.finish(
        MessageSegment.reply(event.message_id)
        + f"当前饮品菜单共有 {len(items)} 种：\n{names}"
    )
