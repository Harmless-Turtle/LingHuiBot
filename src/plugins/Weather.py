# 导入依赖库
from nonebot.plugin import on_command  # 导入事件响应器
from nonebot.adapters import Message  # 导入抽象基类Message以允许Bot回复str
from nonebot.params import CommandArg
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent, Bot  # 导入事件响应器以进行操作
from nonebot import logger
from datetime import datetime
import httpx
import os
import traceback
import time
import pandas as pd

weather = on_command("weather", aliases={"天气查询"}, priority=10, block=True)
Path = "/home/LingHui/NoneBot/LingHuiBot/data/Main/附件001-中国地面气象站点清单.xlsx"

@weather.handle()
async def handle_function(matcher:Matcher,bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    if not args.extract_plain_text():await matcher.finish(MessageSegment.reply(event.message_id)+"未找到城市信息")
    args = str(args)
    Data_Normal = pd.read_excel(Path)
    Dict,Province_Dict,List = {},{},[]
    try:
        for index, row in Data_Normal.iterrows():
            province = row['省份']
            city = row['站名']
            # 如果省份不在字典中，添加它
            if province not in Dict:
                Dict[province] = {}
                Province_Dict[province] = {}
            
            # 如果城市不在省份的子字典中，添加它，并初始化一个空列表
            if city not in Dict[province]:
                Dict[f"{province}{city}"] = []
                Province_Dict[province][city] = []
            
            # 将剩余的数据添加到城市的列表中
            Dict[f"{province}{city}"] = [row['区站号'], row['纬度'], row['经度'],
                                        row['气压传感器拔海高度（米）'], row['观测场拔海高度（米）']]
            Province_Dict[province][city] = [row['区站号'], row['纬度'], row['经度'],
                                        row['气压传感器拔海高度（米）'], row['观测场拔海高度（米）']]
        Dict_Key = list(Dict.keys())        #存放省份的列表
        if Dict.get(args,True) and args not in Dict_Key and Province_Dict.get(args,True):
            await matcher.send(MessageSegment.reply(event.message_id)+"遇到问题：暂未查找到对应地区的站点\n将使用备选API查找...")
            a = httpx.get(f"https://oiapi.net/API/weather/?city={args}").json()
            Data = a['data']
        Select_Area = Dict.get(args)
        if Select_Area == {}:
            for i in Dict:
                if args in i:
                    Select_Area = list(list(Province_Dict.get(args).items())[0])[1]
                    break
        Select_Station,Station_latitude,Station_longitude,Pressure_sensor,Observation_field = Select_Area[0],Select_Area[1],Select_Area[2],Select_Area[3],Select_Area[4]
        now = datetime.now()
        Start_Time = datetime(now.year, now.month, now.day)
        Start_Time = Start_Time.strftime('%Y%m%d%H%M%S')
        End_Time = now.strftime('%Y%m%d%H%M%S')
        # 原始时间字符串
        Start_time_str = f"{Start_Time}"
        End_time_str = f"{End_Time}"
        # 将字符串转换为datetime对象
        # 这里的格式'%Y%m%d%H%M%S'对应于原始字符串的格式
        Start_time_obj = datetime.strptime(Start_time_str, '%Y%m%d%H%M%S')
        End_time_obj = datetime.strptime(End_time_str,'%Y%m%d%H%M%S')
        # 使用strftime方法格式化时间
        Start_formatted_time = Start_time_obj.strftime('%Y年%m月%d日%H时%M分%S秒')
        End_formatted_time = End_time_obj.strftime('%Y年%m月%d日%H时%M分%S秒')
        Find_key = next((Find_key for Find_key, value in Dict.items() if value == Select_Area), None)
        Text = f"""读取站点：{Find_key}[{Select_Station}]
站点信息：
经纬度：({Station_latitude},{Station_longitude})
气压传感器海拔高度：{int(Pressure_sensor)}m
观测场海拔高度：{int(Observation_field)}m
查询时间区间：{Start_formatted_time}~{End_formatted_time}"""
        stranger_info = await bot.call_api('get_stranger_info', user_id=event.user_id)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        List.append(MessageSegment.node_custom(
        user_id=event.user_id,
        nickname=f"{nickname}",
        content=Message(Text)
        ))
        Get_Data = httpx.get(f"http://api.data.cma.cn:8090/api?userId=732103897094GObN8&pwd=XjZsq9l&dataFormat=json&interfaceId=getSurfEleByTimeRangeAndStaID&dataCode=SURF_CHN_MUL_HOR_3H&timeRange=[{Start_Time},{End_Time}]&staIDs={Select_Station}&elements=Station_Id_C,Year,Mon,Day,Hour,PRS,PRS_Sea,PRS_Max,PRS_Min,TEM,TEM_Max,TEM_Min,RHU,RHU_Min,VAP,PRE_1h,WIN_S_Max,WIN_D_S_Max,WIN_S_Avg_10mi,WIN_D_Avg_10mi,WIN_S_Inst_Max").json()
        if Get_Data['returnCode'] != "0":
            Text = Get_Data['returnMessage']
            await matcher.finish(MessageSegment.reply(event.message_id)+f"服务器返回：{Text}")
        Data = Get_Data["DS"]
        Count = 0
        for i in Data:
            # 时间
            Year,Month,Day,Hour = i['Year'],i['Mon'],i['Day'],i['Hour']
            # 气压
            PRS,PRS_Sea,PRS_Max,PRS_Min = i['PRS'],i['PRS_Sea'],i['PRS_Max'],i['PRS_Min']
            # 温度
            TEM,TEM_Max,TEM_Min = i['TEM'],i['TEM_Max'],i['TEM_Min']
            # 湿度
            RHU,RHU_Min = i['RHU'],i['RHU_Min']
            # 水汽压、降水量
            VAP,PRE_1h = i['VAP'],i['PRE_1h']
            # 风速信息
            WIN_S_Max,WIN_D_S_Max,WIN_S_Avg_10mi,WIN_D_Avg_10mi,WIN_S_Inst_Max = i['WIN_S_Max'],i['WIN_D_S_Max'],i['WIN_S_Avg_10mi'],i['WIN_D_Avg_10mi'],i['WIN_S_Inst_Max']
            Count += 1
            Text = f"""站点传感器第{Count}次回报时间为：{Year}年{Month}月{Day}日{Hour}时次
温度数据：
温度/气温：{int(float(TEM))}℃
最高气温：{int(float(TEM_Max))}℃
最低气温：{int(float(TEM_Min))}℃

气压数据：
气压：{int(float(PRS))}hPa
海平面气压：{int(float(PRS_Sea))}hPa
最高气压：{int(float(PRS_Max))}hPa
最低气压：{int(float(PRS_Min))}hPa

风力数据：
最大风速：{int(float(WIN_S_Max))}m/s
最大风速的风向：{WIN_D_S_Max}°
10分钟平均风速：{int(float(WIN_S_Avg_10mi))}m/s
10分钟平均风向：{WIN_D_Avg_10mi}°
极大风速：{int(float(WIN_S_Inst_Max))}m/s

湿度数据：
相对湿度：{int(float(RHU))}%
最小相对湿度：{int(float(RHU_Min))}%

水汽压：{VAP}hPa
降水量：{PRE_1h}mm"""
            List.append(MessageSegment.node_custom(
        user_id=event.user_id,
        nickname=f"{nickname}",
        content=Message(Text)
        ))

        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=List, time_noend=True)
        await matcher.finish()
    except MatcherException:  # 执行完成，接住抛出的FinishedException异常以结束本次事件执行
        # 注：此处必须要接住该异常，否则事件将无法正常结束。
        raise  # 什么都不需要做，接住就行
    except:
        logger.error("遇到问题，错误日志已经追加至error.txt")
        error_dir = os.path.join(os.path.dirname(__file__), "error.txt")
        with open(error_dir, 'a', encoding='utf-8') as f:
            a = __file__
            f.write(
                f"脚本：{a}\n在“{time.strftime('%Y-%m-%d %a %H:%M:%S', time.localtime())}”时返回了异常错误。内容如下：\n\n")
            traceback.print_exc(file=f)
            f.write("\n---------------------异常错误截止---------------------\n\n")