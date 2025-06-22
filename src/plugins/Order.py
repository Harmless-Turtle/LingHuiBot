from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent, 
    MessageSegment, 
    MessageEvent, 
    Message,
    )
from nonebot.params import CommandArg
from pathlib import Path
import json,httpx,random,os

async def chek_rule_at(event: GroupMessageEvent):
    s = event.user_id
    if s == 1815984076 or s == 1097740481:
        return True
    else:
        return False

Order = on_command("点菜",aliases={"点餐"},priority=20)
Upload_Order = on_command("上传饮品",aliases={"添加饮品"},rule=chek_rule_at,priority=20)
Delete_Order = on_command("删除饮品",rule=chek_rule_at,priority=20)

opendata = Path.cwd()
Data_Path = opendata / 'data/Order_System'

@Order.handle()
async def Order_Function(event:MessageEvent,args:Message = CommandArg()):
    args = str(args)
    with open(f"{Data_Path}/List.json",'r',encoding='utf-8') as f:
        Data = json.load(f)

    Key,Value = list(Data.keys()),list(Data.values())
    Select = random.randint(0,len(Key)-1)
    Text,Picture = Key[Select],Value[Select]
    await Order.finish(MessageSegment.reply(event.message_id)+f"您好~您的饮品是{Text}，请慢用~\n"+MessageSegment.image(Picture))

@Upload_Order.handle()
async def Upload_Order_Function(event:MessageEvent,args:Message = CommandArg()):
    args = str(args)
    Data = args.split("#")
    if len(Data) != 3:
        await Upload_Order.finish(MessageSegment.reply(event.message_id)+"输入格式不正确，请重新上传\n正确的格式应该是：上传饮品#饮品名字#饮品图片")
    Name = Data[1]
    msggroup = event.get_message()
    url = msggroup["image"]
    pic_url = list(url)[-1].data["url"]
    with open(f"{Data_Path}/Picture/{Name}.jpg",'wb') as f,open(f"{Data_Path}/List.json",'r',encoding='utf-8') as F:
        f.write(httpx.get(pic_url).content)
        Dict = json.load(F)
    Dict[f"{Name}"] = f"{Data_Path}/Picture/{Name}.jpg"
    with open(f"{Data_Path}/List.json",'w',encoding='utf-8') as f:
        json.dump(Dict,f,ensure_ascii=False)
        
    await Upload_Order.finish(MessageSegment.reply(event.message_id)+"操作成功完成。")

@Delete_Order.handle()
async def Delete_Order_Function(event:MessageEvent,args:Message = CommandArg()):
    args = str(args)
    with open(f"{Data_Path}/List.json",'r',encoding='utf-8') as f:
        Dict = json.load(f)

    if Dict.get(args,None) == None:
        await Delete_Order.finish(MessageSegment.reply(event.message_id)+f"遇到问题：在饮品列表里没有找到{args}")
    del Dict[f'{args}']
    os.remove(f"{Data_Path}/Picture/{args}.jpg")
    with open(f"{Data_Path}/List.json",'w',encoding='utf-8') as f:
        json.dump(Dict,f,ensure_ascii=False)
        
    await Delete_Order.finish(MessageSegment.reply(event.message_id)+"操作成功完成。")