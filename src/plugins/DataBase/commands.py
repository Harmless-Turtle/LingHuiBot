# plugins/sql_tool/commands.py
from typing import List
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from .models import create_item_model, Base, engine

# ====== 命令注册 ======
add_item    = on_command("sql_add",    priority=5, block=True)
del_item    = on_command("sql_del",    priority=5, block=True)
update_item = on_command("sql_update", priority=5, block=True)
get_item    = on_command("sql_get",    priority=5, block=True)
list_items  = on_command("sql_list",   priority=5, block=True)

# ====== 命令实现 ======
@add_item.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    # 预期格式：name value
    if not text:
        await matcher.finish("用法：/sql_add <name> [value]")
    parts = text.split(maxsplit=1)
    name, value = parts[0], (parts[1] if len(parts) > 1 else None)
    try:
        create_item_model.create(name=name, data=value)
        await matcher.finish(f"已添加：{name}")
    except Exception as e:
        await matcher.finish(f"添加失败：{e}")

@del_item.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    try:
        pk = int(args.extract_plain_text().strip())
        item = create_item_model.get(pk)
        if not item:
            await matcher.finish("未找到记录")
        item.delete()
        await matcher.finish(f"已删除 id={pk}")
    except ValueError:
        await matcher.finish("用法：/sql_del <id>")
    except Exception as e:
        await matcher.finish(f"删除失败：{e}")

@update_item.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    # 预期格式：id name value
    if not text:
        await matcher.finish("用法：/sql_update <id> <name> [value]")
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        await matcher.finish("参数不足")
    try:
        pk, name, value = int(parts[0]), parts[1], (parts[2] if len(parts) == 3 else None)
        item = create_item_model.get(pk)
        if not item:
            await matcher.finish("未找到记录")
        item.update(name=name, data=value)
        await matcher.finish(f"已更新 id={pk}")
    except ValueError:
        await matcher.finish("id 必须为整数")
    except Exception as e:
        await matcher.finish(f"更新失败：{e}")

@get_item.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    try:
        pk = int(args.extract_plain_text().strip())
        item = create_item_model.get(pk)
        if not item:
            await matcher.finish("未找到记录")
        await matcher.finish(f"id={item.id}\nname={item.name}\ndata={item.data}")
    except ValueError:
        await matcher.finish("用法：/sql_get <id>")
    except Exception as e:
        await matcher.finish(f"查询失败：{e}")

@list_items.handle()
async def _(matcher: Matcher):
    rows: List[create_item_model] = create_item_model.list_all()
    if not rows:
        await matcher.finish("当前无数据")
    msg = "当前列表：\n" + "\n".join([f"{r.id}: {r.name} | {r.data}" for r in rows])
    await matcher.finish(MessageSegment.text(msg))