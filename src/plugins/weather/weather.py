import os
import time
import jinja2
import jwt

import asyncio
from nonebot import on_message, logger, get_driver
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot_plugin_htmlrender import html_to_pic
from nonebot.exception import FinishedException
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
import re

from .commands import weather_check, weather_forecast
from src.plugins.utils import handle_errors
from .utils import http_get

try:
    api_key = get_driver().config.weather_api_key
    project_id = get_driver().config.weather_project_id
    expire_time = get_driver().config.weather_expired_time
    jwt_id = get_driver().config.weather_jwt_id
    base_url = get_driver().config.weather_api_baseurl
except AttributeError:
    api_key, project_id, expire_time = None, 0, 0
    logger.warning("未读取到天气查询API，天气查询功能将不可用。")


CURRENT_DIR = str(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "html_template")
template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
template_env = jinja2.Environment(loader=template_loader, enable_async=True)

# ===== 常量 =====
CITY_SELECTION_TIMEOUT = 5   # 城市选择超时（秒）
MAX_PENDING_TIMEOUT = 300      # 待选记录最大保留（秒），超过自动清理
VALID_FORECAST_DAYS = {3, 7, 10, 15, 30}
DEFAULT_FORECAST_DAYS = 7

# ===== 多城市选择状态管理 =====
# key: f"{group_id}_{user_id}"  value: {"locations", "time", "type", "days"}
_pending_selections: dict[str, dict] = {}


def _selection_key(event: GroupMessageEvent) -> str:
    return f"{event.group_id}_{event.user_id}"


def _has_pending_numeric_selection(event: GroupMessageEvent) -> bool:
    """Rule: 用户有待处理的城市选择 且 消息为纯数字"""
    key = f"{event.group_id}_{event.user_id}"
    if key not in _pending_selections:
        return False
    text = event.get_plaintext().strip()
    if not text.isdigit():
        return False
    # 超过最大保留时间自动清理，避免内存泄漏
    if time.time() - _pending_selections[key]["time"] > MAX_PENDING_TIMEOUT:
        del _pending_selections[key]
        return False
    return True


# 城市选择响应 matcher（仅当 rule 命中时触发）
city_response = on_message(rule=_has_pending_numeric_selection, priority=5, block=True)


# ===== 工具函数 =====

async def create_jwt() -> dict:
    current_time = int(time.time())
    headers = {
        "alg": "EdDSA",
        "kid": str(jwt_id)
    }
    payload = {
        "sub": str(project_id),
        "iat": current_time - 30,
        "exp": current_time + expire_time
    }
    token = jwt.encode(
        payload=payload,
        key=api_key,
        algorithm="Ed25519",
        headers=headers
    )
    headers = {
        "Authorization": f"Bearer {token}"
    }
    return headers

@handle_errors
async def lookup_city(city: str) -> list[dict]:
    """查询城市列表。API 错误时抛出 ValueError。"""
    headers = await create_jwt()
    data = await http_get(
        "LocationID", f"{base_url}/geo/v2/city/lookup?location={city}", headers
    )
    if data["code"] != "200":
        raise ValueError(
            f"已经正确请求了API，但API返回了错误: "
            f"{data.get('info', '未知错误')}[Status: {data['code']}]"
        )
    return data["location"]


def build_city_list_message(locations: list[dict]) -> str:
    msg = "获取到多个城市信息，请回复编号选择：\n\n"
    for i, loc in enumerate(locations, 1):
        msg += f"{i}. {loc['country']} {loc['adm1']} {loc['adm2']} {loc['name']}\n"
    msg += f"\n⚠️ 超时{CITY_SELECTION_TIMEOUT}秒后将自动选择第1个"
    return msg


def parse_forecast_args(text: str) -> tuple[str, int, bool]:
    """
    解析天气预报参数，格式: "城市名 [天数]"
    返回: (城市名, 天数, 天数参数是否有效)
    """
    parts = text.strip().split()
    city = parts[0] if parts else ""
    days = DEFAULT_FORECAST_DAYS
    valid_days = True

    if len(parts) > 1:
        days_str = parts[1].lower().rstrip("d天日")
        try:
            days = int(days_str)
            if days not in VALID_FORECAST_DAYS:
                days = DEFAULT_FORECAST_DAYS
                valid_days = False
        except ValueError:
            days = DEFAULT_FORECAST_DAYS
            valid_days = False

    return city, days, valid_days


