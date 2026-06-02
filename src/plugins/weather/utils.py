import json
import os
import re
import asyncio
from datetime import datetime, timedelta
import jinja2

import httpx
from nonebot import logger, get_bot
from nonebot_plugin_htmlrender import html_to_pic
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .check_file import typhoon_id_path
from .models import TyphoonSubscribe
# 从全局公共工具包导入
from src.plugins.utils import handle_errors, handle_json, batch_get

# 核心气象学代码中文动态映射表
GRADE_MAP = {
    "TD": "热带低压",
    "TS": "热带风暴",
    "STS": "强热带风暴",
    "TY": "台风",
    "STY": "强台风",
    "SuperTY": "超强台风"
}

WIND_MAP = {
    "30KTS": "七级风圈",
    "50KTS": "十级风圈",
    "64KTS": "十二级风圈"
}


# 🌟 核心修复：完璧归赵！保留给 weather.py 调用的底层 http_get，彻底解决包导入挂掉的问题
@handle_errors
async def http_get(name: str, url: str, headers: dict):
    """
    发送HTTP GET请求并返回响应对象。
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"未能正确请求{name} API。[HTTP {response.status_code}]")
        return response.json()


CURRENT_DIR = str(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "html_template")
template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
template_env = jinja2.Environment(loader=template_loader, enable_async=True)


async def _fetch_all_typhoons_detail() -> list[dict]:
    """
    并发拉取并解析当前气象台列表中的所有台风全量详细信息（支持多台风共存）
    """
    url = "https://typhoon.nmc.cn/weatherservice/typhoon/jsons/list_default"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        typhoon_resp = resp.text

    cleaned_text = typhoon_resp.strip()
    match = re.search(r'({.*})', cleaned_text, re.DOTALL)
    if not match:
        raise ValueError("台风数据格式异常，无法解析。")

    raw_data = json.loads(match.group(1).strip())
    typhoon_list_raw = raw_data.get("typhoonList", [])
    if not typhoon_list_raw:
        return []

    all_typhoons = []
    for t in typhoon_list_raw:
        all_typhoons.append({
            "id": str(t[0]),
            "name_en": t[1],
            "name_cn": t[2],
            "code_4digit": str(t[3]) if t[3] is not None else "0000",
            "seq_code": str(t[4]) if t[4] is not None else "",
            "meaning": t[6] or "暂无寓意数据",
            "status": t[7] if len(t) > 7 else "stop",
            "time_formatted": "暂无数据",
            "lng": "",
            "lat": "",
            "pressure": "",
            "speed": "",
            "movedirection": "暂无",
            "movespeed": "0",
            "grade_cn": "未知强度",
            "wind_circles": [],
            "forecasts": []
        })

    async def fetch_single_view(typhoon: dict):
        view_url = f"https://typhoon.nmc.cn/weatherservice/typhoon/jsons/view_{typhoon['id']}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                view_resp = await client.get(view_url)
                view_text = view_resp.text

            view_cleaned = view_text.strip()
            view_match = re.search(r'({.*})', view_cleaned, re.DOTALL)
            if view_match:
                view_data = json.loads(view_match.group(1).strip())
                typhoon_detail = view_data.get("typhoon", [])

                if typhoon_detail and len(typhoon_detail) > 8:
                    if len(typhoon_detail) > 7 and typhoon_detail[7]:
                        typhoon["status"] = typhoon_detail[7]

                    points = typhoon_detail[8]
                    if points and isinstance(points, list):
                        latest_point = points[-1]

                        time_str = str(latest_point[1]) if len(latest_point) > 1 else ""
                        time_formatted = "暂无数据"
                        if time_str and len(time_str) >= 10:
                            try:
                                utc_dt = datetime.strptime(time_str[:10], "%Y%m%d%H")
                                cst_dt = utc_dt + timedelta(hours=8)
                                time_formatted = cst_dt.strftime("%m月%d日 %H:%M")
                            except Exception as time_err:
                                logger.error(f"[Typhoon Service] 解析台风时间戳失败: {time_err}")

                        grade_code = str(latest_point[3]) if len(latest_point) > 3 else ""
                        typhoon.update({
                            "time_formatted": time_formatted,
                            "grade_cn": GRADE_MAP.get(grade_code, grade_code or "未知强度"),
                            "lng": str(latest_point[4]) if len(latest_point) > 4 else "",
                            "lat": str(latest_point[5]) if len(latest_point) > 5 else "",
                            "pressure": str(latest_point[6]) if len(latest_point) > 6 else "",
                            "speed": str(latest_point[7]) if len(latest_point) > 7 else "",
                            "movedirection": str(latest_point[8]) if len(latest_point) > 8 and latest_point[
                                8] else "暂无",
                            "movespeed": str(latest_point[9]) if len(latest_point) > 9 and latest_point[
                                9] is not None else "0"
                        })

                        parsed_circles = []
                        if len(latest_point) > 10 and isinstance(latest_point[10], list):
                            for wc in latest_point[10]:
                                if len(wc) >= 5:
                                    parsed_circles.append({
                                        "name": WIND_MAP.get(wc[0], wc[0]),
                                        "ne": wc[1], "se": wc[2], "sw": wc[3], "nw": wc[4]
                                    })
                        typhoon["wind_circles"] = parsed_circles

                        parsed_forecasts = []
                        if len(latest_point) > 11 and isinstance(latest_point[11], dict):
                            babj_list = latest_point[11].get("BABJ", [])
                            for f in babj_list:
                                if len(f) >= 8:
                                    parsed_forecasts.append({
                                        "hour": str(f[0]), "lng": str(f[2]), "lat": str(f[3]),
                                        "pressure": str(f[4]), "speed": str(f[5]), "grade_cn": GRADE_MAP.get(f[7], f[7])
                                    })
                        typhoon["forecasts"] = parsed_forecasts
        except Exception as e:
            logger.error(f"[Typhoon Service] 请求台风 view_{typhoon['id']} 失败: {e}")

    await asyncio.gather(*(fetch_single_view(t) for t in all_typhoons))
    return all_typhoons


async def render_typhoon_card(typhoon: dict) -> bytes:
    render_context = {"typhoon": typhoon}
    template = template_env.get_template("typhoon.html")
    rendered_html = await template.render_async(**render_context)
    return await html_to_pic(
        html=rendered_html,
        viewport={"width": 600, "height": 800}
    )


async def get_current_typhoon_cards() -> list[bytes]:
    all_typhoons = await _fetch_all_typhoons_detail()
    if not all_typhoons:
        return []

    active_list = [t for t in all_typhoons if t["status"] in ["start", "active"]]
    targets = active_list if active_list else [all_typhoons[0]]

    cards = []
    for t in targets:
        cards.append(await render_typhoon_card(t))
    return cards


async def run_daily_typhoon_push():
    """
    【定时任务主控核心】每天早上 7:00 自动触发推送
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    history = handle_json(typhoon_id_path, 'r', {})

    if not isinstance(history, dict) or "last_pushed_id" in history:
        history = {}

    all_typhoons = await _fetch_all_typhoons_detail()
    typhoons_to_push = []

    for t in all_typhoons:
        t_id = str(t["id"])
        status = t["status"]

        record = history.get(t_id, {"last_pushed_date": "", "last_status": ""})
        should_push = False

        if status in ["start", "active"]:
            if record["last_pushed_date"] != today_str:
                should_push = True
                record["last_pushed_date"] = today_str
                record["last_status"] = "start"
        elif status == "stop":
            if record["last_status"] == "start":
                should_push = True
                record["last_pushed_date"] = today_str
                record["last_status"] = "stop"

        if should_push:
            typhoons_to_push.append(t)
            history[t_id] = record

    if not typhoons_to_push:
        return

    card_images = []
    for t in typhoons_to_push:
        img_bytes = await render_typhoon_card(t)
        card_images.append(img_bytes)

    try:
        bot = get_bot()
    except ValueError:
        logger.error("[Typhoon Service] 未找到有效 Bot 实例，取消定时推送。")
        return

    async with get_session() as session:
        stmt = select(TyphoonSubscribe).where(TyphoonSubscribe.enable == True)
        result = await session.scalars(stmt)
        subscribed_groups = result.all()

    if not subscribed_groups:
        return

    # 🌟 修正：定时器推送同步使用正确的 batch_get 节点打包逻辑
    picture_list = [await batch_get("", img, 3806419216, "凌辉Bot 台风推送") for img in card_images]

    # 群发投递
    for group in subscribed_groups:
        try:
            # 🌟 修正：调用底层 OneBot API 发送合并消息包
            await bot.call_api("send_group_forward_msg", group_id=group.group_id, message=picture_list, time_noend=True)
            logger.info(f"[Typhoon Service] 成功向群 {group.group_id} 推送台风合并订阅包。")
        except Exception as e:
            logger.error(f"[Typhoon Service] 向群 {group.group_id} 发送订阅失败: {e}")

    handle_json(typhoon_id_path, 'w', history)