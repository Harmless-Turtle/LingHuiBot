from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    Message,
    Bot,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import on_command
from sqlalchemy import inspect

from src.plugins import utils
from src.plugins.DataBase.models import create_item_model, Base, engine

Test = on_command("Test")
@Test.handle()
@utils.handle_errors
async def Test_Function(matcher: Matcher, bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    args = str(args).strip()
    List = args.split(" ")
    if len(List) < 3:
        await matcher.finish("请提供至少3个参数：表名、name、data，可选第4个参数为count")
    table_name = List[0]
    name = List[1]
    data = List[2]
    count = int(List[3]) if len(List) > 3 else 0

    Item = create_item_model(table_name)
    inspector = inspect(engine)
    if table_name in inspector.get_table_names():
        logger.success(f"表 {table_name} 已存在")
    else:
        logger.warning(f"表 {table_name} 不存在，将在MySQL中新建表")
        Base.metadata.create_all(bind=engine, checkfirst=True)

    Item.create(name=name, data=data, count=count)

    db_url = engine.url
    db_name = db_url.database
    msg = f"已在 {db_name} 数据库中的 {table_name} 表新建了 name 为 {name}，data 为 {data} 的数据"
    await matcher.finish(MessageSegment.reply(event.message_id) + msg)
