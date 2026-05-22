import os
import time
import jinja2
import jwt

import asyncio
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot_plugin_htmlrender import html_to_pic
from nonebot.exception import FinishedException
from nonebot.internal.matcher import Matcher
from nonebot import logger, get_driver
from nonebot.params import CommandArg
import re

from .commands import weather_check,weather_forecast
from src.plugins.utils import handle_errors
from .utils import http_get

try:
    api_key = get_driver().config.weather_api_key
    project_id = get_driver().config.weather_project_id
    expire_time = get_driver().config.weather_expired_time
    jwt_id = get_driver().config.weather_jwt_id
    base_url = get_driver().config.weather_api_baseurl
except AttributeError:
    api_key,project_id,expire_time = None,0,0
    logger.warning("未读取到高德地图天气查询API，天气查询功能将不可用。")


CURRENT_DIR = str(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "html_template")
# 创建文件系统加载器，告诉 Jinja2 去哪里找 HTML 模板文件
template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
# 实例化 template_env 对象
template_env = jinja2.Environment(loader=template_loader, enable_async=True)

async def create_jwt() -> dict:
# 1. 构建 JWT 鉴权载荷（与实时天气一致）
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


@weather_check.handle()
@handle_errors
async def _(
        matcher:Matcher,
        event:GroupMessageEvent,
        bot: Bot,
        args:Message = CommandArg()
):
    if not api_key:
        await matcher.finish("天气查询功能未配置，请联系管理员。")

    city = args.extract_plain_text().strip()
    if not city:
        await matcher.finish("请提供要查询的城市名称，例如：天气查询 北京")
    headers = await create_jwt()
    # 异步请求locationID API获取欲查找城市的LocationID
    location_data_normal = await http_get("LocationID",f"{base_url}/geo/v2/city/lookup?location={city}", headers)
    # 排除HTTP请求成功但API返回错误
    if location_data_normal["code"] != "200":
        await matcher.finish(MessageSegment.reply(event.message_id)+f"已经正确请求了API，但API返回了错误: {location_data_normal.get('info', '未知错误')}[Status: {location_data_normal['code']}]")
    # 发送提示信息：告诉用户本次使用模糊查询
    location_data = location_data_normal['location'][0]
    if len(location_data_normal['location'])>1:
        await bot.send(event,f"获取到了多个城市信息，将自动使用第1位城市信息查询：\n"
                             f"国家：{location_data['country']}\n"
                             f"上级行政区划：{location_data['adm1']}\n"
                             f"所属一级行政区:{location_data['adm2']}\n"
                             f"查询名称：{location_data['name']}\n")

    # 获取LocationID等信息
    location_id = location_data['id']
    name = location_data['name']
    adm1 = location_data['adm1']
    adm2 = location_data['adm2']
    country = location_data['country']
    lon = f"{float(location_data['lon']):.2f}"
    lat = f"{float(location_data['lat']):.2f}"
    if name == adm2:
        if re.search(r'[\u4e00-\u9fa5]', country):
            name = "市"
    # 异步请求天气API获取天气信息
    weather_data = await http_get("weather",f"{base_url}/v7/weather/now?location={location_id}", headers)
    if weather_data["code"] != "200":
        await matcher.finish(MessageSegment.reply(event.message_id)+f"已经正确请求了API，但API返回了错误: {weather_data.get('info', '未知错误')}[Status: {weather_data['code']}]")
    qweather_now = weather_data.get("now", {})
    # 异步请求空气质量API
    AQI_data = await http_get("AQI",f"{base_url}/airquality/v1/current/{lat}/{lon}", headers)
    aqi_display = "--"
    aqi_color = None
    primary_pollutant = "无"
    aqi_effect = ""
    pollutants_list = []

    if AQI_data and "indexes" in AQI_data:
        # 提取首位空气质量标准指数
        target_index = AQI_data["indexes"][0]
        aqi_display = f"{target_index.get('aqiDisplay', '--')} {target_index.get('category', '')}"
        aqi_color = target_index.get("color")
        aqi_effect = target_index.get("health", {}).get("effect", "")
        if target_index.get("primaryPollutant"):
            primary_pollutant = target_index["primaryPollutant"].get("name", "无")

        # 循环清洗污染物浓度
        for p in AQI_data.get("pollutants", []):
            pollutants_list.append({
                "name": p.get("name"),
                "value": p.get("concentration", {}).get("value", "--"),
                "unit": p.get("concentration", {}).get("unit", "")
            })
    # 异步请求预警API
    alert = await http_get("alert",f"{base_url}/weatheralert/v1/current/{lat}/{lon}",headers)
    alert_list = []
    if alert["metadata"]['zeroResult']:
        alert_list.append({
            "text": "当前地区未发布预警信息",
            "time": "",
            "bg_color": "rgba(255, 255, 255, 0.15)",  # 轻微白色半透明，融入背景
            "border_color": "rgba(255, 255, 255, 0.3)"  # 淡淡的白边
        })
    else:
        # 存在预警，遍历提取核心属性
        for a in alert.get("alerts", []):
            # 提取颜色，用于给前端预警条做动态背景色
            color_data = a.get("color", {})
            r = color_data.get("red", 255)
            g = color_data.get("green", 77)
            b = color_data.get("blue", 79)

            # 提取格式化时间 (例如 11:19)
            issued_time = a.get("issuedTime", "")
            time_display = issued_time[11:16] if len(issued_time) >= 16 else ""

            alert_list.append({
                "text": a.get("headline", "气象预警"),
                "time": time_display,
                # 动态把 API 返回的 RGBA 调成半透明背景，体验极为高级
                "bg_color": f"rgba({r}, {g}, {b}, 0.25)",
                "border_color": f"rgb({r}, {g}, {b})"
            })
    # 处理模板
    rendered_html = ""
    try:
        # 加载HTML模板
        template = template_env.get_template("weather.html")

        # 准备传入 HTML 参数
        render_context = {
            # 顶部和核心区
            "province": f"{country} {adm1} {adm2}",
            "city": name,
            "obsTime": qweather_now.get("obsTime", ""),
            "weather": qweather_now.get("text", ""),
            "temperature": qweather_now.get("temp", "--"),
            "weather_icon": qweather_now.get("icon", ""),
            "feelsLike": qweather_now.get("feelsLike", "--"),

            # 次核心面板 & 空气质量扩展
            "precip": qweather_now.get("precip", "0.0"),
            "cloud": qweather_now.get("cloud", ""),
            "vis": qweather_now.get("vis", ""),

            # 传入空气质量核心数据
            "aqi": aqi_display,  # 文本展示如："52 良"
            "aqi_color": aqi_color,  # RGBA 变色字典
            "primary_pollutant": primary_pollutant,  # 首要污染物
            "aqi_effect": aqi_effect,  # 健康指导意见
            "pollutants": pollutants_list,  # 5大污染物循环列表

            # 六宫格气象网格
            "humidity": qweather_now.get("humidity", "0"),
            "pressure": qweather_now.get("pressure", ""),
            "dew": qweather_now.get("dew", ""),
            "windDir": qweather_now.get("windDir", ""),
            "wind360": qweather_now.get("wind360", "0"),
            "windScale": qweather_now.get("windScale", ""),
            "windSpeed": qweather_now.get("windSpeed", ""),

            # 页脚技术元数据
            "updateTime": weather_data.get("updateTime", ""),
            "code": weather_data.get("code", "200"),
            "fxLink": weather_data.get("fxLink", ""),
            "refer_sources": ", ".join(weather_data.get("refer", {}).get("sources", ["QWeather"])),
            "refer_license": ", ".join(weather_data.get("refer", {}).get("license", ["License"])),

            # 预警流占位符
            "warnings": alert_list
        }

        # 3. 执行异步渲染
        rendered_html = await template.render_async(**render_context)

        logger.debug(f"天气卡片模板渲染成功！体积: {len(rendered_html)} 字节")

    except FinishedException:
        pass

    except Exception as e:
        logger.error(f"Jinja2 模板渲染发生错误: {e}")
        await matcher.finish(MessageSegment.reply(event.message_id) + f"模板渲染发生局部错误: {e}")
    try:
        # 直接将渲染好的 HTML 字符串转换为图片字节流
        img_bytes = await html_to_pic(
            html=rendered_html,
            viewport={"width": 400, "height": 600}
        )

        await matcher.finish(MessageSegment.image(img_bytes))

    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"Playwright 截图失败: {e}")
        await matcher.finish(MessageSegment.reply(event.message_id) + f"卡片截图失败，错误原因: {e}")


