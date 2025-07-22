# 标准库
import asyncio,json,os,shutil,time,httpx,math,stat

from .Handler import Handler
# 第三方库
from types import SimpleNamespace
from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message,
    Bot,
)
from nonebot.matcher import Matcher
from nonebot.plugin import on_command
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from nonebot import get_driver


# 定义全局变量
login_cookie = {}
timeout = None
count = 0
set_count = 0
api_base = "https://cloud.foxtail.cn/api"
token,account,password = "未获取到数据", "未获取到数据", "未获取到数据"
# 从.env.dev中读取配置项
config = get_driver().config
try:
    token = config.furry_token
    account = config.furry_user
    password = config.furry_password
    logger.success("✅已成功加载Furry模块的相关配置！")
except:
    logger.warning("请注意，当前功能受限制！")
    logger.warning("您没有填写token/account/password，这将导致“投图”功能不可用！")
    logger.info(f"获取到的信息：\ntoken：{token}\naccount：{account}\npassword：{password}\napi_base：{api_base}")
    logger.warning("请确保.env.dev文件中具有如下内容：\nFURRY_TOKEN=您的token\nFURRY_USER=您的账号\nFURRY_PASSWORD=您的密码")


# 定义Data存放路径并作为全局变量使用
opendata = Path.cwd()
Data_Path = opendata / 'data' / 'Furry_System' / 'Upload'
Font_Path = opendata / 'data' / 'MiSans-Demibold.ttf'
Pic_URL = opendata / 'data' / 'temp.jpg'
allin_pic_prerequisite_path = opendata / 'data' / 'Furry_System' / 'processed_images'

# 定义事件响应器

# Foxtail-Furry 兽云祭服务
RanFurry = on_command(
    "来只兽兽", aliases={"来只毛", "来只", "来只兽"}, priority=10, block=True)  # 随机兽图
PicFurry = on_command("指定", aliases={"指定#"}, priority=10, block=True)  # 指定兽图
UploadFurry = on_command(
    "一键上传", aliases={"投图", "管理员上传"}, priority=10, block=True)  # 上传图片
Batch_Upload = on_command("批量投图",aliases={"批量上传"},block=True)      #批量投图图片
Batch_Set = on_command("定义#",aliases={"定义"},priority=10,block=True)
Debugger_Upload = on_command("调试",aliases={"上传调试","上图调试"},priority=1,permission=SUPERUSER)
FurryList = on_command(
    "查列表", aliases={"查列表#", "查兽兽"}, priority=10, block=True)  # 获取列表
Modify_Furry = on_command(
    "修改图片", priority=99, block=True, permission=SUPERUSER)  # 修改图片信息
Furry_status = on_command(
    "兽图状态", aliases={"兽图状态#"}, priority=10, block=True)  # 兽图状态
Service_Status = on_command(
    "服务器状态", aliases={"兽云祭信息", "兽云祭状态", "服务状态"}, priority=10, block=True)  # 获取服务器信息
# See_Furry = on_command("鉴毛")
# 投图审核系统->仅NoneBot SUPERUSER组可用
Check_Upload = on_command(
    "待审核列表", aliases={"审核列表", "上传列表"}, priority=100, block=True, permission=SUPERUSER)  # 获取审核列表
Check_Upload_Decide = on_command(
    "同意上传#", aliases={"同意上载#", "拒绝上传#", "拒绝上载#"}, priority=99, block=True, permission=SUPERUSER)  # 决定是否上传
# Batch_Check = on_command("批量审核",aliases={"批量上传"},priority=98,block=True,permission=SUPERUSER)
Upload_Clear = on_command("清空上传数据",aliases={"清除上传"},permission=SUPERUSER)
# login_account = on_command("登录Fur",permission=SUPERUSER)

# FurryFusion 兽聚汇总服务
FurryFusion_List = on_command(
    "今年兽聚", aliases={"兽聚列表", "兽聚汇总"}, priority=10, block=True)
FurryFusion_Check = on_command("兽聚查询", block=True) 
FurryFusion_countdown = on_command("兽聚倒计时", block=True)
FurryFusion_Quick_Information = on_command("兽聚快讯#", block=True)
FurryFusion_Information = on_command("兽聚信息", aliases={"兽聚详情"}, block=True)

@RanFurry.handle()
@Handler.handle_errors
async def RanFur_handle_function(matcher:Matcher,event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    if args == "":
        data = httpx.get(f"{api_base}/function/random")  # 发起Get请求获取一张随机毛图
    else:
        try:
            data = httpx.get(f"{api_base}/function/pictures?picture={int(args)}&model=1",timeout=timeout,verify=False)
        except ValueError:
            data = httpx.get(f"{api_base}/function/random?name={args}",timeout=timeout)
    if data.status_code != 200:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"凌辉似乎没有获取到要下载的图片qwq...[HTTP {data.status_code}]")
    data = data.json()  # 将获取到的request请求转为Json格式
    Code = data["code"]  # 获取数据中的code变量，即状态码
    msg = data["msg"]  # 获取数据中的msg变量，即信息
    if Code == "20600":
        url = data['url']
        name = data['name']
        suggest = data['suggest']  # 获取download字段中suggest变量，即该图片的留言信息。
        if suggest != "":  # 如果留言不为空
            suggest = f"它的留言是“{suggest}”\n"
        id = data['id']  # 获取download字段中的id变量，即该图片的数字id
        await matcher.finish(MessageSegment.reply(event.message_id)+f"这只兽兽叫“{name}”~\n{suggest}图片码为：{id}\n"+MessageSegment.image(url))
    elif Code != "20900":  # 如果状态码不为20900（即获取失败）
        await matcher.finish(MessageSegment.reply(event.message_id)+f"好像哪里不对...？\n错误信息：{msg}[Code:{Code}]")
    data = data['picture']  # 获取data中的picture变量，即图片详细信息
    Picture = data['picture']  # 获取data字段中的picture变量，即图片唯一识别码
    # 发起POST请求以获取数据，将数据传入给download变量，转为Json格式
    download = httpx.post(
        f"{api_base}/function/pictures?picture={Picture}&model=",timeout=timeout)
    if download.status_code != 200:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"凌辉似乎没有获取到要下载的图片qwq...\n[HTTP {download.status_code}]")
    download = download.json()
    name = download['name']  # 获取download字段中的name变量，即该兽兽的名字
    id = download['id']  # 获取download字段中的id变量，即该图片的数字id
    url = download['url']  # 获取download字段中的url变量，即该图片的临时URL
    suggest = download['suggest']  # 获取download字段中suggest变量，即该图片的留言信息。
    if suggest != "":  # 如果留言不为空
        suggest = f"它的留言是：“{suggest}”\n"
    # 输出正常的信息。
    await matcher.finish(MessageSegment.reply(event.message_id)+f"这只兽兽叫“{name}”~\n{suggest}图片码为：{id}\n"+MessageSegment.image(url))


