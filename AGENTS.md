# LingHuiBot Agent 指南 (AGENTS.md)

## 1. 环境与工具链
- **技术栈**：Python 3.12, NoneBot2 (OneBot V11), Pydantic 2.0+, SQLAlchemy 2.0+ (`nonebot_plugin_orm`)。
- **包管理**：`uv`（安装：`uv sync`；运行：`uv run python ...`）。
- **导入规范**：插件内部及跨插件引用**强制使用相对导入**。

## 2. 插件架构规范

### 2.1 标准目录结构
```text
src/plugins/<plugin_name>/
├── __init__.py       # 校验 is_configured 后动态导入模块
├── config.py         # 继承 BaseModel，提供 is_configured 属性与启动告警
├── command.py        # 响应器注册（on_command, on_message）
├── handler.py        # 业务逻辑与事务提交（挂载 @handle_errors）
├── model.py          # ORM 模型与 CRUD（仅 flush/refresh，严禁 commit）
├── exceptions.py     # 插件异常（继承自 ..Exceptions）
└── utils.py          # 插件内部辅助函数（可选）
```

### 2.2 条件加载范式 (`config.py` & `__init__.py`)
外部配置缺失时仅输出 `logger.warning` 并跳过模块导入，不阻断 Bot 启动：

```python
# config.py
from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel, Field

class Config(BaseModel):
    ORDER_ADMIN: list = Field(default_factory=list)

    @property
    def is_configured(self) -> bool:
        return bool(self.ORDER_ADMIN)

@get_driver().on_startup
async def _():
    if not get_plugin_config(Config).is_configured:
        logger.warning("模块配置不完整，功能未启用！")

# __init__.py
from nonebot import get_plugin_config
from .config import Config

if get_plugin_config(Config).is_configured:
    from . import command, exceptions, handler, model
```

### 2.3 数据库与 Handler 范式 (`model.py` & `handler.py`)
- **CRUD (`model.py`)**：只负责数据操作、`await session.flush()` 和 `await session.refresh(obj)`，**严禁在内部调用 `commit()`**。
- **业务层 (`handler.py`)**：
  1. `@handle_errors` 必须紧贴 `async def` 上方（位于 `@cmd.handle()` 下方）。
  2. 业务/输入校验失败直接抛出 `UserVisibleError`（或其子类），交由装饰器自动回滚并回复，禁止手写重复回滚逻辑。
  3. **防 `MissingGreenlet`**：必须在 `await session.commit()` **之前**将回复所需的 ORM 属性提取为局部变量。

```python
# handler.py
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session
from ..Exceptions import LingHuiError, ModuleError, UserVisibleError
from ..utils import handle_errors
from .command import cmd
from .model import add_item

@cmd.handle()
@handle_errors
async def handle_sample(matcher: Matcher, event: MessageEvent, session: async_scoped_session):
    if not valid:
        raise UserVisibleError("输入格式不正确呢。")

    item = await add_item(session, "示例")  # 内部仅 flush & refresh
    reply_text = item.name                 # commit 前提取属性
    await session.commit()                 # Handler 统一提交事务

    await matcher.finish(MessageSegment.reply(event.message_id) + f"处理完成：{reply_text}")
```

## 3. 验证与交付标准
- **禁止编写单测**：不要新增 `pytest` / `unittest` 用例或临时测试脚本。
- **本地三步必检**：
  1. 编译检查：`uv run python -m compileall -q src bot.py`
  2. 类型检查：`uv run pyright`
  3. 启动冒烟：`uv run python bot.py`（确认输出 `Application startup complete` 且无报错）
- **真机测试提示**：完成验证后，在最终回复中提示用户进行实际上机测试，并给出具体的触发指令示例。
- **Git 提交前缀**：`feat:` / `fix:` / `refactor:` / `chore:` / `docs:`。