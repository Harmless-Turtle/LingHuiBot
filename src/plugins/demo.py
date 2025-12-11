import datetime
import httpx
from nonebot import (
    on_command,
    get_driver,
    logger
)
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import os
from PIL import Image, ImageDraw, ImageFont
from nonebot.matcher import Matcher

# ========= 特殊聚会列表 =========
config = get_driver().config
try:
    SPECIAL_EVENTS = config.SPECIAL_EVENTS
except:
    SPECIAL_EVENTS = [
        "得闲兽聚",
        "hifurry",
        "furrygooo"
    ]
    logger.error(f"未获取到自定义特殊兽聚列表，将使用内置兽聚列表，列表内容：\n{SPECIAL_EVENTS}")


# ========= 插件指令 =========
schedule_cmd = on_command("demo", priority=5)


# ========= 工具函数：请求 API =========
async def get_event_list():
    """
    访问FurryFusion活动API，获取活动列表
    """
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.get("https://api.furryfusion.net/service/activity")
            resp.raise_for_status()
            response = resp.json()
    except httpx.HTTPError:
        return False
    return response.get("data", [
        {
            "title": "请求失败！",
            "location": f"{resp.status_code} {resp.reason_phrase}",
            "time_start": "1900-01-01",
            "time_end": "9999-01-01"
        }
    ])

# ========= 工具函数：生成倒计时 =========
def calc_days_remaining(start_date: str):
    today = datetime.date.today()
    start = datetime.datetime.strptime(start_date, "%Y.%m.%d").date()
    days = (start - today).days
    return days

def format_remaining_days(days: int) -> tuple:
    """格式化剩余天数显示，返回(文本, 颜色)"""
    if days < 0:
        text = f"已开始{abs(days)}天"
        color = (132, 37, 62)  # 红色
    elif days == 0:
        text = "今天开始"
        color = (243, 213, 22)
    else:
        text = f"剩余 {days} 天"
        color = (120, 180, 255)  # 蓝色
    return text, color


# ========= 工具函数：按月份分组 =========
def group_by_year_month(events):
    groups = {}
    for e in events:
        s = e.get("time_start", "")
        dt = datetime.datetime.strptime(s, "%Y.%m.%d").date()
        year = str(dt.year)
        month = f"{dt.year}.{dt.month:02d}"

        if year not in groups:
            groups[year] = {}
        if month not in groups[year]:
            groups[year][month] = []

        groups[year][month].append(e)
    return groups
    

