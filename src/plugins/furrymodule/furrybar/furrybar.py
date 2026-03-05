import os
import re
import shutil

import emoji
import httpx
import zhconv
from nonebot import get_driver
from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..check_file import (
    forward_path
)
from ..commands import (
    furrybar,
    change_config,
    reset_furrybar,
    clear,
    latest,
    fb_model_list,
    user_model_switch,
    check_model
)
from ...utils import handle_json, handle_errors, batch_get

config = get_driver().config
try:
    APIKEY = config.furry_aikey
    BASE_URL = config.furry_ai_baseurl
    logger.success("✅已成功加载FurryBar的相关配置！")
except AttributeError:
    logger.warning("请在配置文件中设置FURRY_AIKEY、FURRY_AI_BASEURL以及FURRY_AI_MODELLIST！")


@furrybar.handle()
@handle_errors
async def furry_bar_function(matcher: Matcher, event: MessageEvent, reply: GroupMessageEvent):
    content = str(event.get_message())  # 用户输入内容
    # 屏蔽回复信息、复制的at信息、机器人信息、空信息
    if content == "" or "reply" in str(reply.get_event_description()) or str(
            event.user_id) == "2854196310" or "at" not in str(event.original_message):
        await matcher.finish()
    if len(content) >= 100:
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
    # 如果父目录不存在，则新建
    if not os.path.exists(user_data_directory):
        os.mkdir(user_data_directory)
    # 如果未读取到用户文件，则写默认文件
    if not os.path.exists(user_normal_path):
        await matcher.send(
            "未找到用户信息，发送创建用户信息<空格><这里输入称呼><空格><这里输入文字设定或介绍>即可定义个人信息")
        handle_json(user_normal_path, 'w', normal_data)
        handle_json(user_json_path, 'w', normal_data)
    # 读取用户文件
    user_json_data = handle_json(user_json_path, 'r')
    user_normal_json_data = handle_json(user_normal_path, 'r')
    user_model = user_json_data.get("model", "deepseek-reasoner")
    # 如果用户json数据为空，则新建messages键值对
    if not user_json_data:
        user_json_data['model'] = user_model
        user_json_data['messages'] = []
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
    user_json_data['model'] = user_model
    # Async httpx Request to API
    async with httpx.AsyncClient(
            http2=True,
            verify=False,
            timeout=httpx.Timeout(connect=10, read=60, write=60, pool=30)
    ) as client:
        response = await client.post(BASE_URL, headers=headers, json=user_json_data)
        # 请求未返回200 OK，输出错误内容
        if response.status_code != 200:
            text = ""
            try:
                text = response.json()["error"]["message"]
            except KeyError:
                pass
            await matcher.finish(MessageSegment.reply(
                event.message_id) + f"请求失败，API未返回正确的错误码。[HTTP {response.status_code}]\n错误文本：{text}")
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
        # logger.debug(f"Reason：{result['choices'][0]['message']['reasoning_content']}")
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
@handle_errors
async def reset_function(matcher: Matcher, event: MessageEvent):
    user = event.user_id
    main_path = forward_path / f"{user}" / f"{user}.json"
    user_data_path = forward_path / f"{user}" / f"{user}_Normal.json"
    handle_json(main_path, 'w', handle_json(user_data_path, 'r'))
    await matcher.finish(MessageSegment.reply(event.message_id) + "已重置聊天记录。")


@change_config.handle()
@handle_errors
async def change_config_function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    args_list = args.split(" ")
    logger.info(args)
    logger.info(args_list)
    user = event.user_id
    main_path_temp = forward_path / f"{user}"
    main_path = main_path_temp / f"{user}_Normal.json"
    if not os.path.exists(main_path_temp):
        await matcher.finish(MessageSegment.reply(
            event.message_id) + "似乎没有找到你的聊天信息，请先至少进行一次聊天后再定义自己的个人信息。")
    main_data = handle_json(main_path, 'r')
    self_data = main_data['messages']
    if len(self_data) >= 3:
        if self_data[-2].get("content") in "你知道我是谁吗":
            del self_data[-1], self_data[-2]
    temp_dict_1, temp_dict_2 = {
        "role": "user",
        "content": "你知道我是谁吗"
    }, {
        "role": "assistant",
        "content": f"当然知道呀~你是{args_list[0]}，{args_list[1]}"
    }
    self_data.append(temp_dict_1)
    self_data.append(temp_dict_2)
    main_data['messages'] = self_data
    handle_json(main_path, 'w', main_data)
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


