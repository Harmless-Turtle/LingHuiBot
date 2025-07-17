from nonebot.plugin import on_command,on_message
# 导入异常基类MatcherException，以限制try-except捕获正常finish函数抛出的异常
from nonebot.exception import MatcherException
# 导入事件响应器以进行操作
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent,
    Message,
    Bot
)
from .Handler import Handler
from nonebot.rule import to_me
from nonebot_plugin_alconna.uniseg import UniMsg, At, Reply
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER  # 导入SUPERUSER库以限制仅SUPERUSER用户组可用命令
import os,zhconv,re,json,emoji,httpx,shutil,time
from pathlib import Path
from nonebot.matcher import Matcher
from nonebot import logger
from nonebot import get_driver

FurryBar = on_message(rule=to_me(),priority=60, block=True)
change_config = on_command("更改用户信息",aliases={"创建用户信息","定义个人信息"},block=False)
Reset_FurryBar = on_command(
    "Reset", aliases={"重置对话", "重置模型"})
Clear = on_command("删除信息",aliases={"重置fb","清空数据"})
latest = on_command("上次对话",aliases={"上次聊天","最后对话","最后记录"})

config = get_driver().config
KEY = config.furry_token

opendata = Path.cwd()
Normal_Path = opendata / "data"/"Furry_System"/"FurryBar"/"FurryBar_Normal.json"
# Model_Path = opendata / "data/Furry_System/FurryBar/model.json"

@FurryBar.handle()
@Handler.handle_errors
async def FB_Function(matcher:Matcher,bot:Bot,msg: UniMsg,event: MessageEvent,Reply:GroupMessageEvent):

    # await FurryBar.finish(MessageSegment.reply(event.message_id)+"该功能正在维护，暂停提供服务")
    logger.info("FB")
    content = str(event.get_message())
    if content == "" or "reply" in str(Reply.get_event_description()) or str(event.user_id) == "2854196310" or "[CQ:at,qq=3806419216]" not in str(event.original_message) or "单词" in content: await FurryBar.finish()
    User = event.user_id
    Main_Path = opendata / f"data/Furry_System/FurryBar/{User}/{User}.json"
    Normal_Dict_Temp = opendata / f"data/Furry_System/FurryBar/{User}/{User}_Normal.json"
    Dict = opendata / f"data/Furry_System/FurryBar/{User}"
    if not os.path.exists(Dict):
        os.mkdir(Dict)
    if not os.path.exists(Main_Path):
        Temp_Dict = Handler.load_json(Normal_Path,'r')
        Handler.load_json(Main_Path,'w',Temp_Dict)
        Handler.load_json(Normal_Dict_Temp,'w',Temp_Dict)
    url = "http://fb-ai.furrybar.com:3000/v1/chat/completions"
    Model_Path = opendata / f"data/Furry_System/FurryBar/{User}/model.json"
    model = {"model":'deepseek-reasoner'}
    List = Handler.load_json(Main_Path,'r',None)
    if os.path.exists(Model_Path):
        model = Handler.load_json(Model_Path,'r',None)
    else:
        Handler.load_json(Model_Path,'w',model)
        await matcher.send("未找到用户信息，发送创建用户信息<空格><这里输入称呼><空格><这里输入文字设定或介绍>即可定义个人信息")
    model = model['model']
    simplified_text = zhconv.convert(content, 'zh-hans')
    if emoji.emoji_count(content) != 0:
        await FurryBar.finish(MessageSegment.reply(event.message_id)+"请求被驳回：检测到emoji表情。")
    Text_Dict = {
        "role": "user",
        "content": f"{simplified_text}"
    }
    if len(content) > 100:
        await FurryBar.finish(MessageSegment.reply(event.message_id)+"请求被驳回：超出请求字数上限（100字符）。")
    List.append(Text_Dict)
    model="deepseek-reasoner"
    payload = {
        'model': f"{model}",  # 从文件里面导入预设模型
        "messages": List
    }
    logger.info("Debug:将使用"+model+"模型进行答复。")
    headers = {
        'Authorization': f'{KEY}',
        'Content-Type': 'application/json'
    }
    # response = requests.post(url, headers=headers, data=payload)
    async with httpx.AsyncClient(http2=True,verify=False,timeout=httpx.Timeout(connect=10,read=60,write=60,pool=30)) as client:
        response = await client.post(url,headers=headers,json=payload)
        if response.status_code != 200:
            logger.error(f"{response.text}")
            await FurryBar.finish(MessageSegment.reply(event.message_id)+f"请求失败\n服务器返回:{response['error']['message']}[{response.status_code}]")
        if response == "":
            await FurryBar.finish(MessageSegment.reply(event.message_id)+"模型返回了空值，这可能是因为key失效或不稳定，请稍后再试。")
        Json = response.json()
        if Json.get("error") != None:
            Error_Text = Json['error']['message']
            if "模型繁忙" in str(Error_Text):
                await FurryBar.finish(MessageSegment.reply(event.message_id)+"遇到一个错误，这可能是因为模型认为该内容不适合展示或该模型繁忙，请稍后重试。")
            Normal_Data = Handler.load_json(Normal_Path,'r',None)
            Handler.load_json(Main_Path,'w',Normal_Data)
            await FurryBar.finish(MessageSegment.reply(event.message_id)+f"""遇到问题：{Error_Text}\n凌辉Bot已经自动清空了对话记录以尝试修复，请在稍后重试命令以验证是否已解决问题""")
        logger.info(Json)
        Text = Json['choices'][0]['message']['content']
        logger.info("Debug:模型回复，内容是"+Text)
        Text = Text.replace("\n","")
        Assistant_Dict = {
            "role": "assistant",
            "content": Text
        }
        List.append(Assistant_Dict)
        Handler.load_json(Main_Path,'w',List)
        logger.success("Debug:处理完成，最终输出："+Text)
        await FurryBar.finish(MessageSegment.reply(event.message_id)+Text)


