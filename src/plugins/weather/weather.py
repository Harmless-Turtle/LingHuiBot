import os
import httpx
import time
import jinja2
import jwt

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot_plugin_htmlrender import html_to_pic
from nonebot.exception import FinishedException
from nonebot.internal.matcher import Matcher
from nonebot import logger, get_driver
from nonebot.params import CommandArg
import re

from .commands import weather_check
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
# 创建文件系统加载器，告诉 Jinja2 去哪里找 HTML 模板文件
template_loader = jinja2.FileSystemLoader(searchpath=CURRENT_DIR)
# 实例化 template_env 对象
template_env = jinja2.Environment(loader=template_loader, enable_async=True)

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
    # 构建JWT载荷
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
        # 1. 提取首位空气质量标准指数
        target_index = AQI_data["indexes"][0]
        aqi_display = f"{target_index.get('aqiDisplay', '--')} {target_index.get('category', '')}"
        aqi_color = target_index.get("color")  # 包含 red, green, blue
        aqi_effect = target_index.get("health", {}).get("effect", "")
        if target_index.get("primaryPollutant"):
            primary_pollutant = target_index["primaryPollutant"].get("name", "无")

        # 2. 循环清洗污染物浓度
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