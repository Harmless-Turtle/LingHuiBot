from nonebot.plugin import on_command  # 导入事件响应器
# 导入异常基类MatcherException，以限制try-except捕获正常finish函数抛出的异常
from nonebot.exception import MatcherException,ActionFailed
# 导入事件响应器以进行操作
from nonebot.adapters.onebot.v11 import (
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
    PrivateMessageEvent,
    FriendRequestEvent,
    GroupMessageEvent,
    GroupRequestEvent,
    PokeNotifyEvent,
    MessageSegment,
    MessageEvent,
    NoticeEvent,
    Message,
    Bot,
    )
from nonebot.matcher import Matcher
import Handler
from nonebot.rule import to_me,is_type,Rule
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
import json,time,requests,re,datetime,httpx
import random as rd
from pathlib import Path
from nonebot import logger, on_request,on_notice
from types import SimpleNamespace
from datetime import datetime as dt

# 定义Data存放路径并作为全局变量使用
path = Path.cwd() / 'data' / 'Main'
Poke_Path = path / "Poke_Text.json"
Welcome_Path = path / "Welcome_System.json"
AWord_Path = path / "AWord.json"
Sign_in_Path = path / "Sign_in" / "Sign_in.json"
Sign_in_Pic_True = path / "Sign_in" / "Background_True.png"
Sign_in_Pic_False = path / "Sign_in" / "Background_False.jpg"

async def check_bt(event: GroupMessageEvent):
    s = re.match(r'我是(.+)控', str(event.original_message))
    if s:
        return True
    else:
        return False

async def chek_boss(event:MessageEvent):
    if event.user_id == 1097740481:
        return True
    else:
        return False


async def chek_add_welcome(event:GroupIncreaseNoticeEvent):
    Welcome_Dict = Handler.handle_json(Welcome_Path, 'r')
    Group_id = str(event.group_id)
    logger.info(f"检查群 {Group_id} 的欢迎配置，当前数据：{Welcome_Dict.get(Group_id)}")
    if Welcome_Dict.get(Group_id,False):
        Group_Dict = Welcome_Dict[Group_id]
        logger.info(f"群 {Group_id} 的欢迎模式为：{Group_Dict.get('mode')}")
        return Group_Dict.get('mode')
    return False


async def ChekGroupMemberChange(event:GroupDecreaseNoticeEvent):
    try:
        Data = Handler.handle_json(f'{path}/GroupMemberChange.json', "r")
        logger.info(f"检查群 {event.group_id} 的退群通知开关，当前状态：{Data.get(str(event.group_id))}")
        return Data.get(str(event.group_id), False)
    except Exception as e:
        logger.error(f"读取退群通知配置失败：{e}")
        return False

async def add_group_switch(event:GroupRequestEvent):
    Data = Handler.handle_json(f'{path}/add_group_switch.json', "r")
    logger.info(Data.get(str(event.group_id), False))
    logger.info(event.sub_type == "add")
    return Data.get(str(event.group_id), False) and event.sub_type == "add"


#基础功能
Test = on_command("Test")
Sign_in = on_command("签到",aliases={"凌辉好久不见"},priority=2,block=True)
Poke_Check = on_notice(rule=to_me()&is_type(PokeNotifyEvent), priority=3,block=False)
Tarot = on_command("塔罗牌",priority=4,block=True)
AWord = on_command("一言",priority=4,block=True)
btfrk = on_command("我是",rule=check_bt)
Like = on_command("点赞",aliases={"赞我"},block=True)
Eat_What = on_command("今天吃什么")

# 入群检查
add_group = on_request(rule=add_group_switch)
switch_add_group = on_command("入群检测",permission=SUPERUSER,block=True)

#入群欢迎系统
Change_Welcome = on_command("入群欢迎",permission=SUPERUSER,block=True)
Change_Welcome_Text = on_command("修改欢迎",aliases={"欢迎文本","修改入群欢迎"},permission=SUPERUSER,block=True)

# 是否提示退群
Exit_Change = on_command("退群提示",aliases={"退群提醒","退群通知","退群检测"},block = True)

# 定义全局变量
Poke_Count = 0
Time_Count = time.time()
AT_Count = 0
AT_Time = time.time()