@Reset_FurryBar.handle()
async def Reset_Function(event: MessageEvent):
    User = event.user_id
    Main_Path = opendata / f"data/Furry_System/FurryBar/{User}/{User}.json"
    Normal_Path = opendata / f"data/Furry_System/FurryBar/{User}/{User}_Normal.json"
    Handler.load_json(Main_Path,'w',Handler.load_json(Normal_Path,'r'))
    await Reset_FurryBar.finish(MessageSegment.reply(event.message_id)+"已重置聊天记录。")

@change_config.handle()
async def change_config_Function(event:MessageEvent,args:Message = CommandArg()):
    args = str(args)
    args_List = args.split(" ")
    logger.info(args)
    logger.info(args_List)
    # await change_config.finish()
    User = event.user_id
    Main_Path = opendata / f"data/Furry_System/FurryBar/{User}/{User}_Normal.json"
    Main_Path_Temp = opendata / f"data/Furry_System/FurryBar/{User}"
    if not os.path.exists(Main_Path_Temp):
        os.mkdir(Main_Path_Temp)
    Normal_Dict = Handler.load_json(Normal_Path,'r')
    for i in range(0,len(Normal_Dict)-1):
        if Normal_Dict[i].get("你知道我是谁吗") != None:
            del Normal_Dict[i],Normal_Dict[i+1]
    Temp_Dict_1,Temp_Dict_2 = {
        "role": "user",
        "content": "你知道我是谁吗"
    },{
        "role": "assistant",
        "content": f"当然知道呀~你是{args_List[0]}，{args_List[1]}"
        }
    Normal_Dict.append(Temp_Dict_1)
    Normal_Dict.append(Temp_Dict_2)
    Handler.load_json(Main_Path,'w',Normal_Dict)
    Temp = Temp_Dict_2['content']
    await change_config.finish(MessageSegment.reply(event.message_id)+f"已记录个人设定，内容如下：\nUser：你知道我是谁吗\nAssistant：{Temp}\n注：如需改动立即生效，请发送“重置模型”命令")
    
@Clear.handle()
async def Clear_Function(event:MessageEvent):
    User = event.user_id
    Main_Path_Temp = opendata / f"data/Furry_System/FurryBar/{User}"
    if os.path.exists(Main_Path_Temp):
        shutil.rmtree(Main_Path_Temp)
        await Clear.finish(f"已经清空了{User}的FurryBar数据。")
    else:
        await Clear.finish("清除失败：未找到个人信息。")

@latest.handle()
async def Latest_Talk(matcher:Matcher,event:MessageEvent):
    User = event.user_id
    Path = f"{opendata}/data/Furry_System/FurryBar/{User}/{User}.json"
    if not os.path.exists(Path):
        await matcher.finish(MessageSegment.reply(event.message_id)+"未找到聊天记录")
    Text = Handler.load_json(f"{opendata}/data/Furry_System/FurryBar/{User}/{User}.json",'r')
    if Text[-1]['role'] == 'system':
        await matcher.finish(MessageSegment.reply(event.message_id)+"未找到聊天记录")
    User = Text[-2]['content']
    Text = Text[-1]['content']
    Text = re.sub(r'.*?(<think.*?>|</think>|<think/>)', '', Text, flags=re.DOTALL).strip()
    await matcher.finish(MessageSegment.reply(event.message_id)+f"用户：{User}\n模型回复：{Text}\n\n为防止刷屏，已经去除思考内容。请注意辨别！")
