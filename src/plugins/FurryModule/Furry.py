# 标准库
import asyncio, os, shutil, time, httpx, math

from src.plugins import utils
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
from PIL import Image, ImageFont

from src.plugins.utils import get_config_item

# 定义全局变量
login_cookie = {}
timeout = None
count = 0
set_count = 0
api_base = "https://cloud.foxtail.cn/api"

# 读取配置项，优先环境变量
# 统一前缀 FURRY_
token = get_config_item('furry_token', default="未获取到数据", required=True, desc="Foxtail API Token")
account = get_config_item('furry_user', default="未获取到数据", required=True, desc="Foxtail 账号")
password = get_config_item('furry_password', default="未获取到数据", required=True, desc="Foxtail 密码")

if all([token != "未获取到数据", account != "未获取到数据", password != "未获取到数据"]):
    logger.success("✅已成功加载Furry模块的相关配置！")
else:
    logger.warning("请注意，当前功能受限制！")
    logger.warning("您没有填写token/account/password，这将导致“投图”功能不可用！")
    logger.info(f"获取到的信息：\ntoken：{token}\naccount：{account}\npassword：{password}\napi_base：{api_base}")
    logger.warning(
        "请确保.env.dev文件中具有如下内容：\nFURRY_TOKEN=您的token\nFURRY_USER=您的账号\nFURRY_PASSWORD=您的密码")

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
    "同意上传#", aliases={"同意上载#", "拒绝上传#", "拒绝上载#"}, priority=99, block=True,
    permission=SUPERUSER)  # 决定是否上传
# Batch_Check = on_command("批量审核",aliases={"批量上传"},priority=98,block=True,permission=SUPERUSER)
Upload_Clear = on_command("清空上传数据", aliases={"清除上传"}, permission=SUPERUSER)
# login_account = on_command("登录Fur",permission=SUPERUSER)

@RanFurry.handle()
@utils.handle_errors
async def random_furry_image(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    if args == "":
        data = httpx.get(f"{api_base}/function/random")  # 发起Get请求获取一张随机毛图
    else:
        try:
            data = httpx.get(f"{api_base}/function/pictures?picture={int(args)}&model=1", timeout=timeout, verify=False)
        except ValueError:
            data = httpx.get(f"{api_base}/function/random?name={args}", timeout=timeout)
    if data.status_code != 200:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"凌辉似乎没有获取到要下载的图片qwq...[HTTP {data.status_code}]")
    data = data.json()  # 将获取到的request请求转为Json格式
    code = data["code"]  # 获取数据中的code变量，即状态码
    msg = data["msg"]  # 获取数据中的msg变量，即信息
    if code == "20600":
        url = data['url']
        name = data['name']
        suggest = data['suggest']  # 获取download字段中suggest变量，即该图片的留言信息。
        if suggest != "":  # 如果留言不为空
            suggest = f"它的留言是“{suggest}”\n"
        id = data['id']  # 获取download字段中的id变量，即该图片的数字id
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"这只兽兽叫“{name}”~\n{suggest}图片码为：{id}\n" + MessageSegment.image(url))
    elif code != "20900":  # 如果状态码不为20900（即获取失败）
        await matcher.finish(MessageSegment.reply(event.message_id) + f"好像哪里不对...？\n错误信息：{msg}[Code:{code}]")
    data = data['picture']  # 获取data中的picture变量，即图片详细信息
    picture = data['picture']  # 获取data字段中的picture变量，即图片唯一识别码
    # 发起POST请求以获取数据，将数据传入给download变量，转为Json格式
    download = httpx.post(
        f"{api_base}/function/pictures?picture={picture}&model=", timeout=timeout)
    if download.status_code != 200:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"凌辉似乎没有获取到要下载的图片qwq...\n[HTTP {download.status_code}]")
    download = download.json()
    name = download['name']  # 获取download字段中的name变量，即该兽兽的名字
    id = download['id']  # 获取download字段中的id变量，即该图片的数字id
    url = download['url']  # 获取download字段中的url变量，即该图片的临时URL
    suggest = download['suggest']  # 获取download字段中suggest变量，即该图片的留言信息。
    if suggest != "":  # 如果留言不为空
        suggest = f"它的留言是：“{suggest}”\n"
    # 输出正常的信息。
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"这只兽兽叫“{name}”~\n{suggest}图片码为：{id}\n" + MessageSegment.image(url))