# 使用PicFurry响应器的handle装饰器装饰函数PicFur_handle_function

@PicFurry.handle()
@Handler.handle_errors
async def PicFur_handle_function(matcher:Matcher,event: MessageEvent, args: Message = CommandArg()):
    sid = str(args)
    if sid == "":
        await matcher.finish(MessageSegment.reply(event.message_id)+f"凌辉似乎没有获取到要查找的图片qwq...麻烦你再看看有没有正确使用呢owo")
    else:
        # 发起Get请求获取一张指定sid的毛图
        data = httpx.get(f"{api_base}/function/pictures?picture={sid}&model=1",timeout=timeout)
        if data.status_code != 200:
            await matcher.finish(MessageSegment.reply(event.message_id)+f"凌辉好像没有获取到图片信息捏qwq...[HTTP {data.status_code}]")
        data = data.json()  # 将获取到的request请求转为Json格式
        Code = data["code"]  # 获取数据中的code变量，即状态码
        msg = data["msg"]  # 获取数据中的msg变量，即信息
        if Code != "20600":  # 如果状态码不为20600（即获取失败）----->↓
            # 则输出错误
            await matcher.finish(MessageSegment.reply(event.message_id)+f"好像哪里不对...？\n错误信息：{msg}[Code:{Code}]")
        else:  # 如果状态码为20600（即获取成功），则执行else下命令（处理数据）
            url = data['url']  # 获取data中的picture变量，即图片详细信息
            id = data['id']  # 获取data字段中的picture变量，即图片唯一识别码
            name = data['name']  # 获取data字段中的name变量，即图片名称
            suggest = data['suggest']
            if suggest != "":  # 如果留言不为空
                suggest = f"它的留言是：“{suggest}”\n"
            # 输出正常的信息。
            await matcher.finish(MessageSegment.reply(event.message_id)+f"这只兽兽叫“{name}”~\n{suggest}图片码为：{id}\n"+MessageSegment.image(url))

@UploadFurry.handle()
@Handler.handle_errors
async def Upload_Furry_handle(matcher:Matcher, event: MessageEvent,bot: Bot, group: GroupMessageEvent, args: Message = CommandArg()):
    data = str(args).split("#")
    if not os.path.exists(Data_Path):
        os.makedirs(Data_Path)
    if len(data) != 5:
        await matcher.finish(MessageSegment.reply(event.message_id)+"错误：请按照#名字#类型#留言#图片的格式重新上传\n（类型：数字0为设定，1为毛图，2为插画")
    else:
        Name = data[1]
        Type = data[2]
        Suggest = data[3]
        pic = data[4]
        # 对传入参数进行判定
        if Name == "":
            await matcher.finish(MessageSegment.reply(event.message_id)+"错误：您似乎并没有填写名字，请按照#名字#类型#留言#图片的格式重新上传\n（类型：数字0为设定，1为毛图，2为插画")
        elif Type == "":
            await matcher.finish(MessageSegment.reply(event.message_id)+"错误：您似乎并没有填写类型，请按照#名字#类型#留言#图片的格式重新上传\n（类型：数字0为设定，1为毛图，2为插画")
        elif pic == "":
            await matcher.finish(MessageSegment.reply(event.message_id)+"错误：您似乎并没有发送图片，请按照#名字#类型#留言#图片的格式重新上传")
        if not Type.isdigit():
            await matcher.finish(MessageSegment.reply(event.message_id)+"遇到问题：类型并非纯数字（0为设定，1为毛图，2为插画")
        msggroup = event.get_message()
        url = msggroup["image"]
        Upload_account_Number = event.user_id
        Group_Number = group.group_id
        UpLoad_List = []
        Time = int(time.time())
        with open(f"{Data_Path}/{Time}.jpg", 'wb') as f:
            async with httpx.AsyncClient(http2=True,timeout=timeout) as client:
                Data = await client.get(list(url)[-1].data["url"])
                f.write(Data.content)
        File_Size = os.stat(f"{Data_Path}/{Time}.jpg")
        if File_Size.st_size >= 20000000:
            os.remove(f"{Data_Path}/{Time}.jpg")
            await matcher.finish(MessageSegment.reply(event.message_id)+"上传失败：文件过大！（大于20MB）")
        data = {
            "name": f"{Name}",
            "type": f"{Type}",
            "power": 1,
            "suggest": f"{Suggest}",
            "model": 1,
            "token":f"{token}",
            "token_user":f"{account}",
            "token_key":f"{password}",
            "time": f"{Time}",
            "Picturl_URL": f"{Data_Path}/{Time}.jpg",
            "Upload_account": f"{Upload_account_Number}",
            'Group_id': f"{Group_Number}"
        }
        if os.path.exists(f'{Data_Path}/Upload_Data.json'):
            UpLoad_List = Handler.load_json(f'{Data_Path}/Upload_Data.json', 'r')
                
        UpLoad_List.append(data)
        Handler.load_json(f"{Data_Path}/Upload_Data.json", 'w',UpLoad_List)               
        Count = len(UpLoad_List)
        await bot.call_api("send_private_msg", message=f"有人投图，请审核\n当前共有{Count}张图片待审核", user_id='1097740481', time_noend=True)
        await matcher.finish(MessageSegment.reply(event.message_id)+f"您的投图请求已提交给凌辉Bot管理员并进入等待审核状态。")