# ========= 图片生成 =========
def render_schedule_image(groups: dict):
    width = 1080
    padding = 40
    card_w = 300
    card_h = 150
    gap = 30

    # 当前文件所在目录
    BASE_DIR = os.path.dirname(__file__)

    # 字体路径
    FONT_PATH = os.path.join(BASE_DIR, "MiSans-Demibold.ttf")

    font_title = ImageFont.truetype(FONT_PATH, 30)
    font_small = ImageFont.truetype(FONT_PATH, 20)

    # 先计算总高度
    y_offset = padding
    for year in sorted(groups.keys()):  # 按年份顺序排列（旧年份在前）
        months = groups[year]
        y_offset += 70  # 年份标题高度
        for month, events in months.items():
            y_offset += 50  # 月份标题高度
            x = padding
            for idx, e in enumerate(events):
                x += card_w + gap
                if x + card_w > width - padding:
                    x = padding
                    y_offset += card_h + gap
            if x != padding:
                y_offset += card_h + gap
            y_offset += 60  # 月份间距
        y_offset += 20  # 年份间距

    # 创建最终尺寸的图片
    img = Image.new("RGB", (width, y_offset + 100), (22, 22, 28))
    draw = ImageDraw.Draw(img)

    # 绘制内容 — 带时间树（年份左实心圆，月份左空心圆，直线连接）
    y_offset = padding
    timeline_x = padding - 20
    year_r = 8
    month_r = 6
    line_color = (100, 100, 110)

    prev_node_y = None
    prev_node_r = None

    for year in sorted(groups.keys()):  # 按年份顺序排列
        months = groups[year]
        # 年份文本高度与中心
        year_h = font_title.getbbox(year)[3]
        year_center_y = y_offset + year_h // 2

        # 若存在前一个节点，画线到当前年份圆的边缘（避免线进入圆内）
        if prev_node_y is not None:
            if year_center_y > prev_node_y:
                start_y = prev_node_y + prev_node_r
                end_y = year_center_y - year_r
            else:
                start_y = prev_node_y - prev_node_r
                end_y = year_center_y + year_r
            draw.line((timeline_x, start_y, timeline_x, end_y), fill=line_color, width=3)

        # 年份圆（实心）和文本
        draw.ellipse((timeline_x - year_r, year_center_y - year_r, timeline_x + year_r, year_center_y + year_r), fill=(255, 255, 255))
        draw.text((padding, y_offset), year, font=font_title, fill=(255, 255, 255))
        y_offset += year_h + 12

        # 更新为当前节点
        prev_node_y = year_center_y
        prev_node_r = year_r

        for month, events in months.items():
            month_h = font_small.getbbox(month)[3]
            month_center_y = y_offset + month_h // 2

            # 画连接线（从上一个节点到当前月份节点，止于圆边缘）
            if prev_node_y is not None:
                if month_center_y > prev_node_y:
                    start_y = prev_node_y + prev_node_r
                    end_y = month_center_y - month_r
                else:
                    start_y = prev_node_y - prev_node_r
                    end_y = month_center_y + month_r
                draw.line((timeline_x, start_y, timeline_x, end_y), fill=line_color, width=3)

            # 月份空心圆和文本
            draw.ellipse((timeline_x - month_r, month_center_y - month_r, timeline_x + month_r, month_center_y + month_r), outline=line_color, width=2)
            draw.text((padding + 20, y_offset), month, font=font_small, fill=(200, 200, 200))
            y_offset += month_h + 10

            # 更新节点为月份
            prev_node_y = month_center_y
            prev_node_r = month_r

            x = padding
            for idx, e in enumerate(events):
                # 文本内容
                name = e["title"]
                location = e.get("address", "")
                date_str = f"{e['time_start']} - {e['time_end']}"
                remain = calc_days_remaining(e["time_start"])
                remain_str, remain_color = format_remaining_days(remain)

                # 判断是否为特殊聚会
                is_special = name in SPECIAL_EVENTS
                name_color = (240, 215, 140) if is_special else (79, 129, 199)  # 金色或蓝色

                # 获取文本高度（bbox = (x0, y0, x1, y1)）
                name_h = font_title.getbbox(name)[3]
                location_h = font_small.getbbox(location)[3]
                date_h = font_small.getbbox(date_str)[3]
                remain_h = font_small.getbbox(remain_str)[3]

                # 文字间距
                gap_text = 6

                # 计算总高度，用来垂直居中
                total_h = name_h + location_h + date_h + remain_h + gap_text * 3
                start_y = y_offset + (card_h - total_h) // 2

                # 卡片
                card = (x, y_offset, x + card_w, y_offset + card_h)
                draw.rounded_rectangle(card, radius=18, fill=(35, 38, 48))
                # 添加与标题颜色一致的边框
                draw.rounded_rectangle(card, radius=18, outline=name_color, width=2)

                # 绘制内容（垂直自动排版）
                cy = start_y
                draw.text((x + 20, cy), name, font=font_title, fill=name_color)
                cy += name_h + gap_text

                draw.text((x + 20, cy), location, font=font_small, fill=(180, 180, 180))
                cy += location_h + gap_text

                draw.text((x + 20, cy), date_str, font=font_small, fill=(180, 180, 180))
                cy += date_h + gap_text

                draw.text((x + 20, cy), remain_str, font=font_small, fill=remain_color)

                # 多列布局
                x += card_w + gap
                if x + card_w > width - padding:
                    x = padding
                    y_offset += card_h + gap

            if x != padding:
                y_offset += card_h + gap
            y_offset += 60

            # 更新上一个节点为当前月份节点（用于下一次连接）
            prev_node_y = month_center_y

        y_offset += 1

    return img
# ========= 主逻辑 =========
@schedule_cmd.handle()
async def handle_schedule(matcher:Matcher,arg: Message = CommandArg()):
    events = await get_event_list()
    if events is False:
        await matcher.finish("无法获取活动列表，请稍后再试。")
    groups = group_by_year_month(events)
    img = render_schedule_image(groups)

    # 保存临时文件
    file_path = os.path.join(os.getcwd(), "schedule.png")
    img.save(file_path)

    await matcher.finish(MessageSegment.image(f"file:///{file_path}"))