def get_weather_assets(icon_code: str):
    try:
        code = int(icon_code)
    except ValueError:
        return "✨", "linear-gradient(135deg, #FF8C42, #FF3C5F)"
    if code in [100, 150]:
        return "☀️", "linear-gradient(135deg, #FF8C42, #FF3C5F)"
    elif code in [101, 102, 103, 151, 152, 153]:
        return "⛅", "linear-gradient(135deg, #11998E, #38EF7D)"
    elif code == 104:
        return "☁️", "linear-gradient(135deg, #757F9A, #D7DDE8)"
    elif 300 <= code <= 399:
        return "🌧️", "linear-gradient(135deg, #3A7BD5, #203A43)"
    elif 400 <= code <= 499:
        return "❄️", "linear-gradient(135deg, #E0EAFC, #CFDEF3)"
    elif 500 <= code <= 515:
        return "🌫️", "linear-gradient(135deg, #606C88, #3F2B96)"
    return "✨", "linear-gradient(135deg, #FF8C42, #FF3C5F)"


def get_moon_emoji(phase_name: str):
    moons = {
        "新月": "🌑", "蛾眉月": "🌒", "上弦月": "🌓", "盈凸月": "🌔",
        "满月": "🌕", "亏凸月": "🌖", "下弦月": "🌗", "残月": "🌘"
    }
    return moons.get(phase_name, "🌙")


# ===== 天气查询核心逻辑 =====

async def process_weather_check(
        matcher: Matcher, event: GroupMessageEvent, bot: Bot, location: dict
):
    """处理天气查询核心逻辑（从原 handler 中提取）"""
    location_id = location['id']
    name = location['name']
    adm1 = location['adm1']
    adm2 = location['adm2']
    country = location['country']
    lon = f"{float(location['lon']):.2f}"
    lat = f"{float(location['lat']):.2f}"
    if name == adm2:
        if re.search(r'[\u4e00-\u9fa5]', country):
            name = "市"

    headers = await create_jwt()

    weather_data = await http_get("weather", f"{base_url}/v7/weather/now?location={location_id}", headers)
    if weather_data["code"] != "200":
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"已经正确请求了API，但API返回了错误: "
            f"{weather_data.get('info', '未知错误')}[Status: {weather_data['code']}]"
        )
    qweather_now = weather_data.get("now", {})

    AQI_data = await http_get("AQI", f"{base_url}/airquality/v1/current/{lat}/{lon}", headers)
    aqi_display = "--"
    aqi_color = None
    primary_pollutant = "无"
    aqi_effect = ""
    pollutants_list = []

    if AQI_data and "indexes" in AQI_data:
        target_index = AQI_data["indexes"][0]
        aqi_display = f"{target_index.get('aqiDisplay', '--')} {target_index.get('category', '')}"
        aqi_color = target_index.get("color")
        aqi_effect = target_index.get("health", {}).get("effect", "")
        if target_index.get("primaryPollutant"):
            primary_pollutant = target_index["primaryPollutant"].get("name", "无")
        for p in AQI_data.get("pollutants", []):
            pollutants_list.append({
                "name": p.get("name"),
                "value": p.get("concentration", {}).get("value", "--"),
                "unit": p.get("concentration", {}).get("unit", "")
            })

    alert = await http_get("alert", f"{base_url}/weatheralert/v1/current/{lat}/{lon}", headers)
    alert_list = []
    if alert["metadata"]['zeroResult']:
        alert_list.append({
            "text": "当前地区未发布预警信息",
            "time": "",
            "bg_color": "rgba(255, 255, 255, 0.15)",
            "border_color": "rgba(255, 255, 255, 0.3)"
        })
    else:
        for a in alert.get("alerts", []):
            color_data = a.get("color", {})
            r = color_data.get("red", 255)
            g = color_data.get("green", 77)
            b = color_data.get("blue", 79)
            issued_time = a.get("issuedTime", "")
            time_display = issued_time[11:16] if len(issued_time) >= 16 else ""
            alert_list.append({
                "text": a.get("headline", "气象预警"),
                "time": time_display,
                "bg_color": f"rgba({r}, {g}, {b}, 0.25)",
                "border_color": f"rgb({r}, {g}, {b})"
            })

    rendered_html = ""
    try:
        template = template_env.get_template("weather.html")
        render_context = {
            "province": f"{country} {adm1} {adm2}",
            "city": name,
            "obsTime": qweather_now.get("obsTime", ""),
            "weather": qweather_now.get("text", ""),
            "temperature": qweather_now.get("temp", "--"),
            "weather_icon": qweather_now.get("icon", ""),
            "feelsLike": qweather_now.get("feelsLike", "--"),
            "precip": qweather_now.get("precip", "0.0"),
            "cloud": qweather_now.get("cloud", ""),
            "vis": qweather_now.get("vis", ""),
            "aqi": aqi_display,
            "aqi_color": aqi_color,
            "primary_pollutant": primary_pollutant,
            "aqi_effect": aqi_effect,
            "pollutants": pollutants_list,
            "humidity": qweather_now.get("humidity", "0"),
            "pressure": qweather_now.get("pressure", ""),
            "dew": qweather_now.get("dew", ""),
            "windDir": qweather_now.get("windDir", ""),
            "wind360": qweather_now.get("wind360", "0"),
            "windScale": qweather_now.get("windScale", ""),
            "windSpeed": qweather_now.get("windSpeed", ""),
            "updateTime": weather_data.get("updateTime", ""),
            "code": weather_data.get("code", "200"),
            "fxLink": weather_data.get("fxLink", ""),
            "refer_sources": ", ".join(weather_data.get("refer", {}).get("sources", ["QWeather"])),
            "refer_license": ", ".join(weather_data.get("refer", {}).get("license", ["License"])),
            "warnings": alert_list
        }
        rendered_html = await template.render_async(**render_context)
        logger.debug(f"天气卡片模板渲染成功！体积: {len(rendered_html)} 字节")
    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"Jinja2 模板渲染发生错误: {e}")
        await matcher.finish(MessageSegment.reply(event.message_id) + f"模板渲染发生局部错误: {e}")

    try:
        img_bytes = await html_to_pic(html=rendered_html, viewport={"width": 400, "height": 600})
        await matcher.finish(MessageSegment.image(img_bytes))
    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"Playwright 截图失败: {e}")
        await matcher.finish(MessageSegment.reply(event.message_id) + f"卡片截图失败，错误原因: {e}")