# 使用PicFurry响应器的handle装饰器装饰函数PicFur_handle_function

@PicFurry.handle()
@utils.handle_errors
async def pic_fur_handle_function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    sid = str(args)
    if sid == "":
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"凌辉似乎没有获取到要查找的图片qwq...麻烦你再看看有没有正确使用呢owo")
    else:
        # 发起Get请求获取一张指定sid的毛图
        data = httpx.get(f"{api_base}/function/pictures?picture={sid}&model=1", timeout=timeout)
        if data.status_code != 200:
            await matcher.finish(
                MessageSegment.reply(event.message_id) + f"凌辉好像没有获取到图片信息捏qwq...[HTTP {data.status_code}]")
        data = data.json()  # 将获取到的request请求转为Json格式
        Code = data["code"]  # 获取数据中的code变量，即状态码
        msg = data["msg"]  # 获取数据中的msg变量，即信息
        if Code != "20600":  # 如果状态码不为20600（即获取失败）----->↓
            # 则输出错误
            await matcher.finish(
                MessageSegment.reply(event.message_id) + f"好像哪里不对...？\n错误信息：{msg}[Code:{Code}]")
        else:  # 如果状态码为20600（即获取成功），则执行else下命令（处理数据）
            url = data['url']  # 获取data中的picture变量，即图片详细信息
            id = data['id']  # 获取data字段中的picture变量，即图片唯一识别码
            name = data['name']  # 获取data字段中的name变量，即图片名称
            suggest = data['suggest']
            if suggest != "":  # 如果留言不为空
                suggest = f"它的留言是：“{suggest}”\n"
            # 输出正常的信息。
            await matcher.finish(MessageSegment.reply(
                event.message_id) + f"这只兽兽叫“{name}”~\n{suggest}图片码为：{id}\n" + MessageSegment.image(url))

@FurryList.handle()
@utils.handle_errors
async def Furry_List(matcher: Matcher, event: MessageEvent, bot: Bot, args: Message = CommandArg()):
    name = str(args)
    Orignal_data = httpx.get(
        f"{api_base}/function/pulllist?type=&name={name}", timeout=timeout)
    if Orignal_data.status_code != 200:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"请求图片信息失败，服务器回报状态码：{Orignal_data.status_code}")
    Orignal_data = Orignal_data.json()
    msg = Orignal_data['msg']
    code = Orignal_data['code']
    data = Orignal_data['open']
    ListLength = len(data)
    List = []
    if code != "20700":
        await matcher.finish(MessageSegment.reply(event.message_id) + f"错误，{msg}[Code={code}]")
    else:
        if ListLength == 0:
            await matcher.finish(
                MessageSegment.reply(event.message_id) + f"服务器回报：{msg}。但并没有获取到任何数据，请检查名称是否正确")
        text = ""
        User_QQ = event.user_id
        stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        List.append(await utils.batch_get(f"共获取到了{ListLength}条消息，下面为列表。", None, event.self_id, nickname))
        for i in range(0, ListLength):
            Now_Data = data[i]
            name = Now_Data['name']
            id = Now_Data['id']
            suggest = Now_Data['suggest']
            if suggest == "":
                suggest = "该图片暂无留言"
            temp = f"名字：{name}\nid：{id}\n留言：{suggest}\n=======================\n"
            make_text = await utils.batch_get(temp, None, event.self_id, nickname)
            List.append(make_text)
            text += temp
        if ListLength < 100:
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)
            await matcher.finish()
        await bot.call_api("send_group_forward_msg", group_id=event.group_id,
                           message=f"{MessageSegment.reply(event.message_id)}获取到的信息数量过多，将使用图片输出。",
                           time_noend=True)

        # 优化后的图片生成部分
        try:
            font = ImageFont.truetype(Font_Path, size=30)
        except:
            font = ImageFont.load_default()

        text_lines = [line for line in text.split('\n') if line.strip() != '']
        image = utils.generate_text_image(text_lines, font)
        image.save(Pic_URL)
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"共获取到了{ListLength}条消息：" + MessageSegment.image(Pic_URL))