# 定义获取批量投图图片列表函数
async def Get_Batch_Pic_List(User_QQ,bot):
    pic_url = Handler.load_json(f"{opendata}/data/Furry_System/Upload/Batch/{User_QQ}/Upload.json",'r')
    List = []
    logger.debug(f'debug message:{type(pic_url)}')
    for i in range(0,len(pic_url)):
        image = pic_url[i]
        text = f"这是第{i+1}张图片，通过命令“定义”来定义开始该图片的信息。"
        Data = await Handler.Batch_Get(text,image,User_QQ,"凌辉Bot")
        List.append(Data)
    return List
    


@Batch_Upload.got("Upload",prompt="请一次性发送您欲上传的图片。\n当您在发送上传图片时，请在聊天框键入一个空格以将所有图片包含进1个Message中。")
@Handler.handle_errors
async def Get_Upload_Mode(matcher:Matcher,event:MessageEvent,bot:Bot):
    global Count
    Args = str(event.get_message())
    msggroup = event.get_message()
    url = msggroup["image"]
    url_list = []
    Temp_Path = opendata / "data" / "Furry_System" / "Upload" / "Batch" / str(event.user_id)
    Cycle_Count = 0
    if not os.path.exists(Temp_Path):
        os.makedirs(Temp_Path)
    if os.path.exists(f"{Temp_Path}/Upload.json"):
        Data = Handler.load_json(f"{Temp_Path}/Upload.json",'r')
        Cycle_Count = len(Data)
        for i in Data:
            url_list.append(i)
    j = 0
    for i in range(Cycle_Count,len(url)+Cycle_Count):
        pic_url = list(url)[j].data["url"]
        j += 1
        with open(f"{Temp_Path}/Upload_{i+1}.jpg", 'wb') as f:
            async with httpx.AsyncClient(timeout=timeout) as client:
                Data = await client.get(pic_url)
                f.write(Data.content)
                
        url_list.append(f"{Temp_Path}/Upload_{i+1}.jpg")
        File_Size = os.stat(f"{Temp_Path}/Upload_{i+1}.jpg")
        if File_Size.st_size >= 20000000:
            await matcher.send(f"第{i+1}张图片被拒绝上传：文件过大，拒绝处理。")
            os.remove(f"{Temp_Path}/Upload_{i+1}.jpg")
            url_list.remove(f"{Temp_Path}/Upload_{i+1}.jpg")
    if url_list == []:
        global Count
        if "取消" in Args or "退出" in Args:
            await matcher.finish(MessageSegment.reply(event.message_id)+"已退出批量投图。")
        else:
            if Count == 0:
                Count += 1
                await matcher.reject(MessageSegment.reply(event.message_id)+"输入有误，请重新输入。\n取消上传请发送“取消”或“退出”")
            else:
                Count = 0
                await matcher.finish(MessageSegment.reply(event.message_id)+"已退出批量投图。")
    Handler.load_json(f"{Temp_Path}/Upload.json",'w',url_list)
        
    List = await Get_Batch_Pic_List(event.user_id,Bot)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"生成图片链接列表已完成，但图片对应信息尚未设置\n请通过命令“定义”来定义对应图片的信息。")


@Batch_Set.got("Set_Message",prompt="请定义图片信息（定义实例：定义#1#名字#类别#留言）\n结束定义可发送“取消”或“退出”")
@Handler.handle_errors
async def Receive_Batch(matcher:Matcher,bot:Bot,event:MessageEvent):
    global Set_Count
    Temp_Path = f"{opendata}/data/Furry_System/Upload/Batch/{event.user_id}/Upload.json"
    if not os.path.exists(Temp_Path):
        await matcher.finish(MessageSegment.reply(event.message_id)+"遇到问题：未找到文件\n请检查是否已经批量投图图片。")
    List = Handler.load_json(Temp_Path,'r')
    Message = str(event.get_message())
    if "取消" in Message or "退出" in Message:
        await matcher.finish(MessageSegment.reply(event.message_id)+"已退出批量投图。")
    if Message.count("#") == 0:
        if Set_Count == 0:
            Set_Count += 1
            await matcher.reject(MessageSegment.reply(event.message_id)+"输入了一个错误的图片张数，请重新输入（仅接受数字）。\n取消上传请发送“取消”或“退出”")
        else:
            Set_Count = 0
            await matcher.finish(MessageSegment.reply(event.message_id)+"多次非法请求，已自动退出批量投图。")
    Message = Message.split("#")
    if len(Message) != 5:
        if Set_Count == 0:
            Set_Count += 1
            await matcher.reject(MessageSegment.reply(event.message_id)+"输入有误，请重新输入。\n取消上传请发送“取消”或“退出”")
        else:
            Set_Count = 0
            await matcher.finish(MessageSegment.reply(event.message_id)+"多次非法请求，已自动退出批量投图。")
    Pic_id,Name,Class,suggest = Message[1],Message[2],Message[3],Message[4]
    if not Pic_id.isdigit():
        if Set_Count == 0:
            Set_Count += 1
            await matcher.reject(MessageSegment.reply(event.message_id)+"输入的数据长度有误，请重新输入。\n取消上传请发送“取消”或“退出”")
        else:
            Set_Count = 0
            await matcher.finish(MessageSegment.reply(event.message_id)+"多次非法请求，已自动退出批量投图。")
    if int(Pic_id) > len(List):
        await matcher.finish(MessageSegment.reply(event.message_id)+"遇到问题：似乎超出了列表长度\n已自动退出")
    Pic_id = int(Pic_id)-1
    Upload_account_Number = event.user_id
    Group_Number = event.group_id
    data = {
            "name": f"{Name}",
            "type": f"{Class}",
            "power": 1,
            "suggest": f"{suggest}",
            "model": 1,
            "token":f"{token}",
            "token_user":f"{account}",
            "token_key":f"{password}",
            "time":0,
            "Picturl_URL": f"{List[Pic_id]}",
            "Upload_account": f"{Upload_account_Number}",
            'Group_id': f"{Group_Number}"
            }
    logger.info(data)
    del List[Pic_id]
    if len(List)+1 != 0:
        Upload_Data = Handler.load_json(f"{Data_Path}/Upload_Data.json",'r')
        Upload_Data.append(data)
        Handler.load_json(Temp_Path,'w',List)
        List = await Get_Batch_Pic_List(event.user_id,Bot)
        Handler.load_json(f"{Data_Path}/Upload_Data.json",'w',Upload_Data)
            
        logger.info(List)
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)
        await Batch_Set.reject(MessageSegment.reply(event.message_id)+"写入文件完成，请根据列表继续修改图片信息")
    else:
        await matcher.finish("定义图片列表已为空，这意味着你已经定义完了全部的图片\n事件处理结束。")

