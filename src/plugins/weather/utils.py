import json
import os
import re
import jinja2

import httpx
from nonebot import logger
from nonebot_plugin_htmlrender import html_to_pic

from .check_file import typhoon_id_path
from src.plugins.utils import handle_errors,handle_json


@handle_errors
async def http_get(name:str,url: str, headers: dict):
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
# 实例化 template_env 对象
template_env = jinja2.Environment(loader=template_loader, enable_async=True)

async def _fetch_and_parse_typhoon_data() -> dict:
    """
    从中央气象台拉取数据、解析并路由出当前最优的台风目标数据(Dict)
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

    # 路由当前最新的台风：优先锁定 active，其次拿第一条最新的 stop
    target_typhoon = None
    for typhoon in all_typhoons:
        if typhoon["status"] == "active":
            target_typhoon = typhoon
            break
    if not target_typhoon:
        target_typhoon = all_typhoons[0]

    return target_typhoon

async def check_and_get_new_typhoon_card() -> bytes | None:
    """
    【定时任务专用】检查是否有新台风。如果有，渲染并返回图片字节流；如果没有，返回 None。
    """
    # 复用通用清洗层
    target_typhoon = await _fetch_and_parse_typhoon_data()

    current_typhoon_id = target_typhoon["id"]
    last_pushed_id = handle_json(typhoon_id_path, 'r', {}).get("last_pushed_id", 0)

    logger.info(f"[Typhoon Service] 当前最新台风ID: {current_typhoon_id}, 上次推送ID: {last_pushed_id}")

    # 🔍 核心对比逻辑
    if current_typhoon_id <= last_pushed_id:
        logger.info("[Typhoon Service] 🍃 未检测到新台风生成，本次订阅任务不执行出图推送。")
        return None

    logger.info(f"[Typhoon Service] 🚨 检测到新台风！名称: {target_typhoon['name_cn']}，开始渲染卡片...")

    # 执行 Jinja2 渲染与 Playwright 截图
    render_context = {"typhoon": target_typhoon}
    template = template_env.get_template("typhoon.html")
    rendered_html = await template.render_async(**render_context)

    img_bytes = await html_to_pic(
        html=rendered_html,
        viewport={"width": 600, "height": 450},
        wait=1000
    )

    # 成功生成图片后，更新本地缓存的 ID
    handle_json(typhoon_id_path, 'w', {"last_pushed_id": current_typhoon_id})
    return img_bytes


async def get_typhoon_card_image() -> bytes:
    """
    【主动查询专用】核心可复用函数：获取台风数据并生成卡片图片字节流
    :return: 渲染后的图片 bytes 数据
    """
    # 复用通用清洗层
    target_typhoon = await _fetch_and_parse_typhoon_data()

    render_context = {
        "typhoon": target_typhoon
    }

    # Jinja2 渲染
    try:
        template = template_env.get_template("typhoon.html")
        rendered_html = await template.render_async(**render_context)
    except Exception as e:
        logger.error(f"[Typhoon Service] Jinja2 模板渲染发生错误: {e}")
        raise e

    # Playwright 截图
    try:
        logger.info("[Typhoon Service] 正在调用 Playwright 进行图像渲染...")
        img_bytes = await html_to_pic(
            html=rendered_html,
            viewport={"width": 600, "height": 450}
        )
        return img_bytes
    except Exception as e:
        logger.error(f"[Typhoon Service] Playwright 截图失败: {e}")
        raise e