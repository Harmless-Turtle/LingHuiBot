import datetime
import httpx
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from PIL import Image, ImageDraw, ImageFont

# ========= 插件指令 =========
schedule_cmd = on_command("demo", priority=5)


# ========= 假 API（如你要用真实 API 我可以帮你接） =========
API_URL = "https://api.example.com/furry/events"   # 换成真实 FurryFusion API


# ========= 工具函数：请求 API =========
async def get_event_list():
    """
    你可以换成真实 API。
    这里用示例数据模拟返回。
    """
    # ---- 示例数据（你之后可换成真实 API） ----
    return [
        {
            "name": "奇点兽聚",
            "location": "浙江·苏州",
            "start": "2025-11-29",
            "end": "2025-11-30",
        },
        {
            "name": "得闲兽聚",
            "location": "广东·佛山",
            "start": "2025-12-05",
            "end": "2025-12-07",
        },
        {
            "name": "UWU",
            "location": "广州·增城",
            "start": "2025-12-19",
            "end": "2025-12-21",
        },
        {
            "name": "UWU",
            "location": "广州·增城",
            "start": "2026-12-19",
            "end": "2027-12-21",
        },
    ]


# ========= 工具函数：生成倒计时 =========
def calc_days_remaining(start_date: str):
    today = datetime.date.today()
    start = datetime.date.fromisoformat(start_date)
    return (start - today).days


# ========= 工具函数：按月份分组 =========
def group_by_year_month(events):
    groups = {}
    for e in events:
        dt = datetime.date.fromisoformat(e["start"])
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
    height = 2000
    padding = 40
    card_w = 300
    card_h = 150
    gap = 30

    img = Image.new("RGB", (width, height), (22, 22, 28))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("simhei.ttf", 34)
        font_small = ImageFont.truetype("simhei.ttf", 24)
    except:
        font_title = ImageFont.load_default()
        font_small = ImageFont.load_default()

    y_offset = padding

    for year, months in groups.items():
        # 年份标题
        draw.text((padding, y_offset), year, font=font_title, fill=(255, 255, 255))
        y_offset += 70

        # 遍历月份
        for month, events in months.items():
            draw.text((padding + 20, y_offset), month, font=font_small, fill=(200, 200, 200))
            y_offset += 50

            x = padding
            for e in events:
                card = (x, y_offset, x + card_w, y_offset + card_h)
                draw.rounded_rectangle(card, radius=18, fill=(35, 38, 48))

                draw.text((x + 20, y_offset + 20), e["name"], font=font_title, fill=(200, 220, 255))
                draw.text((x + 20, y_offset + 60), e["location"], font=font_small, fill=(180, 180, 180))

                date_str = f"{e['start']} - {e['end']}"
                draw.text((x + 20, y_offset + 95), date_str, font=font_small, fill=(180, 180, 180))

                remain = calc_days_remaining(e["start"])
                remain_str = f"剩余 {remain} 天"
                draw.text((x + 170, y_offset + 95), remain_str, font=font_small, fill=(120, 180, 255))

                x += card_w + gap
                if x + card_w > width - padding:
                    x = padding
                    y_offset += card_h + gap

            y_offset += card_h + 60

        y_offset += 20

    img = img.crop((0, 0, width, min(y_offset + 100, height)))
    return img

# ========= 主逻辑 =========
@schedule_cmd.handle()
async def handle_schedule(arg: Message = CommandArg()):
    events = await get_event_list()
    groups = group_by_year_month(events)
    img = render_schedule_image(groups)

    # 保存临时文件
    import os
    file_path = os.path.join(os.getcwd(), "schedule.png")
    img.save(file_path)

    await schedule_cmd.finish(MessageSegment.image(f"file:///{file_path}"))