# # 新增画布创建函数
# def create_text_canvas(text_lines, font, padding=50, line_spacing=20):
#     # 计算文本尺寸
#     max_width = 0
#     total_height = 0
#     temp_image = Image.new('RGB', (1, 1), (255, 255, 255))
#     draw = ImageDraw.Draw(temp_image)

#     for line in text_lines:
#         bbox = draw.textbbox((0, 0), str(line), font=font)
#         line_width = bbox[2] - bbox[0]
#         line_height = bbox[3] - bbox[1]
        
#         max_width = max(max_width, line_width)
#         total_height += line_height + line_spacing

#     # 计算最终尺寸
#     canvas_width = max_width + 2*padding
#     canvas_height = total_height - line_spacing + 2*padding

#     return Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))

@FurryList.handle()
@Handler.handle_errors
async def Furry_List(matcher:Matcher,event: MessageEvent,bot:Bot, args: Message = CommandArg()):
    name = str(args)
    Orignal_data = httpx.get(
        f"{api_base}/function/pulllist?type=&name={name}",timeout=timeout)
    if Orignal_data.status_code != 200:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"请求图片信息失败，服务器回报状态码：{Orignal_data.status_code}")
    Orignal_data = Orignal_data.json()
    msg = Orignal_data['msg']
    code = Orignal_data['code']
    data = Orignal_data['open']
    ListLength = len(data)
    List = []
    if code != "20700":
        await matcher.finish(MessageSegment.reply(event.message_id)+f"错误，{msg}[Code={code}]")
    else:
        if ListLength == 0:
            await matcher.finish(MessageSegment.reply(event.message_id)+f"服务器回报：{msg}。但并没有获取到任何数据，请检查名称是否正确")
        text = ""
        User_QQ = event.user_id
        stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        List.append(await Handler.Batch_Get(f"共获取到了{ListLength}条消息，下面为列表。",None,event.self_id,nickname))
        for i in range(0, ListLength):
            Now_Data = data[i]
            name = Now_Data['name']
            id = Now_Data['id']
            suggest = Now_Data['suggest']
            if suggest == "":
                suggest = "该图片暂无留言"
            temp = f"名字：{name}\nid：{id}\n留言：{suggest}\n=======================\n"
            make_text = await Handler.Batch_Get(temp,None,event.self_id,nickname)
            List.append(make_text)
            text += temp
        if ListLength < 100:
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)
            await matcher.finish()
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=f"{MessageSegment.reply(event.message_id)}获取到的信息数量过多，将使用图片输出。", time_noend=True)
        
        # 优化后的图片生成部分
        try:
            font = ImageFont.truetype(Font_Path, size=30)
        except:
            font = ImageFont.load_default()
        
        text_lines = [line for line in text.split('\n') if line.strip() != '']
        image = Handler.create_auto_newlines_picture(text_lines, font)
        image.save(Pic_URL)
        await matcher.finish(MessageSegment.reply(event.message_id)+f"共获取到了{ListLength}条消息："+MessageSegment.image(Pic_URL))


@Modify_Furry.handle()
@Handler.handle_errors
async def Modify_Furry_Function(matcher:Matcher,event: MessageEvent, args: Message = CommandArg()):
    try:
        message = str(args)
        After_message = message.split("#")
        Modify_id = int(After_message[1])
        pic_Normal = After_message[2]
        Class = After_message[3]
        data = {
            "picture": f"{Modify_id}",
            "type": "1",
            "model": "1",
            "token":f"{token}",
            "token_user":f"{account}",
            "token_key":f"{password}"
        }
        if Class == "名字":
            pic_Normal = str(pic_Normal)
            data_Name_type = {"name": f"{pic_Normal}", "type": "0"}
            data.update(data_Name_type)
        elif Class == "留言":
            pic_Normal = str(pic_Normal)
            data_suggest_type = {"suggest": f"{pic_Normal}", "type": "3"}
            data.update(data_suggest_type)
        elif Class == "类型":
            pic_Normal = int(pic_Normal)
            data_class_type = {"form": f"{pic_Normal}", "type": "2"}
            data.update(data_class_type)
        else:
            msggroup = event.get_message()
            url = msggroup["image"]
            pic_url = list(url)[-1].data["url"]
            logger.info(pic_url)
            async with httpx.AsyncClient(timeout=timeout) as client:
                image_url = await client.get(pic_url)
                image_url = image_url.content
            files = {'file': (f'Modify.png', image_url, 'image/png')}
            data_type = {"type": "1"}
            data.update(data_type)
    except:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"在获取数据时遇到问题，请按照“修改图片#id#名字/留言/类型>#修改类型/图片”的格式重新调用命令。\n修改类型接受的参数有：名字/留言/类型")
    if "https://" in Class:
        async with httpx.AsyncClient(timeout=timeout) as client:
            a = await client.post(f"{api_base}/function/modify",data=data, files=files)
            if a.status_code != 200:
                await matcher.finish(MessageSegment.reply(event.message_id)+f"请求图片信息失败，服务器回报状态码：{a.status_code}")
            a = a.json()
    else:
        async with httpx.AsyncClient(timeout=timeout) as client:
            a = await client.post(
            f"{api_base}/function/modify",data=data)
            if a.status_code != 200:
                await matcher.finish(MessageSegment.reply(event.message_id)+f"请求图片信息失败，服务器回报状态码：{a.status_code}")
            a = a.json()
    Code, Msg = a['code'], a['msg']
    await matcher.finish(MessageSegment.reply(event.message_id)+f"平台返回：{Msg}[Code:{Code}]")

