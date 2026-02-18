import os
import re
import shutil
from pathlib import Path

import emoji
import httpx
import zhconv
from nonebot import get_driver
from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import on_command, on_message
from nonebot.rule import to_me

from src.plugins import utils

furrybar = on_message(rule=to_me(), priority=99, block=True)
change_config = on_command("更改用户信息", aliases={"创建用户信息", "定义个人信息"}, block=False)
reset_furrybar = on_command(
    "Reset", aliases={"重置对话", "重置模型"})
clear = on_command("删除信息", aliases={"重置fb", "清空数据"})
latest = on_command("上次对话", aliases={"上次聊天", "最后对话", "最后记录"})

config = get_driver().config
try:
    Talk_key = config.furry_aikey
    logger.success("✅已成功加载FurryBar的相关配置！")
except ValueError:
    logger.warning("请在配置文件中设置furry_token！")

opendata = Path.cwd()
forward_path = opendata / "data" / "furry_system" / "FurryBar"
Normal_Path = forward_path / "FurryBar_Normal.json"

utils.ensure_files_exist([Normal_Path],'furrybar模块')

# Model_Path = opendata / "data/Furry_System/FurryBar/model.json"

@furrybar.handle()
@utils.handle_errors
async def furrybar_function(matcher: Matcher, event: MessageEvent, reply: GroupMessageEvent):
    # await matcher.finish(MessageSegment.reply(event.message_id)+"该功能正在维护，暂停提供服务")
    logger.info("FB")
    content = str(event.get_message())
    if content == "" or "reply" in str(reply.get_event_description()) or str(
            event.user_id) == "2854196310" or "[CQ:at,qq=3806419216]" not in str(
        event.original_message) or "单词" in content: await matcher.finish()
    user = event.user_id
    main_path = forward_path / f"/{user}/{user}.json"
    normal_dict_temp = forward_path / f"{user}/{user}_Normal.json"
    user_data_directory = forward_path/f"{user}"
    if not os.path.exists(user_data_directory):
        os.mkdir(user_data_directory)
    if not os.path.exists(main_path):
        temp_dict = utils.handle_json(Normal_Path, 'r')
        utils.handle_json(main_path, 'w', temp_dict)
        utils.handle_json(normal_dict_temp, 'w', temp_dict)
    url = "http://fb-ai.furrybar.com:3000/v1/chat/completions"
    model_path = opendata / f"data/Furry_System/FurryBar/{user}/model.json"
    model = {"model": 'deepseek-reasoner'}
    messages_data = utils.handle_json(main_path, 'r', None)
    if os.path.exists(model_path):
        model = utils.handle_json(model_path, 'r', None)
    else:
        utils.handle_json(model_path, 'w', model)
        await matcher.send(
            "未找到用户信息，发送创建用户信息<空格><这里输入称呼><空格><这里输入文字设定或介绍>即可定义个人信息")
    model = model['model']
    simplified_text = zhconv.convert(content, 'zh-hans')
    if emoji.emoji_count(content) != 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + "请求被驳回：检测到emoji表情。")
    text_dict = {
        "role": "user",
        "content": f"{simplified_text}"
    }
    if len(content) > 100:
        await matcher.finish(MessageSegment.reply(event.message_id) + "请求被驳回：超出请求字数上限（100字符）。")
    messages_data.append(text_dict)
    model = "deepseek-reasoner"
    payload = {
        'model': f"{model}",  # 从文件里面导入预设模型
        "messages": messages_data
    }
    logger.info("Debug:将使用" + model + "模型进行答复。")
    headers = {
        'Authorization': f'{Talk_key}',
        'Content-Type': 'application/json'
    }
    # response = requests.post(url, headers=headers, data=payload)
    async with httpx.AsyncClient(http2=True, verify=False,
                                 timeout=httpx.Timeout(connect=10, read=60, write=60, pool=30)) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.error(f"{response.text}")
            await matcher.finish(MessageSegment.reply(
                event.message_id) + f"请求失败\n服务器返回:{response['error']['message']}[{response.status_code}]")
        if response == "":
            await matcher.finish(
                MessageSegment.reply(event.message_id) + "模型返回了空值，这可能是因为key失效或不稳定，请稍后再试。")
        json = response.json()
        if json.get("error") is not None:
            error_text = json['error']['message']
            if "模型繁忙" in str(error_text):
                await matcher.finish(MessageSegment.reply(
                    event.message_id) + "遇到一个错误，这可能是因为模型认为该内容不适合展示或该模型繁忙，请稍后重试。")
            normal_data = utils.handle_json(Normal_Path, 'r', None)
            utils.handle_json(main_path, 'w', normal_data)
            await matcher.finish(MessageSegment.reply(
                event.message_id) + f"""遇到问题：{error_text}\n凌辉Bot已经自动清空了对话记录以尝试修复，请在稍后重试命令以验证是否已解决问题""")
        logger.info(json)
        text = json['choices'][0]['message']['content']
        logger.info("Debug:模型回复，内容是" + text)
        text = text.replace("\n", "")
        assistant_dict = {
            "role": "assistant",
            "content": text
        }
        messages_data.append(assistant_dict)
        utils.handle_json(main_path, 'w', messages_data)
        logger.success("Debug:处理完成，最终输出：" + text)
        await matcher.finish(MessageSegment.reply(event.message_id) + text)


