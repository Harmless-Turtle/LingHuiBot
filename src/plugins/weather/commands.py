from nonebot import on_command

# 敏感词管理
weather_check = on_command("天气查询", aliases={"查询天气"})
typhoon_check = on_command("台风查询", aliases={"查询台风"})
typhoon_subscribe = on_command("台风订阅", aliases={"订阅台风"})