@Test.handle()
@Handler.handle_errors
async def Test_Function(matcher: Matcher,bot: Bot,event:MessageEvent, args: Message = CommandArg()):
    logger.info(await bot.get_group_member_info(group_id=event.group_id,user_id=event.self_id))
    raise RuntimeError("Test Function Error")  # 测试用的异常抛出


@Poke_Check.handle()
@Handler.handle_errors
async def PC_Function(matcher:Matcher,event: PokeNotifyEvent):
    global Poke_Count, Time_Count, Send
    if Poke_Count >= 3 and time.time()-Time_Count <= 120:
        if time.time()-Time_Count >= 120:
            Poke_Count = 0
            PC_Function()
        else:
            if Send:
                Send = False
                await matcher.finish("呜呜...不可以再捏了~（2分钟后可以继续捏~）")
            else:
                pass
    else:
        Send = True
        Text_List = Handler.handle_json(Poke_Path, 'r')
            
        Poke_Count += 1
        Time_Count = time.time()
        Choise_Text = Text_List[rd.randint(0, len(Text_List)-1)]
        await matcher.finish(f"{Choise_Text}")

@Tarot.handle()
@Handler.handle_errors
async def Tarot_Function(matcher:Matcher,event: MessageEvent):
    get = requests.get("https://oiapi.net/API/Tarot").json()
    if get['code'] != 1:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"遇到错误：{get['message']}[{get['code']}]")
    data = get['data']
    send = data[rd.randint(0, len(data)-1)]
    meaning = send['meaning']
    name_cn = send['name_cn']
    position = send['type']
    position_meaning = send[f"{position}"]
    pic_URL = send['pic']
    await matcher.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(pic_URL)+f"""你抽到了{name_cn}
这张牌的意思是：{meaning}，方位是{position}
这个牌的方位解释为：{position_meaning}""")


Add_Welcome = on_notice(rule=is_type(GroupIncreaseNoticeEvent) & Rule(chek_add_welcome),priority=1,block=True)
@Add_Welcome.handle()
@Handler.handle_errors
async def Welcome(matcher:Matcher,event=GroupIncreaseNoticeEvent):
    if event.user_id == event.self_id:await matcher.finish()
    Welcome_Dict = Handler.handle_json(Welcome_Path, 'r')
    Group_id = str(event.group_id)
    if Welcome_Dict.get(Group_id,False):
        Group_Dict = Welcome_Dict[f'{Group_id}']
        if not Group_Dict['mode']:
            await matcher.finish()
        if Group_Dict.get("Text",False):
            Return_Text = Welcome_Dict[f"{Group_id}"]['Text']
            await matcher.finish(f"{Return_Text}")
        else:
            await matcher.finish("新人记得给群主早上请安晚上侍寝（bushi\n欢迎新成员加入本群！凌辉Bot欢迎您~\nWelcome new members to join this family! Linghui Bot welcomes you~")
    else:
        await matcher.finish()

SelfJoinGroupWelcome = on_notice(rule=is_type(GroupIncreaseNoticeEvent),priority=1,block=True)
@SelfJoinGroupWelcome.handle()
@Handler.handle_errors
async def SelfJoinGroupWelcome_Function(matcher:Matcher,event=GroupIncreaseNoticeEvent):
    if event.user_id == event.self_id:await Matcher.finish("嗷呜~感谢您使用凌辉Bot~我可以给你提供Furry的相关功能，以及一些其他的功能哦~\n如果您想要了解更多功能，请输入“菜单”来获取帮助信息哦~\n如果您担心与群里其他Bot的命令冲突，可以通过“凌辉菜单”来使用菜单哦www~希望您能喜欢我~\n如果您有任何问题，请随时联系管理员[1097740481]哦~")
    else:
        pass