@Furry_status.handle()
@Handler.handle_errors
async def Furry_Status_Function(matcher:Matcher,event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    Get = httpx.get(
        f"{api_base}/function/pictures?picture={args}&model=1",timeout=timeout)
    if Get.status_code != 200:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"请求图片信息失败，服务器回报状态码：{Get.status_code}")
    Get = Get.json()
    Msg, code = Get['msg'], Get['code']
    examine_Number, type_number = Get['examine'], Get['power']
    examine_name_list, type_name_list = [
        "待审核", "已通过审核", "已被审核拒绝"], ['设定', '毛图', '插画']
    name, id, examine, type = Get['name'], Get["id"], examine_name_list[examine_Number], type_name_list[type_number]
    await matcher.finish(MessageSegment.reply(event.message_id)+f"""=========FurBot=========
您查询的id为{id}的图片信息如下：
图片名字：{name}
审核结果：{examine}
图片类型：{type}
=======LingHuiBot=======""")


@Service_Status.handle()
@Handler.handle_errors
async def Service_Furry_Status(matcher:Matcher,event: MessageEvent):
    a = httpx.get(
        f"{api_base}/information/feedback",timeout=timeout).json()
    code, msg = a['code'], a['msg']
    if code != "40000":
        await matcher.finish(MessageSegment.reply(event.message_id)+f"平台返回：{msg}[Code={code}]")
    else:
        time, examine, power, atlas, total, page = a['time']['count'], a['examine']['count'], a[
            'power']['count'], a['atlas']['count'], a['total']['count'], a['page']['count']
        await matcher.finish(MessageSegment.reply(event.message_id)+f"""平台返回：
==========FurBot==========
运行时长：{time}天
待审核图片数：{examine}
已公开图片数：{power}
已有图片数：{atlas}
总调用次数：{total}
-->由兽云祭API提供服务支持
========Service Status========""")


@FurryFusion_List.handle()
@Handler.handle_errors
async def FurryFusion_List_Function(matcher:Matcher, event: MessageEvent,bot: Bot):
    a = httpx.get(
        "https://api.furryfusion.net/service/activity",timeout=timeout).json()
    Data = a['data']
    State_Name_List = ['活动已结束', "活动正在预告中", "售票中", "活动正在举行", "活动已取消"]
    List = []
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    try:
        img = f"{allin_pic_prerequisite_path}/image_1.png"
        file_stat = os.stat(img)
        if int(time.time()) - file_stat.st_mtime >= 86400:
            await bot.send(event, MessageSegment.reply(event.message_id)+"图库似乎已过期，本次操作将重新同步数据，所以将需要一些时间，请耐心等待。")
    except:
        await bot.send(event, MessageSegment.reply(event.message_id)+"图库似乎还没有生成，本次操作将重新同步数据，所以将需要一些时间，请耐心等待。")
    List.append(await Handler.Batch_Get("通过命令“兽聚快讯#<这里输入要查询的兽聚信息条数，仅需要数字即可。>”可以获取指定项目的详细信息",None,event.self_id,nickname))
    for i in range(0, len(Data)):
        title = Data[i]['title']  # 兽聚主体名称
        name = Data[i]['name']  # 当次兽聚的主题名称
        state = State_Name_List[Data[i]['state']]  # 获取展会动态
        address = Data[i]['address']  # 当次兽聚的举办地址
        time_day = Data[i]['time_day']
        time_start = Data[i]['time_start']
        time_end = Data[i]['time_end']
        image = Data[i]['image']
        text = f"第{i+1}条兽聚信息：\n展会举办者：{title}\n兽聚主题：{name}\n当前展会状态：{state}\n举办地点：{address}\n举办时间：共{time_day}天\n【{time_start}~{time_end}】"
        img = f"{allin_pic_prerequisite_path}/image_{i+1}.png"
        try:
            file_stat = os.stat(img)
        except:
            file_stat = SimpleNamespace(st_mtime=0)
        if int(time.time()) - file_stat.st_mtime >= 86400:
            logger.warning(f"文件 image_{i+1}.png 似乎已过期或未生成，重新生成中。")
            img = await Handler.furryfusion_picture_handle(image,i+1,text)
            logger.info(f"第{i+1}条兽聚信息已被处理。")
        make_text = await Handler.Batch_Get(text,img,User_QQ,nickname)

        List.append(make_text)
    # 合并图片
    furryfusion_allin_pic_path = [f"{allin_pic_prerequisite_path}/image_{i}.png" for i in range(1,len(os.listdir(allin_pic_prerequisite_path)))]
    columns = 1  # 设置列数
    background_color = (255, 255, 255)  # 设置背景颜色为白色

    IMG_WIDTH, IMG_HEIGHT = 350, 130
    
    # 计算行列数
    image_count = len(furryfusion_allin_pic_path)
    rows = math.ceil(image_count / columns)
    
    # 创建空白画布 (RGBA模式支持透明背景)
    canvas = Image.new(
        mode='RGB',
        size=(columns * IMG_WIDTH, rows * IMG_HEIGHT),
        color=background_color
    )
    
    # 遍历并粘贴图片
    for index, img_path in enumerate(furryfusion_allin_pic_path):
        # 计算当前图片位置
        row = index // columns
        col = index % columns
        
        # 打开图片并确保为RGB模式
        with Image.open(img_path) as img:
            img = img.convert('RGB')
            if img.size != (IMG_WIDTH, IMG_HEIGHT):
                img = img.resize((IMG_WIDTH, IMG_HEIGHT), Image.LANCZOS)
            
            # 计算粘贴坐标
            x = col * IMG_WIDTH
            y = row * IMG_HEIGHT
            canvas.paste(img, (x, y))
    
    # 保存结果
    canvas.save(f"{allin_pic_prerequisite_path}/allin.jpg")
    logger.success(f"拼接完成! 生成图片: {allin_pic_prerequisite_path}/allin.jpg")
    logger.info(f"布局: {columns}列 x {rows}行 | 总分辨率: {canvas.size[0]}x{canvas.size[1]}")
    await matcher.finish(MessageSegment.reply(event.message_id)+"输出完毕~"+MessageSegment.image(f"{allin_pic_prerequisite_path}/allin.jpg"))


