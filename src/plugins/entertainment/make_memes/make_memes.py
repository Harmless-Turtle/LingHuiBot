from io import BytesIO

from nonebot.adapters.onebot.v11 import MessageSegment, Message, GroupMessageEvent
from nonebot.params import CommandArg,RawCommand
from meme_generator import (
    Image,
    ImageNumberMismatch,
    TextNumberMismatch,
    TextOverLength,
    MemeFeedback,
    ImageDecodeError,
    ImageEncodeError,
    ImageAssetMissing,
    DeserializeError,
)

from src.plugins.entertainment.check_files import memes_make_path
from src.plugins.utils import handle_errors, at_is_true
from .tools import check_memes_func, download_avatar
from .meme_list_tools import build_meme_groups, render_meme_list_image, add_meme_list_footer
from ..commands import meme_matcher, meme_list_matcher




# ────────────────────────────────────────────────────────────
# 表情列表
# ────────────────────────────────────────────────────────────

@meme_list_matcher.handle()
@handle_errors
async def handle_meme_list(event: GroupMessageEvent):
    groups = build_meme_groups()
    img = render_meme_list_image(groups)
    img = add_meme_list_footer(img)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    await meme_list_matcher.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(buf))


# ────────────────────────────────────────────────────────────
# 制作表情
# ────────────────────────────────────────────────────────────

@meme_matcher.handle()
@handle_errors
async def handle_meme(
        event: GroupMessageEvent,
        args: Message = CommandArg(),
        raw_cmd = RawCommand()
):
    plain = args.extract_plain_text().strip()
    tokens = plain.split()
    if raw_cmd in ("摸",):
        meme_key_input = 'petpet'
        user_texts = []
    elif not tokens:
        await meme_matcher.finish(
            MessageSegment.reply(event.message_id) +
            "用法：制作表情 <表情名> [文字1] [文字2] ...\n"
            "发送\"表情列表\"可查看所有可用表情及其所需参数。"
        )
    else:
        meme_key_input = tokens[0]
        user_texts = tokens[1:]

    meme = await check_memes_func(meme_key_input)
    if isinstance(meme, RuntimeError):
        await meme_matcher.finish(MessageSegment.reply(event.message_id)+f"运行时错误：{meme}")
    params = meme.info.params
    min_img = params.min_images
    max_img = params.max_images
    min_txt = params.min_texts
    max_txt = params.max_texts

    # ── 文字数量处理 ─────────────────────────────────────────
    texts = list(user_texts)
    using_default = False

    if len(texts) < min_txt:
        # 先尝试用 default_texts 补齐
        if params.default_texts:
            texts = list(params.default_texts)
            using_default = True

        # 补完后仍不足，报错提示
        if len(texts) < min_txt:
            needed = f"{min_txt}" if min_txt == max_txt else f"{min_txt}~{max_txt}"
            await meme_matcher.finish(MessageSegment.reply(event.message_id)+
                f"该表情「{meme_key_input}」需要 {needed} 段文字，"
                f"你只提供了 {len(user_texts)} 段。\n"
                f"示例：制作表情 {meme_key_input} " +
                " ".join(f"<文字{i + 1}>" for i in range(min_txt))
            )

    # 超出上限则截断（max_texts == -1 表示无上限）
    if max_txt != -1 and len(texts) > max_txt:
        texts = texts[:max_txt]

    # ── 图片处理 ─────────────────────────────────────────────
    images: list[Image] = []

    if max_img == 0:
        # 纯文字表情，不需要图片
        pass
    else:
        user_id = await at_is_true(event, args)

        if user_id == "illegal":
            await meme_matcher.finish(MessageSegment.reply(event.message_id)+"AT 格式不合法，请直接 @用户 而不是输入 @ 符号。")

        if user_id in ("finish", "illegal") or not user_id.isdigit():
            # 没有 @ 任何人
            if min_img > 0:
                # 必须有图 → 用发送者自己的头像
                user_id = str(event.user_id)
            else:
                # 图片可选 → 跳过
                user_id = None

        if user_id:
            target_dir = memes_make_path / f"{event.user_id}.jpg"
            await download_avatar(user_id, target_dir)
            with open(target_dir, "rb") as f:
                images.append(Image("avatar", f.read()))

        if len(images) < min_img:
            await meme_matcher.finish(MessageSegment.reply(event.message_id)+
                f"该表情「{meme_key_input}」需要至少 {min_img} 张图片，"
                f"请 @对应用户 来提供头像。"
            )

    # ── 生成 ─────────────────────────────────────────────────
    result = meme.generate(images, texts, {"circle": True})

    if isinstance(result, bytes):
        if using_default:
            keyword = meme.info.keywords[0]
            custom_hint = (
                "正在使用默认文本制作图片，要自定义文本，请这么使用：\n"
                f"制作表情 {keyword} " +
                " ".join(f"<文字{i + 1}>" for i in range(max_txt))
            )
            await meme_matcher.finish(MessageSegment.reply(event.message_id)+custom_hint + MessageSegment.image(result))
        else:
            await meme_matcher.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(result))
    elif isinstance(result, ImageNumberMismatch):
        await meme_matcher.finish(MessageSegment.reply(event.message_id)+
            f"图片数量不对：需要 {result.min}~{result.max} 张，实际 {result.actual} 张。"
        )
    elif isinstance(result, TextNumberMismatch):
        await meme_matcher.finish(MessageSegment.reply(event.message_id)+
            f"文字数量不对：需要 {result.min}~{result.max} 段，实际 {result.actual} 段。"
        )
    elif isinstance(result, TextOverLength):
        await meme_matcher.finish(MessageSegment.reply(event.message_id)+f"文字太长了：「{result.text}」")
    elif isinstance(result, MemeFeedback):
        await meme_matcher.finish(MessageSegment.reply(event.message_id)+f"表情生成反馈：{result.feedback}")
    elif isinstance(result, ImageDecodeError):
        await meme_matcher.finish(MessageSegment.reply(event.message_id)+f"图片解码失败：{result.error}")
    elif isinstance(result, (ImageEncodeError, ImageAssetMissing, DeserializeError)):
        raise RuntimeError(str(result))
    else:
        raise RuntimeError(f"未知错误：{result!r}")