# ===== 天气预报核心逻辑 =====

async def process_weather_forecast(
        matcher: Matcher, event: GroupMessageEvent, bot: Bot, location: dict, days: int
):
    """处理天气预报核心逻辑（从原 handler 中提取）"""
    location_id = location['id']
    name = location['name']

    headers = await create_jwt()

    forecast_data = await http_get(
        "forecast", f"{base_url}/v7/weather/{days}d?location={location_id}", headers
    )
    if forecast_data["code"] != "200":
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"天气预报API返回错误[Status: {forecast_data['code']}]"
        )

    daily_list = forecast_data.get("daily", [])
    if not daily_list:
        await matcher.finish("未获取到有效的预报天气明细数据。")

    try:
        template = template_env.get_template("weather_vertical.html")
    except Exception as e:
        logger.error(f"加载 weather_vertical.html 模板失败: {e}")
        await matcher.finish("模板加载失败，请确保 html_template 目录下存在 weather_vertical.html。")

    async def render_single_day_card(day_item, index):
        date_labels = ["今天", "明天", "后天", "大后天", "第五天", "第六天", "第七天"]
        label = date_labels[index] if index < len(date_labels) else f"第{index + 1}天"

        day_emoji, bg_grad = get_weather_assets(day_item.get("iconDay", "100"))
        moon_emoji = get_moon_emoji(day_item.get("moonPhase", ""))

        ctx = {
            "city": name,
            "date_label": label,
            "updateTime": forecast_data.get("updateTime", ""),
            "day_emoji": day_emoji,
            "moon_emoji": moon_emoji,
            "bg_gradient": bg_grad,
            "daily": day_item,
            "refer_sources": ", ".join(forecast_data.get("refer", {}).get("sources", ["QWeather"])),
            "refer_license": ", ".join(forecast_data.get("refer", {}).get("license", ["License"])),
            "fxLink": forecast_data.get("fxLink", "")
        }

        html_str = await template.render_async(**ctx)
        img = await html_to_pic(html=html_str, viewport={"width": 400, "height": 720})
        return img

    img_bytes_list = []
    try:
        tasks = [render_single_day_card(day, idx) for idx, day in enumerate(daily_list)]
        img_bytes_list = await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"预报多卡片高并发截图失败: {e}")
        await matcher.finish(MessageSegment.reply(event.message_id) + f"预报多面板并发渲染失败: {e}")

    forward_nodes = []
    for img_bytes in img_bytes_list:
        forward_nodes.append(
            MessageSegment.node_custom(
                user_id=event.self_id,
                nickname="LingHuiBot",
                content=f"{MessageSegment.image(img_bytes)}"
            )
        )

    try:
        await bot.send_group_forward_msg(group_id=event.group_id, messages=forward_nodes)
    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"发送天气预报合并转发消息失败: {e}")
        await matcher.finish("发送合并转发天气流失败，请检查机器人发群合并转发的相关权限。")