@Change_Welcome.handle()
@Handler.handle_errors
async def Change_Welcome_Function(matcher:Matcher,event:GroupMessageEvent,Recivce:MessageEvent):
    Dict = Handler.handle_json(Welcome_Path, 'r')
    Group_id = str(event.group_id)
    args = Recivce.get_message()
    if "开" in str(args):
        Dict[Group_id] = {"mode":None,"Text":None}
        Dict[Group_id]['mode'] = True
        if not Dict[Group_id].get('Text',False):
            Dict[Group_id]['Text'] = "新人记得给群主早上请安晚上侍寝（bushi\n欢迎新成员加入本群！凌辉Bot欢迎您~\nWelcome new members to join this family! Linghui Bot welcomes you~"
    elif "关" in str(args):
        if not Dict.get(Group_id,False):
            await matcher.finish(MessageSegment.reply(event.message_id)+"本群似乎还没有创建过入群欢迎的任务，请先通过“入群欢迎开”的命令来创建哦w")
        Dict[Group_id]["mode"] = False
    else:
        Mode = None
        Text = "未启动"
        if Dict.get(f"{Group_id}",False):
            Mode = Dict[Group_id]["mode"]
            if not Dict[Group_id].get('Text',False):
                Text = "新人记得给群主早上请安晚上侍寝（bushi\n欢迎新成员加入本群！凌辉Bot欢迎您~\nWelcome new members to join this family! Linghui Bot welcomes you~"
            else:
                Text = Dict[Group_id]['Text']
        Mode_Text = "关闭"
        if Mode:
            Mode_Text = "开启"
        elif Mode==None:
            Mode_Text = "未启动"
        await matcher.finish(MessageSegment.reply(event.message_id)+f"当前群聊的入群欢迎状态为：{Mode_Text}\n新人入群欢迎文本：{Text}")
    Handler.handle_json(Welcome_Path, 'w', Dict)
    await matcher.finish(MessageSegment.reply(event.message_id)+"操作成功完成。")

@Change_Welcome_Text.handle()
@Handler.handle_errors
async def CWT_Function(matcher:Matcher,event:MessageEvent,args:Message = CommandArg()):
    args = str(args)
    Dict = Handler.handle_json(Welcome_Path, 'r')
    Group = str(event.group_id)
    Text = ""
    if not Dict.get(Group,False):
        Text = "由于未创建入群欢迎任务，所以本次操作将自动打开本群的入群欢迎提示~\n"
    New_Dict = {
        f"{Group}":{
            "mode":True,
            "Text":args
            }
    }
    Dict.update(New_Dict)
    Text_1 = "入群文本已经成功替换啦~"
    if args == "":
        Dict[Group]['Text'] = "新人记得给群主早上请安晚上侍寝（bushi\n欢迎新成员加入本群！凌辉Bot欢迎您~\nWelcome new members to join this family! Linghui Bot welcomes you~"
        Text_1 = "由于未找到对应的文本，所以本次操作将会使用默认文本来进行入群欢迎~"
    Handler.handle_json(Welcome_Path, 'w', Dict)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{Text}{Text_1}")        

