"""
表情列表图片生成工具
复用 furry 模块的 render_schedule_image / add_custom_footer 风格，
但数据结构和卡片内容针对 meme_generator 重新定义。
不修改原始 tools.py。
"""
import datetime

from PIL import Image, ImageDraw, ImageFont
from meme_generator import get_memes

from src.plugins.utils import FONT_PATH


# ────────────────────────────────────────────────────────────
# 数据准备
# ────────────────────────────────────────────────────────────

def build_meme_groups() -> dict:
    """
    按 date_created 年 → 月分组，结构与兽聚 group_by_year_month 保持一致：
      { "2022": { "2022.10": [ MemeCard, ... ], ... }, ... }

    MemeCard 是一个普通 dict，包含渲染卡片所需的字段。
    """
    all_memes = get_memes()
    groups: dict[str, dict[str, list]] = {}

    for meme in all_memes:
        info = meme.info
        params = info.params

        dt = info.date_created
        year = str(dt.year)
        month = f"{dt.year}.{dt.month:02d}"

        # 关键词（优先取中文，回退到 key）
        keywords = info.keywords
        display_name = next(
            (k for k in keywords if any('\u4e00' <= c <= '\u9fff' for c in k)),
            keywords[0] if keywords else meme.key
        )
        all_keywords = "、".join(keywords) if len(keywords) > 1 else ""

        # 图片需求描述
        min_img, max_img = params.min_images, params.max_images
        if max_img == 0:
            img_desc = "无需图片"
        elif min_img == max_img:
            img_desc = f"需 {min_img} 张图片"
        else:
            img_desc = f"需 {min_img}~{max_img} 张图片"

        # 文字需求描述
        min_txt, max_txt = params.min_texts, params.max_texts
        if max_txt == 0:
            txt_desc = "无需文字"
        elif min_txt == max_txt:
            txt_desc = f"需 {min_txt} 段文字"
        else:
            txt_desc = f"需 {min_txt}~{max_txt} 段文字"

        # 有默认文本时额外标注
        has_default = bool(params.default_texts) and min_txt > 0

        card = {
            "display_name": display_name,
            "all_keywords": all_keywords,
            "img_desc": img_desc,
            "txt_desc": txt_desc,
            "has_default": has_default,
            "date_created": f"{dt.year}.{dt.month:02d}.{dt.day:02d}",
        }

        groups.setdefault(year, {}).setdefault(month, []).append(card)

    return groups


# ────────────────────────────────────────────────────────────
# 渲染
# ────────────────────────────────────────────────────────────

# 配色（与兽聚风格保持一致）
_BG        = (22, 22, 28)
_CARD_BG   = (35, 38, 48)
_LINE_CLR  = (100, 100, 110)
_WHITE     = (255, 255, 255)
_GREY      = (180, 180, 180)
_DIM       = (130, 130, 140)

# 卡片类型色
_CLR_IMG   = (79, 129, 199)   # 需要图片 → 蓝色（与兽聚活动名一致）
_CLR_TXT   = (120, 195, 140)  # 有文字    → 绿色
_CLR_PURE  = (160, 120, 200)  # 纯文字表情 → 紫色
_CLR_DFLT  = (243, 213, 22)   # 有默认文本 → 金色（与兽聚特殊聚会一致）


def _card_accent(card: dict) -> tuple:
    """根据卡片属性决定强调色（边框 + 名称色）"""
    if card["has_default"]:
        return _CLR_DFLT
    if card["img_desc"] == "无需图片":
        return _CLR_PURE
    if card["txt_desc"] == "无需文字":
        return _CLR_IMG
    return _CLR_TXT