# ===== 命令处理器 =====

@weather_check.handle()
@handle_errors
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        args: Message = CommandArg()
):
    if not api_key:
        await matcher.finish("天气查询功能未配置，请联系管理员。")

    city = args.extract_plain_text().strip()
    if not city:
        await matcher.finish("请提供要查询的城市名称，例如：天气查询 北京")

    try:
        locations = await lookup_city(city)
    except ValueError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + str(e))

    if not locations:
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到匹配的城市，请检查城市名称")

    if len(locations) == 1:
        await process_weather_check(matcher, event, bot, locations[0])
    else:
        key = _selection_key(event)
        _pending_selections[key] = {
            "locations": locations,
            "time": time.time(),
            "type": "check"
        }
        msg = build_city_list_message(locations)
        await matcher.finish(msg)


@weather_forecast.handle()
@handle_errors
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        args: Message = CommandArg()
):
    if not api_key:
        await matcher.finish("天气预报功能未配置，请联系管理员。")

    raw_text = args.extract_plain_text().strip()
    if not raw_text:
        await matcher.finish("请提供要查询的城市名称，例如：天气预报 北京 或 天气预报 北京 3")

    city, days, valid_days = parse_forecast_args(raw_text)
    if not city:
        await matcher.finish("请提供要查询的城市名称，例如：天气预报 北京 或 天气预报 北京 3")

    # 天数参数无效时提示
    if not valid_days and len(raw_text.strip().split()) > 1:
        await bot.send(
            event,
            f"不支持该天数预报，已自动使用{days}天预报"
            f"（支持天数: {', '.join(map(str, sorted(VALID_FORECAST_DAYS)))}）"
        )

    try:
        locations = await lookup_city(city)
    except ValueError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + str(e))

    if not locations:
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到匹配的城市，请检查城市名称")

    if len(locations) == 1:
        await process_weather_forecast(matcher, event, bot, locations[0], days)
    else:
        key = _selection_key(event)
        _pending_selections[key] = {
            "locations": locations,
            "time": time.time(),
            "type": "forecast",
            "days": days
        }
        msg = build_city_list_message(locations)
        await matcher.finish(msg)


# ===== 城市选择响应处理器 =====

@city_response.handle()
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
):
    key = _selection_key(event)
    pending = _pending_selections.get(key)
    if not pending:
        return

    locations = pending["locations"]
    choice_text = event.get_plaintext().strip()

    # 检查超时
    if time.time() - pending["time"] > CITY_SELECTION_TIMEOUT:
        location = locations[0]
        del _pending_selections[key]
        await bot.send(
            event,
            f"选择超时，已自动使用第1个城市："
            f"{location['adm1']} {location['adm2']} {location['name']}"
        )
    else:
        choice = int(choice_text)
        if choice < 1 or choice > len(locations):
            del _pending_selections[key]
            await matcher.finish("输入的编号无效，请重新发送指令查询")
        location = locations[choice - 1]
        del _pending_selections[key]

    # 根据类型调用对应的处理函数
    selection_type = pending["type"]
    if selection_type == "check":
        await process_weather_check(matcher, event, bot, location)
    elif selection_type == "forecast":
        days = pending.get("days", DEFAULT_FORECAST_DAYS)
        await process_weather_forecast(matcher, event, bot, location, days)