@weather_forecast.handle()
@handle_errors
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        args: Message = CommandArg()
):
    img_bytes_list = []
    if not api_key:
        await matcher.finish("天气预报功能未配置，请联系管理员。")

    city = args.extract_plain_text().strip()
    if not city:
        await matcher.finish("请提供要查询的城市名称，例如：天气预报 北京")
    headers = await create_jwt()
    # 2. 异步请求 LocationID API 获取城市 ID
    location_data_normal = await http_get("LocationID", f"{base_url}/geo/v2/city/lookup?location={city}", headers)
    if location_data_normal["code"] != "200":
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"城市查询失败[Status: {location_data_normal['code']}]")

    location_data = location_data_normal['location'][0]
    if len(location_data_normal['location']) > 1:
        await bot.send(event, f"获取到了多个城市信息，将自动使用第1位城市信息查询预测：\n"
                              f"级划：{location_data['adm1']} {location_data['adm2']} -> {location_data['name']}\n")

    location_id = location_data['id']
    name = location_data['name']

    # 3. 异步请求 7 天天气预报 API
    forecast_data = await http_get("forecast", f"{base_url}/v7/weather/7d?location={location_id}", headers)
    if forecast_data["code"] != "200":
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"天气预报API返回错误[Status: {forecast_data['code']}]")

    daily_list = forecast_data.get("daily", [])
    if not daily_list:
        await matcher.finish("未获取到有效的预报天气明细数据。")

    # 4. 加载刚才排版好的 720px 纵向精致预测模板
    try:
        template = template_env.get_template("weather_vertical.html")
    except Exception as e:
        logger.error(f"加载 weather_vertical.html 模板失败: {e}")
        await matcher.finish(f"模板加载失败，请确保 html_template 目录下存在 weather_vertical.html。")

    # 5. 核心辅助映射函数：根据不同天气状态码注入精心挑选的渐变色和 Emoji
    def get_weather_assets(icon_code: str):
        try:
            code = int(icon_code)
        except ValueError:
            return "✨", "linear-gradient(135deg, #FF8C42, #FF3C5F)"

        # 晴天
        if code in [100, 150]:
            return "☀️", "linear-gradient(135deg, #FF8C42, #FF3C5F)"
        # 多云 / 晴间多云
        elif code in [101, 102, 103, 151, 152, 153]:
            return "⛅", "linear-gradient(135deg, #11998E, #38EF7D)"
        # 阴天
        elif code == 104:
            return "☁️", "linear-gradient(135deg, #757F9A, #D7DDE8)"
        # 各种雨天
        elif 300 <= code <= 399:
            return "🌧️", "linear-gradient(135deg, #3A7BD5, #203A43)"
        # 各种雪天
        elif 400 <= code <= 499:
            return "❄️", "linear-gradient(135deg, #E0EAFC, #CFDEF3)"
        # 雾/霾/沙尘
        elif 500 <= code <= 515:
            return "🌫️", "linear-gradient(135deg, #606C88, #3F2B96)"

        return "✨", "linear-gradient(135deg, #FF8C42, #FF3C5F)"

    def get_moon_emoji(phase_name: str):
        moons = {"新月": "🌑", "蛾眉月": "🌒", "上弦月": "🌓", "盈凸月": "🌔", "满月": "🌕", "亏凸月": "🌖", "下弦月": "🌗",
                 "残月": "🌘"}
        return moons.get(phase_name, "🌙")

    # 6. 定义单张卡片的异步渲染与截图单元任务
    async def render_single_day_card(day_item, index):
        date_labels = ["今天", "明天", "后天", "大后天", "第五天", "第六天", "第七天"]
        label = date_labels[index] if index < len(date_labels) else "预报"

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

        # ✨ 【关键点 1】：执行异步渲染，渲染出填充好数据的纯 HTML 字符串
        html_str = await template.render_async(**ctx)

        # ✨ 【关键点 2】：把 html_str 作为关键字参数赋给 html，切勿传错变量！
        img = await html_to_pic(
            html=html_str,  # 👈 必须是刚刚拿到的 html_str 字符串
            viewport={"width": 400, "height": 720}
        )
        return img

    # 7. 🚀 【极致高并发】通过 asyncio.gather 并发同时截取 7 张图片
    try:
        tasks = [render_single_day_card(day, idx) for idx, day in enumerate(daily_list)]
        img_bytes_list = await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"预报多卡片高并发截图失败: {e}")
        await matcher.finish(MessageSegment.reply(event.message_id) + f"预报多面板并发渲染失败: {e}")

    # 8. 📦 将截出来的多张图片字节流打包转换成 OneBot V11 标准的合并转发节点
    forward_nodes = []
    for img_bytes in img_bytes_list:
        forward_nodes.append(
            MessageSegment.node_custom(
                user_id=event.self_id,
                nickname="LingHuiBot",
                content=f"{MessageSegment.image(img_bytes)}"
            )
        )

    # 9. 📤 发送丝滑的合并转发消息流
    try:
        await bot.send_group_forward_msg(group_id=event.group_id, messages=forward_nodes)
    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"发送天气预报合并转发消息失败: {e}")
        await matcher.finish("发送合并转发天气流失败，请检查机器人发群合并转发的相关权限。")