def render_meme_list_image(groups: dict) -> Image.Image:
    """
    渲染表情列表图片，布局与 render_schedule_image 完全对齐：
    - 左侧时间轴（年实心圆 / 月空心圆 / 连接线）
    - 右侧多列卡片（3 列，每张 300×150）
    """
    width   = 1080
    padding = 40
    card_w  = 300
    card_h  = 150
    gap     = 30
    cols    = 3  # 每行最多 3 列，比兽聚多一列（卡片内容更简短）

    font_title = ImageFont.truetype(FONT_PATH, 28)
    font_small = ImageFont.truetype(FONT_PATH, 20)
    font_tiny  = ImageFont.truetype(FONT_PATH, 16)

    # ── 第一遍：预算总高度 ────────────────────────────────
    def _calc_height() -> int:
        y = padding
        for year in sorted(groups):
            y += 70   # 年份行
            for month, cards in groups[year].items():
                y += 50  # 月份行
                x = padding
                for card in cards:
                    x += card_w + gap
                    if x + card_w > width - padding:
                        x = padding
                        y += card_h + gap
                if x != padding:
                    y += card_h + gap
                y += 60
            y += 20
        return y

    total_h = _calc_height()
    img  = Image.new("RGB", (width, total_h), _BG)
    draw = ImageDraw.Draw(img)

    # ── 第二遍：绘制 ──────────────────────────────────────
    y_offset    = padding
    timeline_x  = padding - 20
    year_r      = 8
    month_r     = 6
    prev_node_y = None
    prev_node_r = None

    for year in sorted(groups):
        months = groups[year]

        year_h      = font_title.getbbox(year)[3]
        year_cy     = y_offset + year_h // 2

        # 连接上一节点到本年份圆
        if prev_node_y is not None:
            s = prev_node_y + prev_node_r
            e = year_cy - year_r
            if e > s:
                draw.line((timeline_x, s, timeline_x, e), fill=_LINE_CLR, width=3)

        # 年份实心圆 + 文本
        draw.ellipse(
            (timeline_x - year_r, year_cy - year_r,
             timeline_x + year_r, year_cy + year_r),
            fill=_WHITE
        )
        draw.text((padding, y_offset), year, font=font_title, fill=_WHITE)
        y_offset   += year_h + 12
        prev_node_y = year_cy
        prev_node_r = year_r

        for month, cards in months.items():
            month_h  = font_small.getbbox(month)[3]
            month_cy = y_offset + month_h // 2

            # 连接上一节点到本月份圆
            if prev_node_y is not None:
                s = prev_node_y + prev_node_r
                e = month_cy - month_r
                if e > s:
                    draw.line((timeline_x, s, timeline_x, e), fill=_LINE_CLR, width=3)

            # 月份空心圆 + 文本
            draw.ellipse(
                (timeline_x - month_r, month_cy - month_r,
                 timeline_x + month_r, month_cy + month_r),
                outline=_LINE_CLR, width=2
            )
            draw.text((padding + 20, y_offset), month, font=font_small, fill=_GREY)
            y_offset   += month_h + 10
            prev_node_y = month_cy
            prev_node_r = month_r

            # 卡片多列布局
            x = padding
            for card in cards:
                accent = _card_accent(card)

                # 卡片底色 + 边框
                rect = (x, y_offset, x + card_w, y_offset + card_h)
                draw.rounded_rectangle(rect, radius=18, fill=_CARD_BG)
                draw.rounded_rectangle(rect, radius=18, outline=accent, width=2)

                # ── 卡片内容垂直排布 ──
                cx = x + 18
                cy = y_offset + 14

                # 表情名（强调色）
                draw.text((cx, cy), card["display_name"], font=font_title, fill=accent)
                cy += font_title.getbbox(card["display_name"])[3] + 6

                # 别名（暗灰，过长截断）
                alias = card["all_keywords"]
                if alias:
                    # 限制别名宽度
                    max_alias_w = card_w - 36
                    while alias and font_tiny.getlength(alias) > max_alias_w:
                        alias = alias[:-1]
                    if alias != card["all_keywords"]:
                        alias += "…"
                    draw.text((cx, cy), alias, font=font_tiny, fill=_DIM)
                    cy += font_tiny.getbbox(alias)[3] + 6

                # 图片 / 文字需求
                draw.text((cx, cy), card["img_desc"], font=font_small, fill=_GREY)
                cy += font_small.getbbox(card["img_desc"])[3] + 4

                draw.text((cx, cy), card["txt_desc"], font=font_small, fill=_GREY)
                cy += font_small.getbbox(card["txt_desc"])[3] + 4

                # 有默认文本时显示小标签
                if card["has_default"]:
                    draw.text((cx, cy), "✦ 有默认文本", font=font_tiny, fill=_CLR_DFLT)

                # 列推进
                x += card_w + gap
                if x + card_w > width - padding:
                    x = padding
                    y_offset += card_h + gap

            if x != padding:
                y_offset += card_h + gap
            y_offset += 60

        y_offset += 20

    return img


def add_meme_list_footer(img: Image.Image) -> Image.Image:
    """在图片底部添加 footer，风格与兽聚 add_custom_footer 一致。"""
    footer_text = (
        f"                   合成时间：{datetime.datetime.now().strftime('%Y.%m.%d %H:%M:%S')}\n"
        "        排版制作：Design by LingHui  |  数据来源：meme-generator"
    )
    footer_h  = 90
    bg_color  = (22, 22, 28)
    txt_color = (100, 100, 110)

    w, h = img.size
    final = Image.new("RGB", (w, h + footer_h), bg_color)
    final.paste(img, (0, 0))

    draw = ImageDraw.Draw(final)
    try:
        font = ImageFont.truetype(FONT_PATH, 20)
    except Exception:
        font = ImageFont.load_default()

    draw.text(
        (w // 2, h + footer_h // 2),
        footer_text,
        font=font,
        fill=txt_color,
        anchor="mm"
    )
    return final