@FurryFusion_Check.handle()
@Handler.handle_errors
async def FurryFusion_Check_Function(matcher:Matcher, event: MessageEvent,bot: Bot, args: Message = CommandArg()):
    message = str(args)
    if "省" in message and "市" in message:
        await matcher.send("不应带有省+市字样，将取市作为查找依据。")
        message = message.split("市")
        message = message[1]
    elif "省" in message:
        message = message.split("省")
        message = message[0]
    elif "市" in message:
        message = message.split("市")
        message = message[0]
    logger.info(message)
    a = httpx.get(
        f"https://api.furryfusion.net/service/screen?content={message}&mode=address",timeout=timeout).json()
    Code = a['code']
    msg = a['rel']
    city_list = a['data']['history']['province']
    List = []
    logger.info(message)
    logger.info(city_list)
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    if city_list == []:
        city_list = a['data']['history']['city']
    for i in range(0, len(city_list)):
        title = city_list[i]['title']
        name = city_list[i]['name']
        image_url = city_list[i]['image']
        group_list = city_list[i]['groups']
        group_str = ''
        if group_list != ['']:
            for j in range(0, len(group_list)):
                group_str += f"{group_list[j]}、"
        else:
            group_str = "尚未获取到已登记的官方群聊信息"
        time_start = city_list[i]['time_start']
        time_end = city_list[i]['time_end']
        time_day = city_list[i]['time_day']
        address = city_list[i]['address']
        text = f"展会名称：{title}\n举办展会主题：{name}\n官方群聊：{group_str}\n举办地点：{address}\n举办总时长：{time_day}天\n【{time_start}~{time_end}】"
        make_text = await Handler.Batch_Get(text,image_url,event.self_id,nickname)
        List.append(make_text)
    if List == []:
        await matcher.finish(MessageSegment.reply(event.message_id)+"未查找到任何兽聚。")
    else:
        # logger.info(List)
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)


@FurryFusion_countdown.handle()
@Handler.handle_errors
async def FurryFusion_countdown_Function(matcher:Matcher,event: MessageEvent,bot:Bot):
    data = httpx.get(
        "https://api.furryfusion.net/service/countdown",timeout=timeout).json()
    code = data['code']
    msg = data['rel']
    data = data['data']
    State_text_List = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    List = []
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    for i in range(0, len(data)):
        title = data[i]['title']
        name = data[i]['name']
        State = data[i]['state']
        address_province = data[i]['address_province']
        address_city = data[i]['address_city']
        address = f"{address_province}省 {address_city}市"
        time_day = data[i]['time_day']
        time_start = data[i]['time_start']
        time_end = data[i]['time_end']
        time_surplus = data[i]['time_surplus']
        State = State_text_List[State]
        text = f"展会名称：{title}\n举办展会主题：{name}\n当前展会状态：{State}\n举办地点：{address}\n举办\
总时长：{time_day}天\n【{time_start}~{time_end}】\n距离展会开始还有：{time_surplus+1}天\n该倒计时天数已加上今天"
        make_text = await Handler.Batch_Get(f"{text}\n生成时间：{time.strftime('%Y-%m-%d %a %H:%M:%S', time.localtime())}",None,event.self_id,nickname)
        List.append(make_text)
    # logger.info(List)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)


@FurryFusion_Quick_Information.handle()
@Handler.handle_errors
async def FurryFusion_Quick_Information_Function(matcher:Matcher, event: MessageEvent,bot: Bot, args: Message = CommandArg()):
    args = int(str(args))
    Get = httpx.get(
        "https://api.furryfusion.net/service/activity",timeout=timeout).json()
    code = Get['code']
    msg = Get['rel']
    if code != "OK":
        await matcher.finish(f"遇到错误：{msg}[Code={code}]")
    data = Get['data']
    Number = args-1
    List = []
    Information = data[Number]
    title = Information['title']
    name = Information['name']
    image = Information['image']
    state = Information['state']
    State_Text_List = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    State_Text = State_Text_List[state]
    group_list = Information['groups']
    group_str = ''
    if group_list != ['']:
        for j in range(0, len(group_list)):
            group_str += f"{group_list[j]}、"
    else:
        group_str = "尚未获取到已登记的官方群聊信息"
    address = Information['address']
    time_day = Information['time_day']
    time_start = Information['time_start']
    time_end = Information['time_end']
    text = f"展会名称：{title}\n举办展会主题：{name}\n展会状态：{State_Text}\n官方群聊：{group_str}\n举办地点：{address}\n举办总时长：{time_day}天\n【{time_start}~{time_end}】\n推荐结合“今年兽聚”命令使用"
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    make_text = await Handler.Batch_Get(text,image,event.self_id,nickname)
    List.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)

