import os
import re
import shutil

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

from ..check_file import (
    forward_path,
    normal_path
)
from ..commands import (
    furrybar,
    change_config,
    reset_furrybar,
    clear,
    latest
)
from ...utils import handle_json, handle_errors

config = get_driver().config
try:
    APIKEY = config.furry_aikey
    BASE_URL = config.furry_ai_baseurl
    logger.success("✅已成功加载FurryBar的相关配置！")
except ValueError:
    logger.warning("请在配置文件中设置FURRY_AIKEY以及FURRY_AI_BASEURL！")


# Model_Path = opendata / "data/furry_system/FurryBar/model.json"

@furrybar.handle()
@handle_errors
async def furry_bar_function(matcher: Matcher, event: MessageEvent, reply: GroupMessageEvent):
    content = str(event.get_message())  # 用户输入内容
    # 屏蔽回复信息、复制的at信息、机器人信息、空信息
    if content == "" or "reply" in str(reply.get_event_description()) or str(
            event.user_id) == "2854196310" or "at" not in str(event.original_message):
        await matcher.finish()
    if len(content) > 100:
        await matcher.finish(MessageSegment.reply(event.message_id) + "请求被驳回：超出请求字数上限（100字符）。")
    # 将用户输入信息强制转换为简体中文，防止繁体中文以及其他莫名其妙的语言被传入模型
    user_message = zhconv.convert(content, 'zh-hans')
    # 驳回emoji
    if emoji.emoji_count(content) != 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + "请求被驳回：检测到emoji表情。")
    # 获取默认模型参数
    normal_data_path = forward_path / "furrybar_normal.json"
    normal_data = handle_json(normal_data_path, 'r')
    # 定义用户文件路径
    user = event.user_id
    user_data_directory = forward_path / f"{user}"
    user_json_path = user_data_directory / f"{user}.json"
    user_normal_path = user_data_directory / f"{user}_Normal.json"
    user_model_path = user_data_directory / f"model.json"
    # 如果父目录不存在，则新建
    if not os.path.exists(user_data_directory):
        os.mkdir(user_data_directory)
    # 如果未读取到用户文件，则写默认文件
    if not os.path.exists(user_normal_path):
        await matcher.send(
            "未找到用户信息，发送创建用户信息<空格><这里输入称呼><空格><这里输入文字设定或介绍>即可定义个人信息")
        handle_json(user_normal_path, 'w', normal_data)
        handle_json(user_json_path, 'w', normal_data)
        handle_json(user_model_path, 'w', {"model": "deepseek-reasoner"})
    # 读取用户文件
    user_json_data = handle_json(user_json_path, 'r')
    user_normal_json_data = handle_json(user_normal_path, 'r')
    user_model_data = handle_json(user_model_path, 'r')
    # 构建用户对话json
    user_message_data = {
        "role": "user",
        "content": f"{user_message}"
    }
    # 构建请求头
    headers = {
        'Authorization': f'{APIKEY}',
        'Content-Type': 'application/json'
    }
    # 将用户对话添加进data
    user_json_data['messages'].append(user_message_data)
    # 将用户的模型数据写入
    user_model_data['model'] = user_model_data.get("model", "deepseek-reasoner")
    # Async httpx Request to API
    async with httpx.AsyncClient(
            http2=True,
            verify=False,
            timeout=httpx.Timeout(connect=10, read=60, write=60, pool=30)
    ) as client:
        response = await client.post(BASE_URL, headers=headers, json=user_json_data)
        # 请求未返回200 OK，输出错误内容
        if response.status_code != 200:
            await matcher.finish(MessageSegment.reply(
                event.message_id) + f"请求失败，API未返回正确的错误码。[HTTP {response.status_code}]")
        # 请求返回空值，模型异常
        if response == "":
            await matcher.finish(
                MessageSegment.reply(event.message_id) + "模型返回了空值，这可能是因为key失效或不稳定，请稍后再试。")
        # 请求返回正确的值，但是值中含有错误，输出错误内容：
        result = response.json()
        if result.get("error") is not None:
            error_text = result['error']['message']
            # 模型繁忙错误
            if "模型繁忙" in str(error_text):
                await matcher.finish(
                    MessageSegment.reply(event.message_id) +
                    "遇到一个错误，这可能是因为模型认为该内容不适合展示或该模型繁忙，请稍后重试。"
                )
            # 如果不是模型繁忙，那么必定是上下文超出长度，重置模型信息
            handle_json(user_json_path, 'w', user_normal_json_data)
            await matcher.finish(
                MessageSegment.reply(event.message_id) +
                f"遇到问题：{error_text}\n"
                f"凌辉Bot已经自动清空了对话记录以尝试修复，请在稍后重试命令以验证是否已解决问题"
            )
        # 模型正确访问，返回数据
        return_data = result['choices'][0]['message']['content']
        # 清除回答中的换行符号
        text = return_data.replace("\n", "")
        # 构建答复数据
        assistant_data = {
            "role": "assistant",
            "content": text
        }
        # 写入答复数据
        user_json_data['messages'].append(assistant_data)
        # 写入用户文件进行保存
        handle_json(user_json_path, 'w', user_json_data)
        await matcher.finish(MessageSegment.reply(event.message_id) + text)


@reset_furrybar.handle()
async def reset_function(matcher: Matcher, event: MessageEvent):
    user = event.user_id
    main_path = forward_path / f"{user}" / f"{user}.json"
    user_data_path = forward_path / f"{user}" / f"{user}_Normal.json"
    handle_json(main_path, 'w', handle_json(user_data_path, 'r'))
    await matcher.finish(MessageSegment.reply(event.message_id) + "已重置聊天记录。")


@change_config.handle()
async def change_config_function(event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    args_list = args.split(" ")
    logger.info(args)
    logger.info(args_list)
    # await change_config.finish()
    user = event.user_id
    main_path = forward_path / f"{user}" / f"{user}_Normal.json"
    main_path_temp = forward_path / f"{user}"
    if not os.path.exists(main_path_temp):
        os.mkdir(main_path_temp)
    normal_dict = handle_json(normal_path, 'r')
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
    handle_json(main_path, 'w', normal_dict)
    temp = temp_dict_2['content']
    await change_config.finish(MessageSegment.reply(
        event.message_id) + f"已记录个人设定，内容如下：\nUser：你知道我是谁吗\nAssistant：{temp}\n注：如需改动立即生效，请发送“重置模型”命令")


@clear.handle()
async def clear_function(matcher: Matcher, event: MessageEvent):
    user = event.user_id
    main_path_temp = forward_path / f"{user}"
    if os.path.exists(main_path_temp):
        shutil.rmtree(main_path_temp)
        await matcher.finish(f"已经清空了{user}的FurryBar数据。")
    else:
        await matcher.finish("清除失败：未找到个人信息。")


@latest.handle()
async def latest_talk(matcher: Matcher, event: MessageEvent):
    user = event.user_id
    path = forward_path / f"{user}" / f"{user}.json"
    if not os.path.exists(path):
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到聊天记录")
    text = handle_json(forward_path / f"{user}" / f"{user}.json", 'r')
    if text[-1]['role'] == 'system':
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到聊天记录")
    user = text[-2]['content']
    text = text[-1]['content']
    text = re.sub(r'.*?(<think.*?>|</think>|<think/>)', '', text, flags=re.DOTALL).strip()
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"用户：{user}\n模型回复：{text}\n\n为防止刷屏，已经去除思考内容。请注意辨别！")
