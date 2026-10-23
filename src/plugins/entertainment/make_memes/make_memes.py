from io import BytesIO

from meme_generator import (
    DeserializeError,
    Image,
    ImageDecodeError,
    ImageEncodeError,
    ImageAssetMissing,
    ImageNumberMismatch,
    MemeFeedback,
    TextNumberMismatch,
    TextOverLength,
)
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, RawCommand

from .meme_list_tools import add_meme_list_footer, build_meme_groups, render_meme_list_image
from .tools import check_memes_func, download_avatar
from ..check_files import memes_make_path
from ..commands import meme_list_matcher, meme_matcher
from ...Exceptions import UserVisibleError
from ...utils import at_is_true, handle_errors


# ────────────────────────────────────────────────────────────
# 表情列表
# ────────────────────────────────────────────────────────────

@meme_list_matcher.handle()
@handle_errors
async def handle_meme_list(matcher: Matcher, event: GroupMessageEvent):
    groups = build_meme_groups()
    img = render_meme_list_image(groups)
    img = add_meme_list_footer(img)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(buf))


# ────────────────────────────────────────────────────────────
# 制作表情
# ────────────────────────────────────────────────────────────

@meme_matcher.handle()
@handle_errors
async def handle_meme(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
    raw_cmd: str = RawCommand(),
):
    plain = args.extract_plain_text().strip()
    tokens = plain.split()
    if raw_cmd in ("摸",):
        if "自己" not in str(args) and "[CQ:at" not in str(args):
            await matcher.finish()
        meme_key_input = "petpet"
        user_texts = []
    elif not tokens:
        raise UserVisibleError(
            "用法：制作表情 <表情名> [文字1] [文字2] ...\n"
            "发送\"表情列表\"可查看所有可用表情及其所需参数。"
        )
    else:
        meme_key_input = tokens[0]
        user_texts = tokens[1:]

    meme = await check_memes_func(meme_key_input)
    if isinstance(meme, RuntimeError):
        raise UserVisibleError(f"运行时错误：{meme}")
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
            raise UserVisibleError(
                f"该表情「{meme_key_input}」需要 {needed} 段文字，"
                f"你只提供了 {len(user_texts)} 段。\n"
                f"示例：制作表情 {meme_key_input} "
                + " ".join(f"<文字{i + 1}>" for i in range(min_txt))
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
        at_user_ids: list[str] = []
        for segment in args:
            if segment.type == "at":
                qq = str(segment.data.get("qq", ""))
                if qq == "all":
                    continue
                if qq.isdigit():
                    at_user_ids.append(qq)

        if at_user_ids:
            if max_img != -1:
                at_user_ids = at_user_ids[:max_img]
            for index, user_id in enumerate(at_user_ids):
                target_dir = memes_make_path / f"{event.message_id}_{index}_{user_id}.jpg"
                await download_avatar(user_id, target_dir)
                with open(target_dir, "rb") as f:
                    images.append(Image("avatar", f.read()))
        else:
            user_id = await at_is_true(event)

            if user_id == "illegal":
                raise UserVisibleError("AT 格式不合法，请直接 @用户 而不是输入 @ 符号。")

            if user_id in ("finish", "illegal") or not user_id.isdigit():
                if min_img > 0:
                    user_id = str(event.user_id)
                else:
                    user_id = None

            if user_id:
                target_dir = memes_make_path / f"{event.user_id}.jpg"
                await download_avatar(user_id, target_dir)
                with open(target_dir, "rb") as f:
                    images.append(Image("avatar", f.read()))

        if len(images) < min_img:
            raise UserVisibleError(
                f"该表情「{meme_key_input}」需要至少 {min_img} 张图片，"
                "请 @对应用户 来提供头像。"
            )

    # ── 生成 ─────────────────────────────────────────────────
    result = meme.generate(images, texts, {"circle": True})

    if isinstance(result, bytes):
        if using_default:
            keyword = meme.info.keywords[0]
            custom_hint = (
                "正在使用默认文本制作图片，要自定义文本，请这么使用：\n"
                f"制作表情 {keyword} "
                + " ".join(f"<文字{i + 1}>" for i in range(max_txt))
            )
            await matcher.finish(
                MessageSegment.reply(event.message_id) + custom_hint + MessageSegment.image(result)
            )
        else:
            await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(result))
    elif isinstance(result, ImageNumberMismatch):
        raise UserVisibleError(f"图片数量不对：需要 {result.min}~{result.max} 张，实际 {result.actual} 张。")
    elif isinstance(result, TextNumberMismatch):
        raise UserVisibleError(f"文字数量不对：需要 {result.min}~{result.max} 段，实际 {result.actual} 段。")
    elif isinstance(result, TextOverLength):
        raise UserVisibleError(f"文字太长了：「{result.text}」")
    elif isinstance(result, MemeFeedback):
        raise UserVisibleError(f"表情生成反馈：{result.feedback}")
    elif isinstance(result, ImageDecodeError):
        raise UserVisibleError(f"图片解码失败：{result.error}")
    elif isinstance(result, (ImageEncodeError, ImageAssetMissing, DeserializeError)):
        raise RuntimeError(str(result))
    else:
        raise RuntimeError(f"未知错误：{result!r}")