@FurryFusion_Information.handle()
@Handler.handle_errors
async def FurryFusion_Information_Function(matcher:Matcher, event: MessageEvent,bot: Bot, args: Message = CommandArg()):
    args = str(args)
    List = []
    a = httpx.get(
        f"https://api.furryfusion.net/service/details?title={args}",timeout=timeout).json()
    msg = a['rel']
    code = a['code']
    if code != "OK" or args == "":
        await matcher.finish(MessageSegment.reply(event.message_id)+"好像没有找到你想要查找的兽聚或你要查找的兽聚是个空值呢qwq...")
    data = a['data']
    title = data['title']
    url = data['url']
    group_list = data['groups']
    group_str = ''
    correlation_str = ''
    if group_list != ['']:
        for i in range(0, len(group_list)):
            group_str += f"{group_list[i]}、"
            logger.info(i)
    else:
        group_str = "尚未获取到已登记的官方群聊信息"
    image = data['image']
    brief = data['brief']
    correlation = data['correlation']
    if correlation != ['']:
        for i in range(0, len(correlation)):
            correlation_str += f"{correlation[i]}、"
    else:
        correlation_str = "尚未获取到具有关联性的其他品牌名称"
    State_List_str = ["正常运行", "举办预告中", "宣告解散、停止运行", "信息失联"]
    State = State_List_str[data['state']]
    ltd_name, ltd_url = data['ltd']['name'], data['ltd']['url']
    bilibili_name, bilibili_url = data['bilibili']['name'], data['bilibili']['url']
    weibo_name, weibo_url = data['weibo']['name'], data['weibo']['url']
    mail = data['mail']['name']
    if correlation_str == "":
        correlation_str = "暂未获取到数据"
    if url == "":
        url = "暂未获取到数据"
    if ltd_name == "":
        ltd_name, ltd_url = "暂未获取到数据", "暂未获取到数据"
    if weibo_name == "":
        weibo_name, weibo_url = "暂未获取到数据", "暂未获取到数据"
    if mail == "":
        mail = "暂未获取到数据"
    text = f"""展会名称：{title}
展会介绍：{brief}
展会状态：{State}
展会官网：{url}
工商主体：{ltd_name}，URL：{ltd_url}
bilibili：{bilibili_name}，URL：{bilibili_url}
官方微博：{weibo_name}，URL：{weibo_url}
官方邮箱：{mail}
官方群聊：{group_str}
具有关联性的其他品牌名称：{correlation_str}
下面为该展会举办的部分活动/线下兽聚"""
    User_QQ = event.user_id
    stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    make_text = await Handler.Batch_Get(text,image,event.self_id,nickname)
    List.append(make_text)
    info = a['info']
    Info_State_List_str = ['活动结束', '预告中', '售票中', '活动中', '活动取消']
    for i in range(0, len(info)):
        Info_title = info[i]['title']
        Info_name = info[i]['name']
        Info_image = info[i]['image']
        Info_state = Info_State_List_str[info[i]['state']]
        Info_address = info[i]['address']
        Info_time_start = info[i]['time_start']
        Info_time_end = info[i]['time_end']
        text = f"""第{i+1}条：
举办展会：{Info_title}
活动名称：{Info_name}
活动举办状态：{Info_state}
活动举办地点：{Info_address}
举办时间：【{Info_time_start}~{Info_time_end}】"""
        make_text = await Handler.Batch_Get(text,Info_image,event.self_id,nickname)
        List.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)

# @See_Furry.handle()
# async def See_Furry_Function(matcher:Matcher,bot:Bot,event: MessageEvent,args:Message = CommandArg()):
#     try:
#         a = httpx.get(
#             "https://atlas.foxtail.cn/api/function/obtain",timeout=timeout).json()
#         if args != None:
#             if str(args).isdigit():
#                 a = httpx.get(
#                 f"https://atlas.foxtail.cn/api/function/obtain?data={int(str(args))}",timeout=timeout).json()
#             else:
#                 await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=f"{MessageSegment.reply(event.message_id)}输入类型错误，将随机获取。", time_noend=True)
#         data = a['Data']
#         Number = data['Number']
#         Name = data['Name']
#         Atlas = data['Atlas']
#         await matcher.finish(MessageSegment.reply(event.message_id)+f"获取完成\nid：{Number}\n名字：{Name}"+MessageSegment.image(Atlas))
#     except MatcherException:  # 执行完成，接住抛出的FinishedException异常以结束本次事件执行
#         # 注：此处必须要接住该异常，否则事件将无法正常结束。
#         raise  # 什么都不需要做，接住就行
#     except Exception as e:
#         e = str(e)
#         if "NetWorkError" in e:
#             raise
#         else:
#             Error()
#             await matcher.finish(f"在运行中遇到未知错误。\n错误已添加至错误日志中，请联系管理员进行检查或提供帮助。")


@Check_Upload.handle()
@Handler.handle_errors
async def CU_Function(matcher:Matcher, event: MessageEvent,bot: Bot):
    Data_List, List = [], []
    Data_List = Handler.load_json(f"{Data_Path}/Upload_Data.json", 'r')
    if Data_List == []:
        await matcher.finish(MessageSegment.reply(event.message_id)+"当前投图待审核列表是空的")
    Len = len(Data_List)
    type_Text = ['设定', '毛图', '插画']
    for i in range(Len):
        Name = Data_List[i]['name']
        type = int(Data_List[i]['type'])
        Picture_URL = Data_List[i]['Picturl_URL']
        suggest = Data_List[i]['suggest']
        if suggest == '':
            suggest = "未填写留言"
        Upload_account = Data_List[i]['Upload_account']
        Group_id = Data_List[i]['Group_id']
        text = f"""第{i+1}条：
上传者：{Upload_account}
上传群聊：{Group_id}
图片名称：{Name}
留言内容：{suggest}
图片类型：{type_Text[type]}"""
        User_QQ = event.user_id
        stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        make_text = await Handler.Batch_Get(text,Picture_URL,event.self_id,nickname)
        List.append(make_text)
    logger.info(List)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)