@Modify_Furry.handle()
@utils.handle_errors
async def Modify_Furry_Function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
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
            "token": f"{token}",
            "token_user": f"{account}",
            "token_key": f"{password}"
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
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"在获取数据时遇到问题，请按照“修改图片#id#名字/留言/类型>#修改类型/图片”的格式重新调用命令。\n修改类型接受的参数有：名字/留言/类型")
    if "https://" in Class:
        async with httpx.AsyncClient(timeout=timeout) as client:
            a = await client.post(f"{api_base}/function/modify", data=data, files=files)
            if a.status_code != 200:
                await matcher.finish(
                    MessageSegment.reply(event.message_id) + f"请求图片信息失败，服务器回报状态码：{a.status_code}")
            a = a.json()
    else:
        async with httpx.AsyncClient(timeout=timeout) as client:
            a = await client.post(
                f"{api_base}/function/modify", data=data)
            if a.status_code != 200:
                await matcher.finish(
                    MessageSegment.reply(event.message_id) + f"请求图片信息失败，服务器回报状态码：{a.status_code}")
            a = a.json()
    Code, Msg = a['code'], a['msg']
    await matcher.finish(MessageSegment.reply(event.message_id) + f"平台返回：{Msg}[Code:{Code}]")


@Furry_status.handle()
@utils.handle_errors
async def Furry_Status_Function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    args = str(args)
    Get = httpx.get(
        f"{api_base}/function/pictures?picture={args}&model=1", timeout=timeout)
    if Get.status_code != 200:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"请求图片信息失败，服务器回报状态码：{Get.status_code}")
    Get = Get.json()
    Msg, code = Get['msg'], Get['code']
    examine_Number, type_number = Get['examine'], Get['power']
    examine_name_list, type_name_list = [
        "待审核", "已通过审核", "已被审核拒绝"], ['设定', '毛图', '插画']
    name, id, examine, type = Get['name'], Get["id"], examine_name_list[examine_Number], type_name_list[type_number]
    await matcher.finish(MessageSegment.reply(event.message_id) + f"""=========FurBot=========
您查询的id为{id}的图片信息如下：
图片名字：{name}
审核结果：{examine}
图片类型：{type}
=======LingHuiBot=======""")


@Service_Status.handle()
@utils.handle_errors
async def Service_Furry_Status(matcher: Matcher, event: MessageEvent):
    a = httpx.get(
        f"{api_base}/information/feedback", timeout=timeout).json()
    code, msg = a['code'], a['msg']
    if code != "40000":
        await matcher.finish(MessageSegment.reply(event.message_id) + f"平台返回：{msg}[Code={code}]")
    else:
        time, examine, power, atlas, total, page = a['time']['count'], a['examine']['count'], a[
            'power']['count'], a['atlas']['count'], a['total']['count'], a['page']['count']
        await matcher.finish(MessageSegment.reply(event.message_id) + f"""平台返回：
==========FurBot==========
运行时长：{time}天
待审核图片数：{examine}
已公开图片数：{power}
已有图片数：{atlas}
总调用次数：{total}
-->由兽云祭API提供服务支持
========Service Status========""")

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
@utils.handle_errors
async def CU_Function(matcher: Matcher, event: MessageEvent, bot: Bot):
    Data_List, List = [], []
    Data_List = utils.handle_json(Path(Data_Path) / "Upload_Data.json", 'r')
    if Data_List == []:
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前投图待审核列表是空的")
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
        text = f"""第{i + 1}条：
上传者：{Upload_account}
上传群聊：{Group_id}
图片名称：{Name}
留言内容：{suggest}
图片类型：{type_Text[type]}"""
        User_QQ = event.user_id
        stranger_info = await bot.call_api('get_stranger_info', user_id=User_QQ, time_noend=True)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        make_text = await utils.batch_get(text, Picture_URL, event.self_id, nickname)
        List.append(make_text)
    logger.info(List)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)


