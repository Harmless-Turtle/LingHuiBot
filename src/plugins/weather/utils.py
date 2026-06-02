import json
import os
import re
from datetime import datetime, timedelta
import jinja2

import httpx
from nonebot import logger
from nonebot_plugin_htmlrender import html_to_pic

from .check_file import typhoon_id_path
from src.plugins.utils import handle_errors, handle_json

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


@handle_errors
async def http_get(name: str, url: str, headers: dict):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"未能正确请求{name} API。[HTTP {response.status_code}]")
        return response.json()


CURRENT_DIR = str(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "html_template")
template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
template_env = jinja2.Environment(loader=template_loader, enable_async=True)


async def _fetch_and_parse_typhoon_data() -> dict:
    """
    拉取数据、解析并路由出当前最优的台风目标数据，全量链式融合 view 接口深度提取实时轨迹、风圈、预报
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
        raise ValueError("当前中央气象台未发布任何台风监控数据。")

    all_typhoons = []
    for t in typhoon_list_raw:
        all_typhoons.append({
            "id": t[0],
            "name_en": t[1],
            "name_cn": t[2],
            "code_4digit": str(t[3]) if t[3] is not None else "0000",
            "seq_code": str(t[4]) if t[4] is not None else "",
            "meaning": t[6] or "暂无寓意数据",
            "status": t[7] if len(t) > 7 else "stop"
        })

    target_typhoon = None
    for typhoon in all_typhoons:
        if typhoon["status"] == "active":
            target_typhoon = typhoon
            break
    if not target_typhoon:
        target_typhoon = all_typhoons[0]

    # 初始化全量详细信息默认值
    target_typhoon.update({
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

    # 链式融合 view 接口
    view_url = f"https://typhoon.nmc.cn/weatherservice/typhoon/jsons/view_{target_typhoon['id']}"
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
                    target_typhoon["status"] = typhoon_detail[7]

                points = typhoon_detail[8]
                if points and isinstance(points, list):
                    latest_point = points[-1]

                    # 🕒 核心时区转换：解析 API 的 UTC 时间串并安全转换为北京时间 (+8h)
                    time_str = str(latest_point[1]) if len(latest_point) > 1 else ""
                    time_formatted = "暂无数据"
                    if time_str and len(time_str) >= 10:
                        try:
                            # 提取 YYYYMMDDHH 部分进行转换
                            utc_dt = datetime.strptime(time_str[:10], "%Y%m%d%H")
                            # 加上 8 小时跨向北京时间，datetime 会自动处理好跨天、跨月进位
                            cst_dt = utc_dt + timedelta(hours=8)
                            time_formatted = cst_dt.strftime("%m月%d日 %H:%M")
                        except Exception as time_err:
                            logger.error(f"[Typhoon Service] 解析台风 API 时间戳失败: {time_err}")

                    grade_code = str(latest_point[3]) if len(latest_point) > 3 else ""
                    target_typhoon.update({
                        "time_formatted": time_formatted,
                        "grade_cn": GRADE_MAP.get(grade_code, grade_code or "未知强度"),
                        "lng": str(latest_point[4]) if len(latest_point) > 4 else "",
                        "lat": str(latest_point[5]) if len(latest_point) > 5 else "",
                        "pressure": str(latest_point[6]) if len(latest_point) > 6 else "",
                        "speed": str(latest_point[7]) if len(latest_point) > 7 else "",
                        "movedirection": str(latest_point[8]) if len(latest_point) > 8 and latest_point[8] else "暂无",
                        "movespeed": str(latest_point[9]) if len(latest_point) > 9 and latest_point[
                            9] is not None else "0"
                    })

                    # 动态提取：风圈半径数据解析
                    parsed_circles = []
                    if len(latest_point) > 10 and isinstance(latest_point[10], list):
                        for wc in latest_point[10]:
                            if len(wc) >= 5:
                                parsed_circles.append({
                                    "name": WIND_MAP.get(wc[0], wc[0]),
                                    "ne": wc[1],
                                    "se": wc[2],
                                    "sw": wc[3],
                                    "nw": wc[4]
                                })
                    target_typhoon["wind_circles"] = parsed_circles

                    # 动态提取：未来路径主客观预报解析
                    parsed_forecasts = []
                    if len(latest_point) > 11 and isinstance(latest_point[11], dict):
                        babj_list = latest_point[11].get("BABJ", [])
                        for f in babj_list:
                            if len(f) >= 8:
                                parsed_forecasts.append({
                                    "hour": str(f[0]),
                                    "lng": str(f[2]),
                                    "lat": str(f[3]),
                                    "pressure": str(f[4]),
                                    "speed": str(f[5]),
                                    "grade_cn": GRADE_MAP.get(f[7], f[7])
                                })
                    target_typhoon["forecasts"] = parsed_forecasts

    except Exception as e:
        logger.error(f"[Typhoon Service] 链式请求/解析台风 view 详细数据失败: {e}")

    return target_typhoon


async def check_and_get_new_typhoon_card() -> bytes | None:
    target_typhoon = await _fetch_and_parse_typhoon_data()
    current_typhoon_id = target_typhoon["id"]
    last_pushed_id = handle_json(typhoon_id_path, 'r', {}).get("last_pushed_id", 0)

    if current_typhoon_id <= last_pushed_id:
        return None

    render_context = {"typhoon": target_typhoon}
    template = template_env.get_template("typhoon.html")
    rendered_html = await template.render_async(**render_context)

    img_bytes = await html_to_pic(
        html=rendered_html,
        viewport={"width": 600, "height": 800},
        wait=1000
    )
    handle_json(typhoon_id_path, 'w', {"last_pushed_id": current_typhoon_id})
    return img_bytes


async def get_typhoon_card_image() -> bytes:
    target_typhoon = await _fetch_and_parse_typhoon_data()
    render_context = {"typhoon": target_typhoon}

    try:
        template = template_env.get_template("typhoon.html")
        rendered_html = await template.render_async(**render_context)
        img_bytes = await html_to_pic(
            html=rendered_html,
            viewport={"width": 600, "height": 800}
        )
        return img_bytes
    except Exception as e:
        logger.error(f"[Typhoon Service] 渲染或截图失败: {e}")
        raise e