@Check_Upload_Decide.handle()
@Handler.handle_errors
async def CUD_Function(matcher:Matcher, event: MessageEvent,bot: Bot, args: Message = CommandArg()):
    await matcher.send("将通过凌辉Bot内置账户进行处理")
    Data_Message = event.get_message()
    args = str(args)
    args = args.split("#")
    Temp_args = args
    args = int(args[0])
    List = Handler.load_json(f"{Data_Path}/Upload_Data.json", 'r')
    logger.info(List)
    logger.info(Temp_args)
    if args > len(List):
        await matcher.finish(MessageSegment.reply(event.message_id)+"错误：输入的值超出列表项目\n请确认列表项目后重试。")
    if List == []:
        await matcher.finish(MessageSegment.reply(event.message_id)+"遇到问题：似乎没有待审核的图片。")
    Data_Normal = List[args-1]
    Pic_URL = Data_Normal['Picturl_URL']
    Time_Wait = Data_Normal['time']
    Time = time.localtime(int(Time_Wait))
    Name = Data_Normal['name']
    Type = int(Data_Normal['type'])
    TypeList = ["设定", "毛图", "插画"]
    TypeValue = TypeList[Type]
    Suggest = Data_Normal['suggest']
    Group_id = int(Data_Normal['Group_id'])
    account = Data_Normal['Upload_account']
    if Suggest == "":
        Suggest = "未填写"
    del Data_Normal['Picturl_URL'], Data_Normal['Group_id'], Data_Normal['Upload_account'], Data_Normal['time']
    if "拒绝" in str(Data_Message):
        del List[args-1]
        Handler.load_json(f"{Data_Path}/Upload_Data.json", 'w',List)
            
        Data_Message = str(Data_Message)
        if Data_Message.count("#") != 2:
            Caution = "管理员没有填写"
        else:
            Caution = Temp_args[1]
        if event.group_id != Group_id:
            await bot.call_api("send_group_msg", group_id=Group_id,message=f"""凌辉Bot管理员已拒绝了来自{account}的投图请求
拒绝理由：{Caution}
【上传时间戳：{time.strftime("%Y-%m-%d %H:%M:%S", Time)}】
下面是打回图片的详细信息：
图片名字：{Name}
图片类型：{TypeValue}
图片留言：{Suggest}
图片内容："""+MessageSegment.image(f"{Pic_URL}"), time_noend=True)
        os.remove(f"{Pic_URL}")
        await matcher.finish(MessageSegment.reply(event.message_id)+f"拒绝上载的操作已完成\n传入拒绝理由参数：{Caution}")

    with open(f"{Pic_URL}", 'rb') as f:
        async with httpx.AsyncClient(timeout=timeout) as client:
            a = await client.post(f"{api_base}/function/upload",data=Data_Normal, files={'file': ('Upload.png', f, 'image/png')})
            a = a.json()
    logger.info(a)
    if a['code'] != '20000':
        await matcher.finish(MessageSegment.reply(event.message_id)+f"好像没有上传成功呢...？\n{a['msg']}[{a['code']}]")
    msg = a['msg']
    code = a['code']
    id = a['id']
    picture = a['picture']
    if code != "20000":
        await matcher.finish(MessageSegment.reply(event.message_id)+f"错误：{msg}[Code={code}]")
    else:
        text = f"""API返回信息：{msg}[Code={code}]
======传入参数======
图片名字:{Name}
图片类型:{TypeValue}
图片留言:{Suggest}
======服务器数据=======
您的数字id：{id}
您的图片码：{picture}"""
        del List[args-1]
        Handler.load_json(f"{Data_Path}/Upload_Data.json", 'w',List)
        if event.group_id != Group_id:
            await bot.call_api("send_group_msg", group_id=Group_id, message=f"""凌辉Bot管理员已经同意了来自{account}的投图请求，请等待兽云祭管理员进行审核
上载图片："""+MessageSegment.image(f"{Pic_URL}")+f"""数字id：{id}
【上传时间戳：{time.strftime("%Y-%m-%d %H:%M:%S", Time)}】""", time_noend=True)
        await bot.call_api("send_group_msg", group_id=event.group_id, message=f"{text}\n上载图片："+MessageSegment.image(f"{Pic_URL}"), time_noend=True)
        os.remove(f"{Pic_URL}")

@Debugger_Upload.handle()
async def Debugger(matcher:Matcher,event:MessageEvent):
    await matcher.send("调试器运行中...")
    Data = Handler.load_json(f"{Data_Path}/Upload_Data.json", 'r')
    Dir_List = []
    for root, dirs, files in os.walk(f'{Data_Path}'):
        Dir_List.append(f'root={root}, dirs={dirs}, files={files}')
    await asyncio.sleep(1.5)
    Text = f"""调试器返回:
文件【{Data_Path}/Upload_Data.json】中所包含的信息如下：
{Data}
文件【{Data_Path}/Upload_Data.json】中信息的Type值为：{type(Data)}
路径【{Data_Path}】中包含的所有文件及其子目录：
{Dir_List}

它可以告诉您Furry_System的上传功能所使用的文件是否存在错误。但它无法告诉你为什么以及在哪里可能存在潜在的错误。
在大多数情况下，文件名和文件中包含的内容都没有也不应存在任何错误，如果函数仍然无法运行。请联系管理员检查代码以排除可能存在的隐性问题。
调试器已经将这一段文本作为critical级日志输出于后台终端。
感谢您使用调试器。
"""
    logger.critical(Text)
    await matcher.finish(MessageSegment.reply(event.message_id)+Text)

@Upload_Clear.handle()
async def UC_Function(matcher:Matcher):
    Temp_Path = Data_Path / "Upload_Data.json"
    Dir_Path = Data_Path / "Batch"
    if os.path.exists(Temp_Path):
        os.remove(Temp_Path)
    if os.path.exists(Dir_Path):
        shutil.rmtree(Dir_Path)
    with open(Temp_Path,'w',encoding='utf-8') as f:
        f.write("[]")
    await matcher.finish("操作已完成。")
