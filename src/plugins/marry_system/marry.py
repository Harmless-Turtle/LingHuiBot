import random as rd
import time
from datetime import datetime
from typing import Optional

# 导入事件响应器以进行操作
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    Message,
    Bot
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot import logger

from .commands import *
from .check_files import *

@marry_random.handle()
@utils.handle_errors
async def marry_random_func(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text():await matcher.finish()
    # 读取json数据
    data = utils.handle_json(marry_json_path, 'r')
    # 将自己的QQ号转为str格式，方便后续判断
    self_qq = str(event.user_id)
    group_id = str(event.group_id)
    # 生成默认参数
    switch = False
    count = 0
    # 如果用户数据已存在于key中（被求婚？求婚中？已有对象？），则结束事件处理
    if data.get(self_qq):
        master_dict = data[self_qq]
        if data[self_qq].get(group_id,False) and data[self_qq][group_id].get("cp_qq",False):
            logger.info("已经有对象了，跳过执行")
            text = "你似乎已经有对象了吧...？"
            if data[self_qq].get("request",False) or data[self_qq][group_id].get("cp_qq",False) == 114514:
                self_data = data[self_qq][group_id]
                request_mode = self_data['request_mode']
                request = self_data['request']
                stranger_info = await bot.get_stranger_info(user_id=request)
                nickname = stranger_info.get('nickname', '昵称获取失败')
                request_list = [f"向“{nickname}”求婚中",f"被“{nickname}”求婚中"]
                text = f"你当前正在{request_list[request_mode]}\n请先通过“同意/拒绝求婚”或“取消求婚”命令作出决定后再试。"
            await matcher.finish(MessageSegment.reply(event.message_id)+f"{text}")
        # 读取计数器信息，并进行次数限制判断
        count_json = data[self_qq].get(group_id,False)
        logger.info(count_json)
        if count_json:
            now = datetime.fromtimestamp(int(time.time()))
            self_time = datetime.fromtimestamp(count_json['time'])
            if now.day != self_time.day or now.month != self_time.month:
                logger.info("重置计数器")
                # 如果当前时间和上次请求时间不在同一天，则重置计数器
                count_json['count'] = 0
                count_json['switch'] = True
                logger.info("Reset")
            if count_json.get('switch',False):
                logger.info("获取Switch")
                switch = count_json['switch']
            count = count_json['count']
        if count > 3:
            logger.info("已经达到了请求次数上限啦！本次跳过执行")
            if switch:
                count_json['switch'] = False
                utils.handle_json(marry_count_path, 'w', count_json)
                await matcher.finish(MessageSegment.reply(event.message_id)+"你已经结婚太多次了啦！第二天再结~\n（免打扰模式已开启，您在重置时间前只会看到此消息1次）")
            await matcher.finish()
    else:
        master_dict = {}
    
    # 初步生成排除列表，将已存在的key（即已经有对象的人）和bot以及用户加入到排除列表中，并转化为整数方便进行判断
    exclusion_list = [int(key) for key in data.keys() if data[key].get(group_id,False) and data[key][group_id].get("cp_qq", 0)]
    # 将bot和用户加入到排除列表中
    exclusion_list.extend([event.self_id, event.user_id])
    # 生成群成员列表
    group_user_list = await bot.call_api("get_group_member_list",group_id=event.group_id)
    # 生成随机取值的基列
    data_list = [x['user_id'] for x in group_user_list if x['user_id'] not in exclusion_list and not x['is_robot']]
    # 生成随机数，并获取对应的QQ号
    if len(data_list)-1 == 0:
        await matcher.finish(MessageSegment.reply(event.message_id)+"这个群好像没有其他人了呢...？")
    random_select = data_list[rd.randint(0, len(data_list) - 1)]
    # 生成时间戳
    timestamp = int(time.time())
    # 构建Json文件，预备写入
    random_dict = {}
    logger.info(f"Debug:计数器：{count}")
    master_dict[group_id] = {"cp_qq":random_select,"time":timestamp,"count":count+1,"switch":True}
    random_dict[group_id] = {"cp_qq":event.user_id,"time":timestamp}
    # 将构建好的Json内容直接增加至上文中获取的Data和计数器Data中
    data[f"{random_select}"] = random_dict
    data[f"{self_qq}"] = master_dict
    # 写入文件
    utils.handle_json(marry_json_path, 'w', data)
    # 获取结束事件处理所必要的讯息
    stranger_info = await bot.get_stranger_info(user_id=random_select)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    text = ""
    if count == 2:
        text = "不要老是换群友老婆啦笨蛋！\n"
    elif count == 3:
        text = "再换今天就不给你找群友老婆了！\n"
    # 结束事件处理
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{text}好嗷~你已经和“{nickname}”【{random_select}】在一起了呢")


@finish_marry.handle()
@utils.handle_errors
async def finish_marry_func(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text():await matcher.finish()
    # 获取用户的QQ，并将值转为str格式
    self_qq = str(event.user_id)
    group_id = str(event.group_id)
    # 获取数据
    data = utils.handle_json(marry_json_path, 'r')
    self_data: Optional[dict,None] = data.get(self_qq,False)
    # 异常处理
    if self_data and self_data.get(group_id) and self_data[group_id].get("cp_qq", 114514) == 114514:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你似乎还没有对象吧xwx")
    # 确定用户存在对象后，读取其对象的值
    logger.info(f"{self_data}\n{type(self_data)}")
    self_data = self_data[group_id]
    logger.info(self_data)
    # 获取对象的QQ号
    cp_qq = str(self_data['cp_qq'])
    cp_data = data[cp_qq]
    logger.info(cp_data)
    stranger_info = await bot.get_stranger_info(user_id=int(cp_qq))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    time_text = utils.time_handle(self_data['time'])
    # 直接删除用户和用户对象json
    del data[self_qq][group_id]["cp_qq"],data[cp_qq][group_id]["cp_qq"]
    # 将处理完的Data写入文件
    utils.handle_json(marry_json_path, 'w', data)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"你已经和你的群友对象“{nickname}”[{cp_qq}]离婚了呢www\n在一起的时间：{time_text}")

@marry_propose.handle()
@utils.handle_errors
async def marry_propose_func(matcher:Matcher,event:MessageEvent,bot:Bot):
    # 获取数据
    text = event.get_message()
    user_id,bot_qq,self_qq,timestamp,group_id = event.self_id,event.self_id,event.user_id,int(time.time()),str(event.group_id)
    # 获取at值
    for msg_seg in text:
        if msg_seg.type == 'at':
            logger.info(msg_seg.data)
            user_id = str(msg_seg.data['qq'])
            break
    logger.info(user_id)
    is_robot = await bot.get_group_member_info(group_id=event.group_id,user_id=user_id)
    if int(user_id) == int(self_qq) or int(user_id) == int(bot_qq) or is_robot['is_robot']:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你你...你不可以向自己或者机器人求婚呢xwx")
    # 判断是否为非法请求
    # 获取请求值是否为tx机器人
    temp = str(text)
    if user_id == 0 or user_id == str(event.self_id):
        await matcher.finish(MessageSegment.reply(event.message_id)+"凌辉Bot似乎没能理解你要向谁求婚呢...是不是复制了别人的请求呀owo一定要自己@出来哦~/_ \\")
    if "CQ" not in temp and "求婚" in temp:
        await matcher.finish()
    data = utils.handle_json(marry_json_path, 'r')
    if data.get(user_id,False) and data[user_id].get(group_id,False) and data[user_id][group_id].get("cp_qq",False):
        text = "凌辉Bot小声提醒您：您请求的用户似乎已经有对象了awa"
        if data[user_id][group_id].get("response",False) != 0:
            text = "凌辉Bot小声提醒您：您请求的用户似乎正在被求婚或者求婚其他人呢awa"
        await matcher.finish(MessageSegment.reply(event.message_id)+text)
    if data.get(str(self_qq), {}).get(group_id, {}).get("cp_qq",114514) != 114514:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你已经有对象了啦qwq怎么可以一夫多妻呢/_ \\")
    if data.get(str(self_qq), {}).get(group_id, {}).get("response",0) != 0:
        response = data[str(self_qq)][group_id]['response']
        stranger_info = await bot.get_stranger_info(user_id=response)
        request_text = [f"向{stranger_info["nick"]}求婚中",f"被{stranger_info["nick"]}求婚中"]
        request_mode = data[str(self_qq)][group_id]['Request_Mode']
        await matcher.finish(MessageSegment.reply(event.message_id)+f"你似乎正在{request_text[request_mode]}呢owo")
    # 获取或创建用户数据字典
    self_data = data.setdefault(str(self_qq), {})
    request_data = data.setdefault(str(user_id), {})
    self_count = self_data.get(group_id, {}).get("count", 0)
    cp_count = request_data.get(group_id, {}).get("count", 0)
    # 主动请求人的状态码为0，被请求人的状态码为1
    self_dict = {
        "cp_qq":114514,
        "response":int(user_id),
        "time":timestamp,
        "Request_Mode":0,
        "count":self_count
    }
    request_dict = {
        "cp_qq":114514,
        "response":self_qq,
        "time":timestamp,
        "Request_Mode":1,
        "count":cp_count
    }

    # 更新当前群组数据
    self_data[group_id] = self_dict
    request_data[group_id] = request_dict
    utils.handle_json(marry_json_path, 'w', data)
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    await matcher.finish(MessageSegment.reply(event.message_id)+f"好嗷~你已经向“{nickname}”求婚了哦^_~\n{nickname}[{int(user_id)}]可以通过“同意求婚”或“拒绝求婚”同意或者拒绝求婚请求w")

@marry_select.handle()
@utils.handle_errors
async def marry_select_func(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    text,self_qq,group_id = str(event.get_message()),str(event.user_id),str(event.group_id)
    data = utils.handle_json(marry_json_path, 'r')
    if data.get(self_qq,{}).get(group_id,{}).get("request",0) == 0:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你似乎没有被求婚或正在向他人求婚呢owo")
    if data.get(self_qq).get(group_id).get('cp_qq',0) != 114514 and data.get(self_qq).get(group_id).get('cp_qq',0) != 0:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你似乎已经有对象了吧...？")
    request = data[self_qq][group_id]['request']
    mode = data[self_qq][group_id]["Request_Mode"]
    stranger_info = await bot.get_stranger_info(user_id=request)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    if "拒绝" in text or "取消" in text:
        if not "取消" in text:
            if mode != 1:
                await matcher.finish(MessageSegment.reply(event.message_id)+"这个命令不是你用的吧owo")
        del data[self_qq][group_id]["cp_qq"],data[self_qq][group_id]["request"],data[self_qq][group_id]["Request_Mode"],data[str(request)][group_id]["cp_qq"],data[str(request)][group_id]["request"],data[str(request)][group_id]["Request_Mode"]
        utils.handle_json(marry_json_path, 'w', data)
        temp = "拒绝"
        temp_1 = ""
        if "取消" in text:
            temp = "取消"
        if mode == 0:
            temp_1 = "对"
        await matcher.finish(MessageSegment.reply(event.message_id)+f"好叭/_ \\你已经{temp}了{temp_1}“{nickname}”的求婚请求了呢~")
    if mode == 0 and "同意" in text:
        await matcher.finish(MessageSegment.reply(event.message_id)+"这个命令不是你用的吧owo")
    timestamp = int(time.time())
    self_data = data.setdefault(str(self_qq), {})
    request_data = data.setdefault(str(str(request)), {})
    self_count = self_data.get(group_id, {}).get("count", 0)
    cp_count = request_data.get(group_id, {}).get("count", 0)
    self_dict = {
        "cp_qq":request,
        "request":0,
        "time":timestamp,
        "Request_Mode":2,
        "count":self_count
    }
    request_dict = {
        "cp_qq":int(self_qq),
        "request":0,
        "time":timestamp,
        "Request_Mode":2,
        "count":cp_count
    }
    # 获取或创建用户数据字典
    self_data = data.setdefault(str(self_qq), {})
    request_data = data.setdefault(str(request), {})
    # 更新当前群组数据
    self_data[group_id] = self_dict
    request_data[group_id] = request_dict
    utils.handle_json(marry_json_path, 'w', data)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"好哦好哦~（拍爪子）你已经同意“{nickname}”的求婚请求了哦~")

@marry_time_check.handle()
@utils.handle_errors
async def marry_time_check_func(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    data = utils.handle_json(marry_json_path, 'r')
    self_qq,group_id = str(event.user_id),str(event.group_id)
    if not (data.get(self_qq,False) and data[self_qq].get(group_id,False)) or data[self_qq].get(group_id,{}).get("cp_qq", 114514) == 114514:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你似乎还没有对象吧xwx")
    user_id = data[self_qq][group_id]['cp_qq']
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    time_text = utils.time_handle(data[self_qq][group_id]['time'])
    await matcher.finish(MessageSegment.reply(event.message_id)+f"你和群友“{nickname}”[{int(user_id)}]已经在一起{time_text}了呢~")

@marry_check.handle()
@utils.handle_errors
async def marry_check_func(matcher:Matcher,event:MessageEvent,bot:Bot):
    # 读取前置数据
    data = utils.handle_json(marry_json_path, 'r')
    self_qq,group_id,user_id = str(event.user_id),str(event.group_id),0
    # 获取at值
    text = event.get_message()
    for msg_seg in text:
        if hasattr(msg_seg, 'type') and msg_seg.type == 'at':
            user_id = str(msg_seg.data.get('qq', 0))
            break
    if user_id != 0:
        self_qq = user_id
    text = "你"
    # 安全获取嵌套值，避免异常
    user_data = data.get(str(self_qq), {}).get(str(group_id), {})
    cp_qq = user_data.get("cp_qq",0)
    if cp_qq == 114514 or cp_qq == 0:
        logger.info(f"Debug:获取的cp_qq是{cp_qq}，用户id是{user_id}，群组id是{group_id}")
        if str(self_qq) != str(event.user_id):
            await matcher.finish(MessageSegment.reply(event.message_id) + "你查找的群友似乎还没有对象owo")
        await matcher.finish(MessageSegment.reply(event.message_id) + "你似乎还没有对象吧xwx")    # 确定用户合法后读取必要数据
    cp_qq,timestamp = user_data['cp_qq'],user_data['time']
    # 转换为 datetime 对象
    dt_object = datetime.fromtimestamp(timestamp)
    # 获取用户名
    stranger_info = await bot.get_stranger_info(user_id=int(cp_qq))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    # 获取自己的用户名
    if self_qq != str(event.user_id):
        stranger_info_self = await bot.get_stranger_info(user_id=int(self_qq))
        text = stranger_info_self.get('nickname', '昵称获取失败')
    # 获取时间
    time_text = utils.time_handle(timestamp)
    # 最终输出
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{text}和“{nickname}”[{cp_qq}]在{dt_object.strftime('%Y-%m-%d %H:%M:%S')}时在一起了哦~\n一共在一起{time_text}了呢~")


@marry_switch.handle()
@utils.handle_errors
async def marry_switch_utils(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    # 读取前置数据
    data = utils.handle_json(marry_json_path, 'r')
    self_qq = str(event.user_id)
    group_id = str(event.group_id)
    if data.get(self_qq,{}).get(group_id,{}).get("cp_qq", 0) != 0:
        # 获取对象的QQ号并删除两者的绑定关系
        cp_qq = str(data[self_qq][group_id]['cp_qq'])
        del data[cp_qq][group_id]["cp_qq"], data[cp_qq][group_id]["time"], data[self_qq][group_id]["cp_qq"], data[self_qq][group_id]["time"]
        if data.get(self_qq,{}).get(group_id,{}).get("cp_qq", 0) == 114514:
            request = data[self_qq][group_id]['request']
            del data[request][group_id]["request"], data[request][group_id]["Request_Mode"],data[self_qq][group_id]["request"], data[self_qq][group_id]["Request_Mode"]
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text():await matcher.finish()
    # 读取json数据
    data = utils.handle_json(marry_json_path, 'r')
    # 将自己的QQ号转为str格式，方便后续判断
    self_qq = str(event.user_id)
    group_id = str(event.group_id)
    # 生成默认参数
    switch = False
    count = 0
    if data.get(self_qq):
        master_dict = data[self_qq]
        # 读取计数器信息，并进行次数限制判断
        count_json = data[self_qq].get(group_id,False)
        logger.info(count_json)
        if count_json:
            now = datetime.fromtimestamp(int(time.time()))
            self_time = datetime.fromtimestamp(count_json['time'])
            if now.day != self_time.day or now.month != self_time.month:
                logger.info("重置计数器")
                # 如果当前时间和上次请求时间不在同一天，则重置计数器
                count_json['count'] = 0
                count_json['switch'] = True
                logger.info("Reset")
            if count_json.get('switch',False):
                switch = count_json['switch']
                logger.info(f"获取Switch：{switch}")
            count = count_json['count']
        if count > 3:
            logger.info("已经达到了请求次数上限啦！本次跳过执行")
            if switch:
                count_json['switch'] = False
                logger.info(f"写入数据：{count_json}")
                utils.handle_json(marry_json_path, 'w', count_json)
                await matcher.finish(MessageSegment.reply(event.message_id)+"你已经结婚太多次了啦！第二天再结~\n（免打扰模式已开启，您在重置时间前只会看到此消息1次）")
            await matcher.finish()
    else:
        master_dict = {}
    
    # 初步生成排除列表，将已存在的key（即已经有对象的人）和bot以及用户加入到排除列表中，并转化为整数方便进行判断
    exclusion_list = [int(key) for key in data.keys() if data[key].get(group_id,False) and data[key][group_id].get("cp_qq", 0)]
    # 将bot和用户加入到排除列表中
    exclusion_list.extend([event.self_id, event.user_id])
    # 生成群成员列表
    group_user_list = await bot.call_api("get_group_member_list",group_id=event.group_id)
    # 生成随机取值的基列
    data_list = [x['user_id'] for x in group_user_list if x['user_id'] not in exclusion_list and not x['is_robot']]
    # 生成随机数，并获取对应的QQ号
    if len(data_list)-1 == 0:
        await matcher.finish(MessageSegment.reply(event.message_id)+"这个群好像没有其他人了呢...？")
    random_select = data_list[rd.randint(0, len(data_list) - 1)]
    # 生成时间戳
    timestamp = int(time.time())
    # 构建Json文件，预备写入
    random_dict = {}
    logger.info(f"Debug:计数器：{count}")
    master_dict[group_id] = {"cp_qq":random_select,"time":timestamp,"count":count+1,"switch":True}
    random_dict[group_id] = {"cp_qq":event.user_id,"time":timestamp}
    # 将构建好的Json内容直接增加至上文中获取的Data和计数器Data中
    data[f"{random_select}"] = random_dict
    data[f"{self_qq}"] = master_dict
    # 写入文件
    utils.handle_json(marry_json_path, 'w', data)
    # 获取结束事件处理所必要的讯息
    stranger_info = await bot.get_stranger_info(user_id=random_select)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    text = ""
    if count == 2:
        text = "不要老是换群友老婆啦笨蛋！\n"
    elif count == 3:
        text = "再换今天就不给你找群友老婆了！\n"
    # 结束事件处理
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{text}好嗷~你已经和“{nickname}”【{random_select}】在一起了呢")
