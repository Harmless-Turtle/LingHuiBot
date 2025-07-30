import ssl
from h11 import Request
from nonebot.plugin import on_command  # 导入事件响应器
from nonebot.adapters import Message  # 导入抽象基类Message以允许Bot回复str
from src.plugins import utils
# 导入事件响应器以进行操作
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    Message,
    Bot
)
from nonebot.matcher import Matcher
import random as rd
import time
from datetime import datetime
from nonebot.permission import SUPERUSER  # 导入SUPERUSER库以限制仅SUPERUSER用户组可用命令
from nonebot.params import CommandArg
from pathlib import Path
from nonebot import logger

Marry_Random = on_command("结婚",block=True)
Finish_Marry = on_command("离婚",block=True)

Marry_Propose = on_command("求婚",priority=10,block=True)
Marry_Time_Check = on_command("结婚时间",block=True, aliases={"结婚时长"})
Marry_Select = on_command("同意求婚",aliases={"拒绝求婚","取消求婚"},block=True)
Marry_Check = on_command("查看对象",aliases={"我的对象"},block=True)
MarryChekOthers = on_command("群友对象",block=True)
MarrySwitch = on_command("换老婆")

# 定义Data存放路径并作为全局变量使用
Path_Header = Path.cwd() / "data" / "Marry_System"
# 定义全局变量方便处理
Marry_Json_Path = Path_Header / 'Marry.json'
Temp_Json_Path = Path_Header / "Temp.json"
Marry_Count_Path = Path_Header / 'Marry_Count.json'
Request_Path = Path_Header / "Request.json"