@reset_furrybar.handle()
async def reset_function(matcher: Matcher, event: MessageEvent):
    user = event.user_id
    main_path = opendata / f"data/Furry_System/FurryBar/{user}/{user}.json"
    normal_path = opendata / f"data/Furry_System/FurryBar/{user}/{user}_Normal.json"
    utils.handle_json(main_path, 'w', utils.handle_json(normal_path, 'r'))
    await matcher.finish(MessageSegment.reply(event.message_id) + "已重置聊天记录。")


@change_config.handle()
async def change_config_function(event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    args_list = args.split(" ")
    logger.info(args)
    logger.info(args_list)
    # await change_config.finish()
    user = event.user_id
    main_path = opendata / f"data/Furry_System/FurryBar/{user}/{user}_Normal.json"
    main_path_temp = opendata / f"data/Furry_System/FurryBar/{user}"
    if not os.path.exists(main_path_temp):
        os.mkdir(main_path_temp)
    normal_dict = utils.handle_json(Normal_Path, 'r')
    for i in range(0, len(normal_dict) - 1):
        if normal_dict[i].get("你知道我是谁吗") is not None:
            del normal_dict[i], normal_dict[i + 1]
    temp_dict_1, temp_dict_2 = {
        "role": "user",
        "content": "你知道我是谁吗"
    }, {
        "role": "assistant",
        "content": f"当然知道呀~你是{args_list[0]}，{args_list[1]}"
    }
    normal_dict.append(temp_dict_1)
    normal_dict.append(temp_dict_2)
    utils.handle_json(main_path, 'w', normal_dict)
    temp = temp_dict_2['content']
    await change_config.finish(MessageSegment.reply(
        event.message_id) + f"已记录个人设定，内容如下：\nUser：你知道我是谁吗\nAssistant：{temp}\n注：如需改动立即生效，请发送“重置模型”命令")


@clear.handle()
async def clear_function(matcher: Matcher, event: MessageEvent):
    user = event.user_id
    main_path_temp = opendata / f"data/Furry_System/FurryBar/{user}"
    if os.path.exists(main_path_temp):
        shutil.rmtree(main_path_temp)
        await matcher.finish(f"已经清空了{user}的FurryBar数据。")
    else:
        await matcher.finish("清除失败：未找到个人信息。")


@latest.handle()
async def latest_talk(matcher: Matcher, event: MessageEvent):
    user = event.user_id
    path = f"{opendata}/data/Furry_System/FurryBar/{user}/{user}.json"
    if not os.path.exists(path):
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到聊天记录")
    text = utils.handle_json(opendata / "data" / "Furry_System" / "FurryBar" / f"{user}" / f"{user}.json", 'r')
    if text[-1]['role'] == 'system':
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到聊天记录")
    user = text[-2]['content']
    text = text[-1]['content']
    text = re.sub(r'.*?(<think.*?>|</think>|<think/>)', '', text, flags=re.DOTALL).strip()
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"用户：{user}\n模型回复：{text}\n\n为防止刷屏，已经去除思考内容。请注意辨别！")