@fb_model_list.handle()
async def _fb_model_list(matcher: Matcher, bot: Bot, event: GroupMessageEvent):
    # 获取模型列表
    async with httpx.AsyncClient(timeout=None) as client:
        data = await client.get(config.furry_ai_modellist)
        if data.status_code != 200:
            await matcher.finish(MessageSegment.reply(event.message_id) + f"API 返回了错误码：[HTTP {data.status_code}]")
    # 将获取的数据转化为json格式
    data = data.json()
    # 获取用户组
    user_groups = data['auto_groups']
    # 获取模型数据
    model_dict = data['data']
    # 构建默认列表
    model_list, vendor_list = [], []
    temp = await batch_get(f"用户组类型：{user_groups[0]}", None, event.self_id, "FurryBar 模型列表")
    # 获取供应商名称
    for vendors in data['vendors']:
        vendor_list.append(vendors['name'])
    vendor_list.append("Unknown")
    final_list = [temp]
    # 循环取出信息
    for model_data in model_dict:
        supported_text = ""
        model_name = model_data['model_name']
        vendor_id = model_data.get('vendor_id', len(vendor_list))
        model_ratio = model_data['model_ratio']
        for supported_list in model_data['supported_endpoint_types']:
            supported_text += f"{supported_list}、"
        enable_user_list = model_data['enable_groups']
        is_enable = "模型不可用：不在该模型支持的用户组"
        if enable_user_list:
            is_enable = "模型可用"
        model_list.append(model_name)
        text = (
            f"模型名称：{model_name}\n"
            f"供应商：{vendor_list[vendor_id - 1]}\n"
            f"模型比例：{model_ratio}\n"
            f"支持的断点类型：{supported_text}\n"
            f"该模型在当前用户组的可用性为：{is_enable}"
        )
        make_text = await batch_get(text, None, event.self_id, "FurryBar 模型列表")
        final_list.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)
    await matcher.finish()


@user_model_switch.handle()
@handle_errors
async def _model_switch(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    user = event.user_id
    args = str(args)
    user_normal_path = forward_path / f"{user}" / f"{user}_Normal.json"
    if not os.path.exists(user_normal_path):
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "未找到用户文件，请先使用一次FurryAI功能生成默认文件后重试此功能")
    data = handle_json(user_normal_path, 'r')
    await matcher.send(MessageSegment.reply(event.message_id) + f"获取到模型：{args}，正在验证模型是否存在")
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.get(config.furry_ai_modellist)
    if response.status_code != 200:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"API 返回了错误码：[HTTP {data.status_code}]")
    response = response.json()
    model_dict = response['data']
    model_list = []
    for model_name in model_dict:
        model_list.append(model_name['model_name'])
    if args not in model_list:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "未检索到此模型，请使用”模型列表“命令来查找可用模型")
    data['model'] = args
    handle_json(user_normal_path, 'w', data)
    await matcher.finish(MessageSegment.reply(event.message_id) + "模型已切换。若要立即生效，请发送命令”重置模型“")


@check_model.handle()
@handle_errors
async def _check_model(event: MessageEvent, matcher: Matcher):
    user = event.user_id
    user_normal_path = forward_path / f"{user}" / f"{user}_Normal.json"
    if not os.path.exists(user_normal_path):
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "未找到你的用户配置文件，请先使用过一次FurryAI生成默认文件后再试")
    data = handle_json(user_normal_path, 'r')
    await matcher.finish(MessageSegment.reply(event.message_id) + f"当前的模型是：{data['model']}")