@Marry_Random.handle()
@utils.handle_errors
async def MR_Function(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text():await matcher.finish()
    # 读取json数据
    Data = utils.handle_json(Marry_Json_Path, 'r')
    # 将自己的QQ号转为str格式，方便后续判断
    Self_QQ = str(event.user_id)
    group_id = str(event.group_id)
    # 生成默认参数
    Switch = False
    Count = 0
    # 如果用户数据已存在于key中（被求婚？求婚中？已有对象？），则结束事件处理
    if Data.get(Self_QQ):
        Master_Dict = Data[Self_QQ]
        if Data[Self_QQ].get(group_id,False) and Data[Self_QQ][group_id].get("cp_qq",False):
            logger.info("已经有对象了，跳过执行")
            Text = "你似乎已经有对象了吧...？"
            if Data[Self_QQ].get("Request",False) or Data[Self_QQ][group_id].get("cp_qq",False) == 114514:
                self_data = Data[Self_QQ][group_id]
                Request_Mode = self_data['Request_Mode']
                Request = self_data['Request']
                stranger_info = await bot.get_stranger_info(user_id=Request)
                nickname = stranger_info.get('nickname', '昵称获取失败')
                Request_List = [f"向“{nickname}”求婚中",f"被“{nickname}”求婚中"]
                Text = f"你当前正在{Request_List[Request_Mode]}\n请先通过“同意/拒绝求婚”或“取消求婚”命令作出决定后再试。"
            await matcher.finish(MessageSegment.reply(event.message_id)+f"{Text}")
        # 读取计数器信息，并进行次数限制判断
        Count_Json = Data[Self_QQ].get(group_id,False)
        logger.info(Count_Json)
        if Count_Json:
            Now = datetime.fromtimestamp(int(time.time()))
            Self_Time = datetime.fromtimestamp(Count_Json['time'])
            if Now.day != Self_Time.day or Now.month != Self_Time.month:
                logger.info("重置计数器")
                # 如果当前时间和上次请求时间不在同一天，则重置计数器
                Count_Json['count'] = 0
                Count_Json['switch'] = True
                logger.info("Reset")
            if Count_Json.get('switch',False):
                logger.info("获取Switch")
                Switch = Count_Json['switch']
            Count = Count_Json['count']
        if Count > 3:
            logger.info("已经达到了请求次数上限啦！本次跳过执行")
            if Switch:
                Count_Json['switch'] = False
                utils.handle_json(Marry_Count_Path, 'w', Count_Json)
                await matcher.finish(MessageSegment.reply(event.message_id)+"你已经结婚太多次了啦！第二天再结~\n（免打扰模式已开启，您在重置时间前只会看到此消息1次）")
            await matcher.finish()
    else:
        Master_Dict = {}
    
    # 初步生成排除列表，将已存在的key（即已经有对象的人）和bot以及用户加入到排除列表中，并转化为整数方便进行判断
    Exclusion_List = [int(key) for key in Data.keys() if Data[key].get(group_id,False) and Data[key][group_id].get("cp_qq", 0)]
    # 将bot和用户加入到排除列表中
    Exclusion_List.extend([event.self_id, event.user_id])
    # 生成群成员列表
    Group_User_List = await bot.call_api("get_group_member_list",group_id=event.group_id)
    # 生成随机取值的基列
    List = [x['user_id'] for x in Group_User_List if x['user_id'] not in Exclusion_List and not x['is_robot']]
    # 生成随机数，并获取对应的QQ号
    if len(List)-1 == 0:
        await matcher.finish(MessageSegment.reply(event.message_id)+"这个群好像没有其他人了呢...？")
    Random_Select = List[rd.randint(0,len(List)-1)]
    # 生成时间戳
    Time = int(time.time())
    # 构建Json文件，预备写入
    Random_Dict = {}
    logger.info(f"Debug:计数器：{Count}")
    Master_Dict[group_id] = {"cp_qq":Random_Select,"time":Time,"count":Count+1,"switch":True}
    Random_Dict[group_id] = {"cp_qq":event.user_id,"time":Time}
    # 将构建好的Json内容直接增加至上文中获取的Data和计数器Data中
    Data[f"{Random_Select}"] = Random_Dict
    Data[f"{Self_QQ}"] = Master_Dict
    # 写入文件
    utils.handle_json(Marry_Json_Path, 'w', Data)
    # 获取结束事件处理所必要的讯息
    stranger_info = await bot.get_stranger_info(user_id=Random_Select)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    Text = ""
    if Count == 2:
        Text = "不要老是换群友老婆啦笨蛋！\n"
    elif Count == 3:
        Text = "再换今天就不给你找群友老婆了！\n"
    # 结束事件处理
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{Text}好嗷~你已经和“{nickname}”【{Random_Select}】在一起了呢")


@Finish_Marry.handle()
@utils.handle_errors
async def FM_Function(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text():await matcher.finish()
    # 获取用户的QQ，并将值转为str格式
    Self_QQ = str(event.user_id)
    group_id = str(event.group_id)
    # 获取数据
    Data = utils.handle_json(Marry_Json_Path, 'r')
    self_data = Data.get(Self_QQ,False)
    # 异常处理
    if self_data and self_data.get(group_id) and self_data[group_id].get("cp_qq", 114514) == 114514:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你似乎还没有对象吧xwx")
    # 确定用户存在对象后，读取其对象的值
    logger.info(f"{self_data}\n{type(self_data)}")
    self_data = self_data[group_id]
    logger.info(self_data)
    # 获取对象的QQ号
    cp_qq = str(self_data['cp_qq'])
    cp_data = Data[cp_qq]
    logger.info(cp_data)
    stranger_info = await bot.get_stranger_info(user_id=cp_qq)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    Time_Text = utils.time_handle(self_data['time'])
    # 直接删除用户和用户对象json
    del Data[Self_QQ][group_id]["cp_qq"],Data[cp_qq][group_id]["cp_qq"]
    # 将处理完的Data写入文件
    utils.handle_json(Marry_Json_Path, 'w', Data)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"你已经和你的群友对象“{nickname}”[{cp_qq}]离婚了呢www\n在一起的时间：{Time_Text}")

@Marry_Propose.handle()
@utils.handle_errors
async def MP_Function(matcher:Matcher,event:MessageEvent,bot:Bot):
    # 获取数据
    Text = event.get_message()
    user_id,Bot_QQ,Self_QQ,Time,group_id = event.self_id,event.self_id,event.user_id,int(time.time()),str(event.group_id)
    # 获取at值
    for msg_seg in Text:
        if msg_seg.type == 'at':
            logger.info(msg_seg.data)
            user_id = str(msg_seg.data['qq'])
            break
    logger.info(user_id)
    IsRobot = await bot.get_group_member_info(group_id=event.group_id,user_id=user_id)
    if int(user_id) == int(Self_QQ) or int(user_id) == int(Bot_QQ) or IsRobot['is_robot']:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你你...你不可以向自己或者机器人求婚呢xwx")
    # 判断是否为非法请求
    # 获取请求值是否为tx机器人
    Temp = str(Text)
    if user_id == 0 or user_id == str(event.self_id):
        await matcher.finish(MessageSegment.reply(event.message_id)+"凌辉Bot似乎没能理解你要向谁求婚呢...是不是复制了别人的请求呀owo一定要自己@出来哦~/_ \\")
    if "CQ" not in Temp and "求婚" in Temp:
        await matcher.finish()
    Data = utils.handle_json(Marry_Json_Path, 'r')
    if Data.get(user_id,False) and Data[user_id].get(group_id,False) and Data[user_id][group_id].get("cp_qq",False):
        Text = "凌辉Bot小声提醒您：您请求的用户似乎已经有对象了awa"
        if Data[user_id][group_id].get("Request",False) != 0:
            Text = "凌辉Bot小声提醒您：您请求的用户似乎正在被求婚或者求婚其他人呢awa" 
        await matcher.finish(MessageSegment.reply(event.message_id)+Text)
    if Data.get(str(Self_QQ), {}).get(group_id, {}).get("cp_qq",114514) != 114514:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你已经有对象了啦qwq怎么可以一夫多妻呢/_ \\")
    if Data.get(str(Self_QQ), {}).get(group_id, {}).get("Request",0) != 0:
        Request = Data[str(Self_QQ)][group_id]['Request']
        stranger_info = await bot.get_stranger_info(user_id=Request)
        Request_Text = [f"向{stranger_info}求婚中",f"被{stranger_info}求婚中"]
        Requset_mode = Data[str(Self_QQ)][group_id]['Request_Mode']
        await matcher.finish(MessageSegment.reply(event.message_id)+f"你似乎正在{Request_Text[Requset_mode]}呢owo")
    # 获取或创建用户数据字典
    self_data = Data.setdefault(str(Self_QQ), {})
    request_data = Data.setdefault(str(user_id), {})
    self_count = self_data.get(group_id, {}).get("count", 0)
    cp_count = request_data.get(group_id, {}).get("count", 0)
    # 主动请求人的状态码为0，被请求人的状态码为1
    Self_Dict = {
        "cp_qq":114514,
        "Request":int(user_id),
        "time":Time,
        "Request_Mode":0,
        "count":self_count
    }
    Request_Dict = {
        "cp_qq":114514,
        "Request":Self_QQ,
        "time":Time,
        "Request_Mode":1,
        "count":cp_count
    }

    # 更新当前群组数据
    self_data[group_id] = Self_Dict
    request_data[group_id] = Request_Dict
    utils.handle_json(Marry_Json_Path, 'w', Data)
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    await matcher.finish(MessageSegment.reply(event.message_id)+f"好嗷~你已经向“{nickname}”求婚了哦^_~\n{nickname}[{int(user_id)}]可以通过“同意求婚”或“拒绝求婚”同意或者拒绝求婚请求w")

@Marry_Select.handle()
@utils.handle_errors
async def MS_Function(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    Text,Self_QQ,group_id = str(event.get_message()),str(event.user_id),str(event.group_id)
    Data = utils.handle_json(Marry_Json_Path, 'r')
    if Data.get(Self_QQ,{}).get(group_id,{}).get("Request",0) == 0:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你似乎没有被求婚或正在向他人求婚呢owo")
    if Data.get(Self_QQ).get(group_id).get('cp_qq',0) != 114514 and Data.get(Self_QQ).get(group_id).get('cp_qq',0) != 0:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你似乎已经有对象了吧...？")
    Request = Data[Self_QQ][group_id]['Request']
    Mode = Data[Self_QQ][group_id]["Request_Mode"]
    stranger_info = await bot.get_stranger_info(user_id=Request)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    if "拒绝" in Text or "取消" in Text:
        if not "取消" in Text:
            if Mode != 1:
                await matcher.finish(MessageSegment.reply(event.message_id)+"这个命令不是你用的吧owo")
        del Data[Self_QQ][group_id]["cp_qq"],Data[Self_QQ][group_id]["Request"],Data[Self_QQ][group_id]["Request_Mode"],Data[str(Request)][group_id]["cp_qq"],Data[str(Request)][group_id]["Request"],Data[str(Request)][group_id]["Request_Mode"]
        utils.handle_json(Marry_Json_Path, 'w', Data)
        Temp = "拒绝"
        Temp_1 = ""
        if "取消" in Text:
            Temp = "取消"
        if Mode == 0:
            Temp_1 = "对"
        await matcher.finish(MessageSegment.reply(event.message_id)+f"好叭/_ \\你已经{Temp}了{Temp_1}“{nickname}”的求婚请求了呢~")
    if Mode == 0 and "同意" in Text:
        await matcher.finish(MessageSegment.reply(event.message_id)+"这个命令不是你用的吧owo")
    Time = int(time.time())
    self_data = Data.setdefault(str(Self_QQ), {})
    request_data = Data.setdefault(str(str(Request)), {})
    self_count = self_data.get(group_id, {}).get("count", 0)
    cp_count = request_data.get(group_id, {}).get("count", 0)
    Self_Dict = {
        "cp_qq":Request,
        "Request":0,
        "time":Time,
        "Request_Mode":2,
        "count":self_count
    }
    Request_Dict = {
        "cp_qq":int(Self_QQ),
        "Request":0,
        "time":Time,
        "Request_Mode":2,
        "count":cp_count
    }
    # 获取或创建用户数据字典
    self_data = Data.setdefault(str(Self_QQ), {})
    request_data = Data.setdefault(str(Request), {})
    # 更新当前群组数据
    self_data[group_id] = Self_Dict
    request_data[group_id] = Request_Dict
    utils.handle_json(Marry_Json_Path, 'w', Data)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"好哦好哦~（拍爪子）你已经同意“{nickname}”的求婚请求了哦~")

@Marry_Time_Check.handle()
@utils.handle_errors
async def MTC_Function(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    Data = utils.handle_json(Marry_Json_Path, 'r')
    Self_QQ,group_id = str(event.user_id),str(event.group_id)
    if Data.get(Self_QQ) and Data[Self_QQ].get(group_id) and Data[Self_QQ][group_id].get("cp_qq", 114514) == 114514:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你似乎还没有对象吧xwx")
    user_id = Data[Self_QQ][group_id]['cp_qq']
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    Time_Text = utils.time_handle(Data[Self_QQ][group_id]['time'])
    await matcher.finish(MessageSegment.reply(event.message_id)+f"你和群友“{nickname}”[{int(user_id)}]已经在一起{Time_Text}了呢~")

@Marry_Check.handle()
@utils.handle_errors
async def MC_Function(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    # 读取前置数据
    Data = utils.handle_json(Marry_Json_Path, 'r')
    Self_QQ,group_id,user_id = str(event.user_id),str(event.group_id),0
    # 获取at值
    Text = event.get_message()
    for msg_seg in Text:
        if hasattr(msg_seg, 'type') and msg_seg.type == 'at':
            user_id = str(msg_seg.data.get('qq', 0))
            break
    if user_id != 0:
        Self_QQ = user_id
    Text = "你"
    # 安全获取嵌套值，避免异常
    user_data = Data.get(str(Self_QQ), {}).get(str(group_id), {})
    cp_qq = user_data.get("cp_qq",0)
    if cp_qq == 114514 or cp_qq == 0:
        logger.info(f"Debug:获取的cp_qq是{cp_qq}，用户id是{user_id}，群组id是{group_id}")
        if str(Self_QQ) != str(event.user_id):
            await matcher.finish(MessageSegment.reply(event.message_id) + "你查找的群友似乎还没有对象owo")
        await matcher.finish(MessageSegment.reply(event.message_id) + "你似乎还没有对象吧xwx")    # 确定用户合法后读取必要数据
    cp_qq,time = user_data['cp_qq'],user_data['time']
    # 转换为 datetime 对象
    dt_object = datetime.fromtimestamp(time)
    # 获取用户名
    stranger_info = await bot.get_stranger_info(user_id=int(cp_qq))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    # 获取自己的用户名
    if Self_QQ != str(event.user_id):
        stranger_info_self = await bot.get_stranger_info(user_id=int(Self_QQ))
        Text = stranger_info_self.get('nickname', '昵称获取失败')
    # 获取时间
    Time_Text = utils.time_handle(time)
    # 最终输出
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{Text}和“{nickname}”[{cp_qq}]在{dt_object.strftime('%Y-%m-%d %H:%M:%S')}时在一起了哦~\n一共在一起{Time_Text}了呢~")


@MarrySwitch.handle()
@utils.handle_errors
async def MarrySwitchutils(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    # 读取前置数据
    Data = utils.handle_json(Marry_Json_Path, 'r')
    Self_QQ = str(event.user_id)
    group_id = str(event.group_id)
    Count,Switch = 0,True
    if Data.get(Self_QQ,{}).get(group_id,{}).get("cp_qq", 0) != 0:
        # 获取对象的QQ号并删除两者的绑定关系
        cp_qq = str(Data[Self_QQ][group_id]['cp_qq'])
        del Data[cp_qq][group_id]["cp_qq"], Data[cp_qq][group_id]["time"], Data[Self_QQ][group_id]["cp_qq"], Data[Self_QQ][group_id]["time"]
        if Data.get(Self_QQ,{}).get(group_id,{}).get("cp_qq", 0) == 114514:
            Request = Data[Self_QQ][group_id]['Request']
            del Data[Request][group_id]["Request"], Data[Request][group_id]["Request_Mode"],Data[Self_QQ][group_id]["Request"], Data[Self_QQ][group_id]["Request_Mode"]
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text():await matcher.finish()
    # 读取json数据
    Data = utils.handle_json(Marry_Json_Path, 'r')
    # 将自己的QQ号转为str格式，方便后续判断
    Self_QQ = str(event.user_id)
    group_id = str(event.group_id)
    # 生成默认参数
    Switch = False
    Count = 0
    if Data.get(Self_QQ):
        Master_Dict = Data[Self_QQ]
        # 读取计数器信息，并进行次数限制判断
        Count_Json = Data[Self_QQ].get(group_id,False)
        logger.info(Count_Json)
        if Count_Json:
            Now = datetime.fromtimestamp(int(time.time()))
            Self_Time = datetime.fromtimestamp(Count_Json['time'])
            if Now.day != Self_Time.day or Now.month != Self_Time.month:
                logger.info("重置计数器")
                # 如果当前时间和上次请求时间不在同一天，则重置计数器
                Count_Json['count'] = 0
                Count_Json['switch'] = True
                logger.info("Reset")
            if Count_Json.get('switch',False):
                Switch = Count_Json['switch']
                logger.info(f"获取Switch：{Switch}")
            Count = Count_Json['count']
        if Count > 3:
            logger.info("已经达到了请求次数上限啦！本次跳过执行")
            if Switch:
                Count_Json['switch'] = False
                logger.info(f"写入数据：{Count_Json}")
                utils.handle_json(Marry_Json_Path, 'w', Count_Json)
                await matcher.finish(MessageSegment.reply(event.message_id)+"你已经结婚太多次了啦！第二天再结~\n（免打扰模式已开启，您在重置时间前只会看到此消息1次）")
            await matcher.finish()
    else:
        Master_Dict = {}
    
    # 初步生成排除列表，将已存在的key（即已经有对象的人）和bot以及用户加入到排除列表中，并转化为整数方便进行判断
    Exclusion_List = [int(key) for key in Data.keys() if Data[key].get(group_id,False) and Data[key][group_id].get("cp_qq", 0)]
    # 将bot和用户加入到排除列表中
    Exclusion_List.extend([event.self_id, event.user_id])
    # 生成群成员列表
    Group_User_List = await bot.call_api("get_group_member_list",group_id=event.group_id)
    # 生成随机取值的基列
    List = [x['user_id'] for x in Group_User_List if x['user_id'] not in Exclusion_List and not x['is_robot']]
    # 生成随机数，并获取对应的QQ号
    if len(List)-1 == 0:
        await matcher.finish(MessageSegment.reply(event.message_id)+"这个群好像没有其他人了呢...？")
    Random_Select = List[rd.randint(0,len(List)-1)]
    # 生成时间戳
    Time = int(time.time())
    # 构建Json文件，预备写入
    Random_Dict = {}
    logger.info(f"Debug:计数器：{Count}")
    Master_Dict[group_id] = {"cp_qq":Random_Select,"time":Time,"count":Count+1,"switch":True}
    Random_Dict[group_id] = {"cp_qq":event.user_id,"time":Time}
    # 将构建好的Json内容直接增加至上文中获取的Data和计数器Data中
    Data[f"{Random_Select}"] = Random_Dict
    Data[f"{Self_QQ}"] = Master_Dict
    # 写入文件
    utils.handle_json(Marry_Json_Path, 'w', Data)
    # 获取结束事件处理所必要的讯息
    stranger_info = await bot.get_stranger_info(user_id=Random_Select)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    Text = ""
    if Count == 2:
        Text = "不要老是换群友老婆啦笨蛋！\n"
    elif Count == 3:
        Text = "再换今天就不给你找群友老婆了！\n"
    # 结束事件处理
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{Text}好嗷~你已经和“{nickname}”【{Random_Select}】在一起了呢")
