from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent, MessageEvent
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from typing import Dict, List, Set, Union
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.matcher import Matcher
from nonebot import on_command
from pathlib import Path
from io import BytesIO
from PIL import Image
import ujson as json
import random

from ..commands import tarot,divine
from src.plugins.utils import handle_errors

tarot_path: Path = Path(__file__).parent / "resource"
tarot_official_themes: List[str] = ["BilibiliTarot", "TouhouTarot"]
# __tarot_version__ = "v0.4.0.post4"
# __tarot_usages__ = f'''
# 塔罗牌 {__tarot_version__}
# [占卜] 随机选取牌阵进行占卜
# [塔罗牌] 得到单张塔罗牌回应'''.strip()

class EventNotSupport(Exception):
    pass

@tarot.handle()
@handle_errors
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text(): await matcher.finish()

    # 1. 从两种塔罗牌中随机输出一种的名字
    theme: str = random.choice(tarot_official_themes)

    # 2. 从所有塔罗牌信息中随机出一张
    with open(Path(__file__).parent / "resource/tarot.json", 'r', encoding='utf-8') as f:
        content = json.load(f)
        all_cards = content.get("cards")    # 所有的塔罗牌信息
    
    if theme == "BilibiliTarot":
        sub_types: List[str] = ["MajorArcana", "Cups", "Pentacles", "Sowrds", "Wands"]

    if theme == "TouhouTarot":
        sub_types: List[str] = ["MajorArcana"]
    
    subset: Dict[str, Dict[str, Union[str, Dict[str, str]]]] = {
        k: v for k, v in all_cards.items() if v.get("type") in sub_types
    }
    cards_index: List[str] = random.sample(list(subset), 1)
    cards_info: List[Dict[str, Union[str, Dict[str, str]]]] = [
        v for k, v in subset.items() if k in cards_index]
    
    # 3. 由文本获取指定图片
    card_info = cards_info[0]

    _type: str = card_info.get("type")
    _name: str = card_info.get("pic")
    img_name: str = ""
    img_dir: Path = tarot_path / theme / _type

    # Consider the suffix of pictures
    for p in img_dir.glob(_name + ".*"):
        img_name = p.name
    if img_name == "":
        await matcher.finish("没找到对应塔罗牌")
    else:
        img: Image.Image = Image.open(img_dir / img_name)
    # 3. Choose up or down
    name_cn: str = card_info.get("name_cn")
    if random.random() < 0.5:
        # 正位
        meaning: str = card_info.get("meaning").get("up")
        msg = MessageSegment.text(f"这是一张「{name_cn}正位」\n其意义为「{meaning}」\n")
    else:
        meaning: str = card_info.get("meaning").get("down")
        msg = MessageSegment.text(f"这是一张「{name_cn}逆位」\n其意义为「{meaning}」\n")
        img = img.rotate(180)

    buf = BytesIO()
    img.save(buf, format='png')

    await matcher.finish("你翻开了一张塔罗牌...\n" + msg + MessageSegment.image(buf))



@divine.handle()
@handle_errors
async def general_divine(bot: Bot, matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text(): await matcher.finish()
    
    # 1. 从两种塔罗牌中随机输出一种的名字
    theme: str = random.choice(tarot_official_themes)

    with open(Path(__file__).parent / "resource/tarot.json", 'r', encoding='utf-8') as f:
        content = json.load(f)
        all_cards = content.get("cards")
        all_formations = content.get("formations")

        formation_name = random.choice(list(all_formations))
        formation = all_formations.get(formation_name)

    await matcher.send(f"启用{formation_name}，正在洗牌中")

    # 2. Get cards of "cards_num"
    cards_num: int = formation.get("cards_num")

    if theme == "BilibiliTarot":
        sub_types: List[str] = ["MajorArcana", "Cups", "Pentacles", "Sowrds", "Wands"]

    if theme == "TouhouTarot":
        sub_types: List[str] = ["MajorArcana"]

    if len(sub_types) < 1:
        await matcher.finish("资源完整性不通过")

    subset: Dict[str, Dict[str, Union[str, Dict[str, str]]]] = {
        k: v for k, v in all_cards.items() if v.get("type") in sub_types
    }

    cards_index: List[str] = random.sample(list(subset), cards_num)
    cards_info: List[Dict[str, Union[str, Dict[str, str]]]] = [
        v for k, v in subset.items() if k in cards_index]

    # 3. Get the text of representations
    is_cut: bool = formation.get("is_cut")
    representations: List[Union[str, List[str]]] = random.choice(
        formation.get("representations"))
    
    # 4. Genrate message
    chain = []
    for i in range(cards_num):
        # Select the #i tarot
        if is_cut and i == cards_num - 1:
            msg_header = MessageSegment.text(f"切牌「{representations[i]}」\n")
        else:
            msg_header = MessageSegment.text(
                f"第{i+1}张牌「{representations[i]}」\n")

        card_info = cards_info[i]

        _type: str = card_info.get("type")
        _name: str = card_info.get("pic")
        img_name: str = ""
        img_dir: Path = tarot_path / theme / _type

        # Consider the suffix of pictures
        for p in img_dir.glob(_name + ".*"):
            img_name = p.name
        if img_name == "":
            await matcher.finish("没找到对应塔罗牌")
        else:
            img: Image.Image = Image.open(img_dir / img_name)
        # 3. Choose up or down
        name_cn: str = card_info.get("name_cn")
        if random.random() < 0.5:
            # 正位
            meaning: str = card_info.get("meaning").get("up")
            msg = MessageSegment.text(f"「{name_cn}正位」「{meaning}」\n")
        else:
            meaning: str = card_info.get("meaning").get("down")
            msg = MessageSegment.text(f"「{name_cn}逆位」「{meaning}」\n")
            img = img.rotate(180)

        buf = BytesIO()
        img.save(buf, format='png')

        flag, msg_body = True, msg + MessageSegment.image(buf)

        if not flag:
            await matcher.finish(msg_body)

        if isinstance(event, PrivateMessageEvent):
            if i < cards_num:
                await matcher.send(msg_header + msg_body)
            else:
                await matcher.finish(msg_header + msg_body)

        elif isinstance(event, GroupMessageEvent):
            nickname: Set[str] = {"Bot"}
            data = {
                "type": "node",
                "data": {
                    "name": list(nickname)[0],
                    "uin": bot.self_id,
                    "content": msg_header + msg_body
                },
            }
            chain.append(data)
        else:
            raise EventNotSupport

    await bot.send_group_forward_msg(group_id=event.group_id, messages=chain)