@AWord.handle()
@Handler.handle_errors
async def AWord_Function(matcher:Matcher,event=MessageEvent,args:Message = CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    Dict = Handler.handle_json(AWord_Path, 'r')
        
    Result = Dict[rd.randint(0,len(Dict)-1)]
    await matcher.finish(MessageSegment.reply(event.message_id)+f"“{Result}”")

#签到触发器与实现
@Sign_in.handle()
@Handler.handle_errors
async def Sign_in_Function(matcher:Matcher,event:MessageEvent,GroupEvent:GroupMessageEvent,args:Message=CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    # 打开文件并写入Sign_Dict字典
    Sign_Dict = Handler.handle_json(Sign_in_Path, 'r')

    # 获取触发人QQ号和群聊号
    User,Group = event.user_id,GroupEvent.group_id
    # 获取触发时间
    from datetime import date
    Time_Normal = str(date.today())
    Time_Normal = Time_Normal.split("-")         #切片->构建基本时间
    Time = int(Time_Normal[-1])        # 获取签到天数
    Month = int(Time_Normal[-2])       # 获取签到月份
    # 生成默认参数
    Group_Time,Group_Month,Group_Count,Group_User_List = Time,Month,0,{}
    User_Time,User_Count,User_Month,Text,User_Greenwich_Time = Time,0,Month,"",0
    # 判断：群聊是否已经存在数据
    if Sign_Dict.get(f"{Group}"):    #如果存在数据，则读取它，顺便处理。
        logger.info("找到群聊数据，开始处理")
        Group_Dict = Sign_Dict[f'{Group}']
        Group_Time,Group_Month,Group_Count,Group_User_List = Group_Dict['Time'],Group_Dict['Month'],Group_Dict['Count'],Group_Dict['User_Dict']
        # 判断：群聊最后一次签到时间是否已经超过一天
        if Time != Group_Time:    #如果已经超过了一天，则重置状态。
            Group_Time,Group_Month,Group_Count = Time,Month,0
        elif Month != Group_Month:
            Group_Time,Group_Month,Group_Count,Group_User_List = Time,Month,0,{}
        # 判断：数据内是否已经存在了用户数据
        if Group_User_List.get(str(User)):    #如果不为空，则读取数据
            logger.info("找到个人数据，开始处理")
            User_Dict = Group_User_List.get(str(User))
            User_Time,User_Count,User_Month,User_Greenwich_Time = User_Dict["Time"],User_Dict['Count'],User_Dict["Month"],User_Dict['Greenwich_Time']
            if Time == User_Time and Month == User_Month:
                await matcher.finish(MessageSegment.reply(event.message_id)+"你今天已经在本群签到啦~")
        # 判断：用户最后一次签到时间是否已超过一个月
        if User_Month != Month:    #如果已经超过了一个月，则重置状态
            User_Time,User_Count,User_Month = Time,0,Month
    # 处理数据
    Group_Count += 1
    User_Count += 1
    Greenwich_Time = int(time.time())
    # 构建信息
    New_Sign_User_Dict = {
        "Count":User_Count,
        "Time":Time,
        "Month":Month,
        "Greenwich_Time":Greenwich_Time
    }
    New_Sign_Group_Dict = {
        "Time":Group_Time,
        "Count":Group_Count,
        "Month":Group_Month,
        "User_Dict":Group_User_List
    }
    Group_User_List[f"{User}"] = New_Sign_User_Dict
    Sign_Dict[f'{Group}'] = New_Sign_Group_Dict
    # 将构建完成的信息写入本地json文件进行保存
    Handler.handle_json(Sign_in_Path, 'w', Sign_Dict)
    AwordDict = Handler.handle_json(AWord_Path, 'r')
    Result = AwordDict[rd.randint(0,len(AwordDict)-1)]
    # 判断：调用是否出现“好久不见”字样
    if "好久不见" in str(event.message):
        #生成检测到“好久不见”字样的默认值
        Text = "诶...好像也没有太久吧~是不是记错时间了呀~\n"
        pic = Sign_in_Pic_False
        # 判断：如果读取用户的格林威治时间戳减去当前时间戳大于或等于259200秒（即3天整），则更改输出条件。
        if (Greenwich_Time - User_Greenwich_Time) >= 259200:
            Text = "确实好久不见了诶~抱抱~\n"
            pic = Sign_in_Pic_True
        # 输出
        maomao = rd.randint(5,10)
        await matcher.finish(MessageSegment.reply(event.message_id)+MessageSegment.image(pic)+f"{Text}签到成功。本月在本群中已签到{User_Count}次，今天在本群中排名第{Group_Count}位~\n[DEBUG]{maomao}\n——————\n“{Result}”")
    # 输出
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{Text}签到成功。您本月在本群中已签到{User_Count}次，今天在本群中排名第{Group_Count}位。\n——————\n“{Result}”")

@btfrk.handle()
@Handler.handle_errors
async def wc_btfrk(bot:Bot,matcher:Matcher,event:MessageEvent):
    match = re.search(r"我是(.+)控", str(event.original_message))
    members = await bot.get_group_member_list(group_id=event.group_id)
    if len(match.group(1)) < 2 or match.group(1) in ['福瑞','furry','Furry','兽人','售人']:await matcher.finish()
    List = [item for member in members if not member['is_robot'] for item in (member["nickname"],member['card'],member["title"]) if not item==""]
    Select = None
    # logger.info(List)
    for name in List:
        if match.group(1) in name:
            Select = name
    if Select == None:
        await matcher.finish("未找到")
    for i in members:
        if i['nickname']==Select or i['card'] == Select or i['title'] == Select:
            Select_QQ = i['user_id']
    user_card = MessageSegment.contact_user(f"{Select_QQ}")
    message = Message([
        MessageSegment.text("推荐用户"),
        user_card
    ])
    await bot.send(event, message)

@Exit_Change.handle()
@Handler.handle_errors
async def Change_Exit_Function(matcher:Matcher,event:MessageEvent,args:Message=CommandArg()):
    args = str(args)
    Data = Handler.handle_json(f'{path}/GroupMemberChange.json', "r")
    Temp_1,write = "",None
    if "开" in args:
        write = True
        Temp = "打开"
        Temp_1 = "当有人退群时会发出消息提示哦~"
    elif "关" in args:
        write = False
        Temp = "关闭"
    else:
        Text = "本群的退群通知是关闭状态捏"
        if Data.get(f"{event.group_id}",False):
            if Data[f'{event.group_id}']:
                Text = "本群的退群通知是打开状态捏"
        await matcher.finish(MessageSegment.reply(event.message_id)+f"{Text}~\n输入“退群提示关”或“退群提示开”来更改功能开关")
    logger.info(args)
    Data[f'{event.group_id}']=write
    Handler.handle_json(f'{path}/GroupMemberChange.json', "w", Data)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"好~凌辉Bot已经{Temp}了本群的退群提示w~{Temp_1}")

# 检查群成员减少事件
GroupExitMember = on_notice(
    rule=Rule(ChekGroupMemberChange) & is_type(GroupDecreaseNoticeEvent),
    priority=1,
    block=True
)

@GroupExitMember.handle()
@Handler.handle_errors
async def handle_group_decrease(event: GroupDecreaseNoticeEvent, bot: Bot, matcher: Matcher):
    logger.info(f"触发退群事件：{event.dict()}")
    # 处理 Bot 自己被踢的情况
    if event.sub_type == "kick_me":
        await bot.send_private_msg(
            user_id=1097740481,
            message=f"⚠️ Bot被踢出群聊！\n"
                    f"时间：{dt.fromtimestamp(event.time).strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"群号：{event.group_id}"
        )
        await matcher.finish()
    # 获取用户信息
    nickname = "未知用户"
    try:
        user_info = await bot.get_stranger_info(user_id=event.user_id)
        nickname = user_info.get("nickname", "未知用户")
    except ActionFailed:
        nickname = "信息获取失败"
    
    # 处理退群原因
    if event.sub_type == "kick":
        operator_id = getattr(event, "operator_id", 0)
        if operator_id > 0:
            # 尝试获取操作者信息
            try:
                operator_info = await bot.get_group_member_info(
                    group_id=event.group_id,
                    user_id=operator_id
                )
                operator_name = operator_info.get("nickname", str(operator_id))
            except ActionFailed:
                operator_name = str(operator_id)
            reason = f"被管理员 {operator_name} 移出"
        else:
            reason = "被管理员移出"  # 无权限时的通用描述
    elif event.sub_type == "leave":
        reason = "主动退群"
    else:
        reason = "未知原因"
    
    # 构造消息
    message = Message(
        f"似乎有人离开了我们...？"
        f"时间：{dt.fromtimestamp(event.time).strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"用户：{nickname} ({event.user_id})\n"
        f"原因：{reason}"
    )
    
    # 发送到群聊
    await bot.send_group_msg(
        group_id=event.group_id,
        message=message
    )


async def chekFriendLike(event:NoticeEvent):
    Data = event.model_dump()
    Data_sn = SimpleNamespace(**Data)
    if getattr(Data_sn,"sub_type",False):
        if Data['sub_type'] == "profile_like":
            return True
        else:
            return False
    else:
        return False

# 被点赞事件监测
Like_Friend = on_notice(rule=is_type(NoticeEvent)&chekFriendLike)

@Like_Friend.handle()
@Handler.handle_errors
async def LF_Function(matcher:Matcher,event:NoticeEvent):
    from nonebot import get_bot
    bot = get_bot()
    Data = event.model_dump()
    Dict = Handler.handle_json(f"{path}/Friend_Like.json", 'r')
    user_id = Data['operator_id']
    now = dt.now()
    day = now.day
    Dict_day = day
    if not Dict.get(f"{user_id}",False):
        Dict[f"{user_id}"] = {'Model':True,"Time":Dict_day}
        logger.info("新建用户数据！")
    Dict_day = Dict[f"{user_id}"]['Time']
    if day != Dict_day:
        Dict[f"{user_id}"]['Time'] = day
        Dict[f"{user_id}"]['Model'] = True
        logger.info("不是同一天，进行覆写！")
    Model = Dict[f"{user_id}"]['Model']
    if not Model:
        await matcher.finish()
    try:
        await bot.send_like(user_id=user_id,times=10)
    except ActionFailed:
        pass
    Text = f"owo？是你给我点赞了嘛~谢谢~\n凌辉也给你点赞哦~（如果已经点过了那就不点了呐~嘻嘻ww）"
    Dict[f"{user_id}"]['Model'] = False
    Dict[f"{user_id}"]['Time'] = day
    Handler.handle_json(f"{path}/Friend_Like.json", 'w', Dict)
    try:
        if user_id != 1097740481:
            await bot.send_private_msg(user_id=user_id,message=Text)
            logger.info("已经回赞完毕")
    except ActionFailed:
        logger.error(f"发送点赞消息失败，可能是因为没有添加好友")
        

# 加好友事件请求
Add_Friend = on_request(rule=is_type(FriendRequestEvent),priority=1, block=True)

@Add_Friend.handle()
@Handler.handle_errors
async def AF_Function(bot:Bot,matcher:Matcher,event:FriendRequestEvent):
    request_type,user_id,flag,comment = event.request_type,event.user_id,event.flag,event.comment
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    Text = f"发现新用户试图添加Bot为好友，请查看参数后决定是否批准Bot添加好友。\n用户参数如下：\n加好友请求来源：{request_type}\nQQ资料卡昵称：{nickname}\nQQ号：{user_id}\n加好友理由：{comment}\n请求唯一id号：{flag}\n您可以通过“同意{flag}”或“拒绝{flag}”来处理此请求。"
    await bot.send_private_msg(user_id=1097740481,message=Text)
    await matcher.finish()

async def chekFriend(event:PrivateMessageEvent):
    if event.message_type != "private":
        return False
    else:
        return True

# 处理是否同意加好友
Choice_Friend = on_command("同意",rule=chekFriend,permission=SUPERUSER,aliases={"拒绝"},block=True)

@Choice_Friend.handle()
async def CF_Function(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message=CommandArg()):
    if "同意" in str(event.get_message):
        Select = True
    elif "拒绝" in str(event.get_message):
        Select = False
    else:
        await matcher.finish(MessageSegment.reply(event.message_id)+"命令不正确")
    try:
        await bot.set_friend_add_request(flag=str(args),approve=Select)
        await matcher.finish(MessageSegment.reply(event.message_id)+"已经处理了此好友请求。")
    except ActionFailed:
        await matcher.finish(MessageSegment.reply(event.message_id)+"未找到对应的flag，请检查flag是否正确。")

@Like.handle()
async def Like_Function(bot:Bot,matcher:Matcher,event:MessageEvent,args:Message=CommandArg()):
    if args.extract_plain_text():await matcher.finish()    # 若消息后面存在文本则不响应
    try:
        Random_Number = rd.randint(1,10)
        await bot.send_like(user_id=event.user_id,times=10)
        if Random_Number == 1:
            await matcher.finish(MessageSegment.reply(event.message_id)+"诶嘿~我不点ww~")
        else:
            await matcher.finish(MessageSegment.reply(event.message_id)+"好好~给你点~但是我一天最多只能点10个哦w")
    except ActionFailed:
        await matcher.finish(MessageSegment.reply(event.message_id)+"凌辉今天已经给你点过赞了啦qwq...不能再点了哦~")

@Eat_What.handle()
async def Eat_Function(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message = CommandArg()):
    if str(args) != "":
        List = await bot.get_group_member_list(group_id=event.group_id)
        Random_Choice = List[rd.randint(0,len(List)-1)]
        Name = Random_Choice['nickname']
        user_id = Random_Choice['user_id']
        await matcher.finish(MessageSegment.reply(event.message_id)+f"那...就吃{Name}（{user_id}）吧！（坏笑")
    a = httpx.get("https://zj.v.api.aa1.cn/api/eats/",timeout=None,verify=False)
    if a.status_code != 200:
        await matcher.finish(MessageSegment.reply(event.messgae_id)+f"好像没有访问成功...？[HTTP {a.status_code}]")
    a = a.json()
    if a['code'] != 200:
        msg = a['msg']
        code = a['code']
        await matcher.finish(MessageSegment.reply(event.message_id)+f"好像没有获取到QAQ...{msg}[{code}]")
    Random_Number = rd.randint(1,2)
    Select = a[f'meal{Random_Number}']
    await matcher.finish(MessageSegment.reply(event.message_id)+f"{a['mealwhat']}\n要不{Select}吧！")

@add_group.handle()
@Handler.handle_errors
async def handle_add_group(matcher:Matcher,bot:Bot,event:GroupRequestEvent):
    User = await bot.get_stranger_info(group_id=event.group_id,user_id=event.user_id)
    User = User["nick"]
    Data = Handler.handle_json(f'{path}/add_group_switch.json', 'r')
    if Data.get(str(event.group_id),False):
        flag_list = Data[str(event.group_id)]
    else:
        flag_list = [event.flag]
    # Dict = {event.group_id:flag_list}
    # Handler.load_json(f'{path}/add_group_switch.json','w',Dict)
    comment = event.comment
    if comment == "":
        comment = "未填写入群理由"
    ban_text = "死全家滚开去死废渣傻逼脑残智障败贱货垃圾杂种操你妈"
    if comment in ban_text:
        await bot.set_group_add_request(flag=str(event.flag),approve=False,reason="你的申请存在违禁词库中,请修改后重新申请。")
        await matcher.finish(f"似乎有人想要加入我们awa...\n请求类型：{event.request_type}\n子类型：{event.sub_type}\n申请人信息：{User}[{event.user_id}]\n进群理由:\n（思考）...？似乎在凌辉的内置禁止词库中？\n⚠️已满足判决条件；自动处理生效，将主动拒绝此入群消息！\n如果要手动同意，请关闭入群审核功能后让用户重新申请。")
    await matcher.finish(f"似乎有人想要加入我们awa...\n请求类型：{event.request_type}\n子类型：{event.sub_type}\n申请人信息：{User}[{event.user_id}]\n进群理由:{event.comment}\n要同意此人入群嘛awa？\n可以通过“允许加群{event.flag}”或“拒绝加群{event.flag}”来处理此请求（请在Bot为群管理员时进行操作~")

@switch_add_group.handle()
async def handler_switch_add_group(matcher:Matcher,event:MessageEvent,args:Message=CommandArg()):
    args = str(args)
    Data = Handler.handle_json(f'{path}/add_group_switch.json', 'r')
    if "开" in args:
        write = True
        Temp = "打开"
    elif "关" in args:
        write = False
        Temp = "关闭"
    else:
        Text = "当前Bot的入群检测状态为：关闭"
        if Data.get(str(event.group_id),False):
            if Data[str(event.group_id)]:
                Text = "当前Bot的入群检测状态为：开启"
        await matcher.finish(MessageSegment.reply(event.message_id)+f"{Text}~\n输入“入群检测开”或“入群检测关”来更改功能开关")
    Data[str(event.group_id)] = write
    Handler.handle_json(f'{path}/add_group_switch.json', 'w', Data)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"好~凌辉Bot已经{Temp}了本群的入群检测功能w~")

handle_group = on_command("允许加群",aliases={"拒绝加群"},block=True)
@handle_group.handle()
async def handle_add_group(matcher:Matcher,event:MessageEvent,bot:Bot,args:Message=CommandArg()):
    User = await bot.get_group_member_info(group_id=event.group_id,user_id=event.self_id)
    logger.info(User)
    if User['role']=='member':
        await matcher.finish(MessageSegment.reply(event.message_id)+"请先将Bot设置为管理员哦~")
    if "允许" in str(event.get_message):
        Select = True
    elif "拒绝" in str(event.get_message):
        Select = False
    else:
        await matcher.finish(MessageSegment.reply(event.message_id)+"命令不正确")
    try:
        await bot.set_group_add_request(flag=str(args),approve=Select,reason="管理员拒绝通过。")
        await matcher.finish(MessageSegment.reply(event.message_id)+"已经处理了此请求。")
    except ActionFailed:
        await matcher.finish(MessageSegment.reply(event.message_id)+"未找到对应的flag，请检查flag是否正确。")