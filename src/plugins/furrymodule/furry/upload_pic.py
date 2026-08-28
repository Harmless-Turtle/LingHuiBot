import json
from pathlib import Path

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
)
from nonebot.matcher import Matcher
from nonebot.params import Arg, CommandArg

from ..commands import (
    upload_furry,
    modify_furry,
)
from src.plugins.utils import handle_errors

from .tools import (
    create_upload_directory,
    get_image_segments,
    get_picture_type_name,
    get_picture_type_text,
    remove_upload_directory,
    save_message_images,
    write_upload_info,
    add_review_images
)


@upload_furry.handle()
@handle_errors
async def upload_furry_function(
    event: GroupMessageEvent,
    matcher: Matcher,
    args: Message = CommandArg(),
):
    text = args.extract_plain_text().strip()
    args_list = text.split()
    # 必须提供名字和图片类型
    if len(args_list) < 2:
        await matcher.finish(
            "请按照以下格式上传：\n"
            "上传 <兽兽名字> <图片类型> <图片>\n\n"
            "图片类型：\n"
            f"{get_picture_type_text()}"
        )
    furry_name = args_list[0]
    # 获取图片类型
    try:
        picture_type = int(args_list[1])
    except ValueError:
        await matcher.finish(
            "图片类型必须是数字。\n\n"
            "图片类型：\n"
            f"{get_picture_type_text()}"
        )

    picture_type_name = get_picture_type_name(
        picture_type
    )

    if picture_type_name is None:
        await matcher.finish(
            f"未知图片类型：{picture_type}\n\n"
            "可用图片类型：\n"
            f"{get_picture_type_text()}"
        )

    # 创建本次上传任务目录
    upload_id, upload_dir = create_upload_directory()

    # 保存上传上下文
    matcher.set_arg(
        "upload_id",
        Message(upload_id),
    )

    matcher.set_arg(
        "upload_dir",
        Message(str(upload_dir)),
    )

    matcher.set_arg(
        "furry_name",
        Message(furry_name),
    )

    matcher.set_arg(
        "picture_type",
        Message(str(picture_type)),
    )

    saved_images: list[str] = []

    # 获取命令中携带的图片
    images = get_image_segments(args)

    # 如果命令中已经携带图片，立即保存
    if images:
        try:
            saved_images = await save_message_images(
                message=args,
                upload_dir=upload_dir,
                furry_name=furry_name,
                start_index=0,
            )

        except Exception:
            remove_upload_directory(upload_dir)
            raise

    # 保存已下载图片列表
    matcher.set_arg(
        "saved_images",
        Message(
            json.dumps(
                saved_images,
                ensure_ascii=False,
            )
        ),
    )

    # 发送提示
    if saved_images:
        await matcher.send(
            f"已接收并保存 {len(saved_images)} 张图片。\n"
            f"兽兽：{furry_name}\n"
            f"类型：{picture_type_name}\n\n"
            "可以继续发送图片。\n"
            "发送“结束”完成上传。"
        )
    else:
        await matcher.send(
            f"兽兽：{furry_name}\n"
            f"类型：{picture_type_name}\n\n"
            "请发送图片。\n"
            "可以一次发送多张，也可以分多次发送。\n"
            "发送“结束”完成上传。"
        )


@upload_furry.got(
    "upload_message",
    prompt="请发送图片，或发送“结束”完成上传。",
)
@handle_errors
async def upload_furry_receive(
    event: GroupMessageEvent,
    matcher: Matcher,
    upload_message: Message = Arg(),
):
    """
    持续接收图片。

    收到图片后立即保存。

    用户发送“结束”后生成：
        upload_info.json
    """

    # 获取上传任务信息
    upload_id = (
        matcher.get_arg("upload_id")
        .extract_plain_text()
        .strip()
    )

    upload_dir = Path(
        matcher.get_arg("upload_dir")
        .extract_plain_text()
        .strip()
    )

    furry_name = (
        matcher.get_arg("furry_name")
        .extract_plain_text()
        .strip()
    )

    picture_type = int(
        matcher.get_arg("picture_type")
        .extract_plain_text()
        .strip()
    )

    saved_images = json.loads(
        matcher.get_arg("saved_images")
        .extract_plain_text()
    )

    plain_text = (
        upload_message.extract_plain_text()
        .strip()
    )

    # 用户发送结束
    if plain_text == "结束":

        # 没有上传图片
        if not saved_images:
            remove_upload_directory(upload_dir)

            await matcher.finish(
                "你还没有上传任何图片，"
                "本次上传已取消。"
            )

        # 写入上传信息
        write_upload_info(
            upload_id=upload_id,
            upload_dir=upload_dir,
            furry_name=furry_name,
            picture_type=picture_type,
            uploader_id=str(event.user_id),
            group_id=getattr(
                event,
                "group_id",
                None,
            ),
            images=saved_images,
        )
        review_ids = add_review_images(
            upload_id=upload_id,
            images=saved_images,
        )

        review_text = ", ".join(
            f"#{review_id}"
            for review_id in review_ids
        )
        await matcher.finish(
            f"上传完成！\n"
            f"兽兽：{furry_name}\n"
            f"类型：{get_picture_type_name(picture_type)}\n"
            f"图片数量：{len(saved_images)}\n"
            "当前状态：等待审核"
        )

    # 获取当前消息中的图片
    images = get_image_segments(upload_message)

    # 当前消息没有图片
    if not images:
        await matcher.reject(
            "请发送图片。\n"
            "也可以发送“结束”完成上传。"
        )

    # 立即保存图片
    try:
        new_images = await save_message_images(
            message=upload_message,
            upload_dir=upload_dir,
            furry_name=furry_name,
            start_index=len(saved_images),
        )

    except Exception:
        await matcher.reject(
            "图片下载失败，请重新发送图片。"
        )

    # 更新图片列表
    saved_images.extend(new_images)

    matcher.set_arg(
        "saved_images",
        Message(
            json.dumps(
                saved_images,
                ensure_ascii=False,
            )
        ),
    )

    # reject 会重新等待 got("upload_message")
    await matcher.reject(
        f"已接收并保存 {len(new_images)} 张图片。\n"
        f"当前共 {len(saved_images)} 张。\n\n"
        "可以继续发送图片，"
        "发送“结束”完成上传。"
    )