@Check_Upload_Decide.handle()
@utils.handle_errors
async def CUD_Function(matcher: Matcher, event: MessageEvent, bot: Bot, args: Message = CommandArg()):
    await matcher.send("将通过凌辉Bot内置账户进行处理")
    Data_Message = event.get_message()
    args = str(args)
    args = args.split("#")
    Temp_args = args
    args = int(args[0])
    List = utils.handle_json(Path(Data_Path) / "Upload_Data.json", 'r')
    logger.info(List)
    logger.info(Temp_args)
    if args > len(List):
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "错误：输入的值超出列表项目\n请确认列表项目后重试。")
    if List == []:
        await matcher.finish(MessageSegment.reply(event.message_id) + "遇到问题：似乎没有待审核的图片。")
    Data_Normal = List[args - 1]
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
        del List[args - 1]
        utils.handle_json(Path(Data_Path) / "Upload_Data.json", 'w', List)

        Data_Message = str(Data_Message)
        if Data_Message.count("#") != 2:
            Caution = "管理员没有填写"
        else:
            Caution = Temp_args[1]
        if event.group_id != Group_id:
            await bot.call_api("send_group_msg", group_id=Group_id, message=f"""凌辉Bot管理员已拒绝了来自{account}的投图请求
拒绝理由：{Caution}
【上传时间戳：{time.strftime("%Y-%m-%d %H:%M:%S", Time)}】
下面是打回图片的详细信息：
图片名字：{Name}
图片类型：{TypeValue}
图片留言：{Suggest}
图片内容：""" + MessageSegment.image(f"{Pic_URL}"), time_noend=True)
        os.remove(f"{Pic_URL}")
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"拒绝上载的操作已完成\n传入拒绝理由参数：{Caution}")

    with open(f"{Pic_URL}", 'rb') as f:
        async with httpx.AsyncClient(timeout=timeout) as client:
            a = await client.post(f"{api_base}/function/upload", data=Data_Normal,
                                  files={'file': ('Upload.png', f, 'image/png')})
            a = a.json()
    logger.info(a)
    if a['code'] != '20000':
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"好像没有上传成功呢...？\n{a['msg']}[{a['code']}]")
    msg = a['msg']
    code = a['code']
    id = a['id']
    picture = a['picture']
    if code != "20000":
        await matcher.finish(MessageSegment.reply(event.message_id) + f"错误：{msg}[Code={code}]")
    else:
        text = f"""API返回信息：{msg}[Code={code}]
======传入参数======
图片名字:{Name}
图片类型:{TypeValue}
图片留言:{Suggest}
======服务器数据=======
您的数字id：{id}
您的图片码：{picture}"""
        del List[args - 1]
        utils.handle_json(Path(Data_Path) / "Upload_Data.json", 'w', List)
        if event.group_id != Group_id:
            await bot.call_api("send_group_msg", group_id=Group_id, message=f"""凌辉Bot管理员已经同意了来自{account}的投图请求，请等待兽云祭管理员进行审核
上载图片：""" + MessageSegment.image(f"{Pic_URL}") + f"""数字id：{id}
【上传时间戳：{time.strftime("%Y-%m-%d %H:%M:%S", Time)}】""", time_noend=True)
        await bot.call_api("send_group_msg", group_id=event.group_id,
                           message=f"{text}\n上载图片：" + MessageSegment.image(f"{Pic_URL}"), time_noend=True)
        os.remove(f"{Pic_URL}")

@Upload_Clear.handle()
async def UC_Function(matcher: Matcher):
    Temp_Path = Data_Path / "Upload_Data.json"
    Dir_Path = Data_Path / "Batch"
    if os.path.exists(Temp_Path):
        os.remove(Temp_Path)
    if os.path.exists(Dir_Path):
        shutil.rmtree(Dir_Path)
    with open(Temp_Path, 'w', encoding='utf-8') as f:
        f.write("[]")
    await matcher.finish("操作已完成。")
