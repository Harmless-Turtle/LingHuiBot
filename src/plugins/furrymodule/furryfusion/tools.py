import asyncio
import datetime
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright
from nonebot import logger

from ..check_file import furryfusion_login_session
from ...Exceptions import LingHuiError
from ...utils import get_config_item, handle_json, handle_errors

# 导入特殊兽聚列表
SPECIAL_EVENTS = get_config_item(
    'furry_special_events',
    default="未获取到数据",
    required=True,
    desc="FurryFusion特殊兽聚列表"
)

token = get_config_item(
    'furry_token',
    default="未获取到数据",
    required=True,
    desc="FurryFusion API Token"
)
username = get_config_item(
    'furryfusion_username',
    default="未获取到数据",
    required=True,
    desc="FurryFusion API Token"
)
password = get_config_item(
    'furryfusion_password',
    default="未获取到数据",
    required=True,
    desc="FurryFusion API Token"
)
if token == "未获取到数据" or username == "未获取到数据" or password == "未获取到数据":
    logger.warning("未获取到FurryFusion API Token或用户名或密码，请检查配置文件。")


# ========= FurryFusion 时间轴 HTML 渲染 =========
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

_playwright_manager = None
_playwright_browser = None
_playwright_lock = asyncio.Lock()


def _timeline_date(value):
    """把 API 日期尽量统一成 YYYY.MM.DD；无法解析时返回原文本。"""
    if value is None:
        return ""
    value = str(value).strip()
    if not value:
        return ""
    for fmt in (
        "%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d",
        "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.datetime.strptime(value, fmt).strftime("%Y.%m.%d")
        except ValueError:
            continue
    return value


def _timeline_remaining(start_date):
    """计算开始日期倒计时；日期格式异常时不阻断整张图。"""
    normalized = _timeline_date(start_date)
    try:
        start = datetime.datetime.strptime(normalized, "%Y.%m.%d").date()
    except (TypeError, ValueError):
        return "日期待确认", "neutral"
    days = (start - datetime.date.today()).days
    if days < 0:
        return f"已开始 {abs(days)} 天", "past"
    if days == 0:
        return "今天开始", "today"
    return f"剩余 {days} 天", "future"


def _prepare_timeline_events(events):
    """清洗 API items，补齐模板所需字段并按开始日期排序。"""
    prepared = []
    for raw in events:
        if not isinstance(raw, dict):
            continue

        name = str(raw.get("name") or raw.get("title") or "未命名活动").strip()
        publisher = str(raw.get("title") or "").strip()
        start = _timeline_date(raw.get("time_start"))
        end = _timeline_date(raw.get("time_end"))
        remaining, remaining_class = _timeline_remaining(raw.get("time_start"))

        try:
            start_dt = datetime.datetime.strptime(start, "%Y.%m.%d")
            year = start_dt.strftime("%Y")
            month = start_dt.strftime("%Y.%m")
            sort_key = start_dt
        except (TypeError, ValueError):
            year = "日期待确认"
            month = "日期待确认"
            sort_key = datetime.datetime.max

        special_names = SPECIAL_EVENTS
        if isinstance(special_names, str):
            # 兼容配置项为逗号/换行分隔字符串的情况。
            special_names = [
                item.strip()
                for item in special_names.replace("，", ",").replace("\n", ",").split(",")
                if item.strip()
            ]
        is_special = name in (special_names or [])

        source_label = str(raw.get("source_label") or raw.get("source") or "").strip()
        source_key = source_label.casefold().replace(" ", "")
        if "deluxebot" in source_key:
            source_class = "source-deluxebot"
        elif "兽聚汇总" in source_label:
            source_class = "source-fusion"
        elif "梦想云" in source_label:
            source_class = "source-dreamcloud"
        else:
            source_class = ""

        prepared.append({
            "name": name,
            "publisher": publisher,
            "time_start": start,
            "time_end": end,
            "date_range": f"{start or '日期待确认'} — {end or '日期待确认'}",
            "address": str(raw.get("address") or "").strip(),
            "state": str(raw.get("state") or "").strip(),
            "time_surplus": str(raw.get("time_surplus") or "").strip(),
            "source_label": source_label,
            "source_class": source_class,
            "groups": "、".join(str(group) for group in raw.get("groups", []) if group) if isinstance(raw.get("groups"), list) else str(raw.get("groups") or "").strip(),
            "url": str(raw.get("url") or "").strip(),
            "brief": str(raw.get("brief") or "").strip(),
            "image": str(raw.get("image") or "").strip(),
            "remaining": remaining,
            "remaining_class": remaining_class,
            "is_special": is_special,
            "year": year,
            "month": month,
            "_sort_key": sort_key,
        })

    prepared.sort(key=lambda item: item["_sort_key"])
    grouped = []
    current_year = None
    current_month = None
    for event in prepared:
        if event["year"] != current_year:
            current_year = event["year"]
            current_month = None
            grouped.append({"year": current_year, "months": []})
        if event["month"] != current_month:
            current_month = event["month"]
            grouped[-1]["months"].append({"month": current_month, "events": []})
        grouped[-1]["months"][-1]["events"].append(event)

    return grouped, len(prepared)


async def _get_timeline_browser():
    """懒加载并复用 Playwright 浏览器，避免每次命令都重新启动浏览器。"""
    global _playwright_manager, _playwright_browser
    async with _playwright_lock:
        if _playwright_browser is not None and _playwright_browser.is_connected():
            return _playwright_browser

        if _playwright_manager is None:
            _playwright_manager = await async_playwright().start()
        _playwright_browser = await _playwright_manager.chromium.launch()
        return _playwright_browser


async def render_fursion_timeline_image(events: list[dict]) -> bytes:
    """
    使用 Jinja2 + HTML/CSS + Playwright 渲染 FurryFusion 时间轴。
    返回 PNG 字节，可直接传给 MessageSegment.image()。
    """
    groups, event_count = _prepare_timeline_events(events)
    template = _TEMPLATE_ENV.get_template("fursion_timeline.html")
    # 汇总本次实际出现的数据来源，去重并保持首次出现顺序。
    source_labels = []
    for year_group in groups:
        for month_group in year_group["months"]:
            for event in month_group["events"]:
                source = event.get("source_label", "").strip()
                if source and source not in source_labels:
                    source_labels.append(source)

    html = template.render(
        groups=groups,
        event_count=event_count,
        source_labels=source_labels,
        generated_at=datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
    )

    browser = await _get_timeline_browser()
    page = await browser.new_page(
        viewport={"width": 1080, "height": 900},
        device_scale_factor=1,
    )
    try:
        await page.set_content(html, wait_until="domcontentloaded", timeout=15000)
        await page.evaluate("document.fonts.ready")
        # 活动海报来自外部 URL，网络响应速度可能不稳定；按要求固定等待 60 秒。
        # CSS background-image 不会出现在 document.images 中，因此这里直接延时，
        # 避免图片尚未下载完成就截图发送。
        logger.info("FurryFusion 页面已加载，等待 60 秒确保活动背景图加载完成...")
        await asyncio.sleep(60)
        # 等待延时后的页面绘制完成。
        await page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
        return await page.screenshot(
            type="png",
            full_page=True,
            animations="disabled",
            timeout=30000,
        )
    finally:
        await page.close()


@handle_errors
async def get_fur_session():
    async with httpx.AsyncClient() as client:
        fur_session = await client.post("https://qqbot.fur-bot.com/api/v1/user/login",
                                        headers={"Content-Type": "application/json"},
                                        json={"account": username, "password": password,"login_token": token})
        if fur_session.status_code == 200 and fur_session.cookies.get("fur_session") and fur_session.json().get("ok"):
            handle_json(furryfusion_login_session, 'w', {"fur_session": fur_session.cookies.get("fur_session")})
            return {"fur_session": fur_session.cookies.get("fur_session")}
        else:
            logger.error(f"FurryFusion 登录失败，状态码：{fur_session.status_code}，响应内容：{fur_session.text}")
            raise LingHuiError("登录失败，请检查用户名和密码是否正确。\n调试信息已发送在终端。")