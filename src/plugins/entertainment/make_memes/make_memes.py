from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment
from .tools import generate_meme  # 引入上面的异步函数

meme_matcher = on_command("制作表情", aliases={"memes"})


@meme_matcher.handle()
async def handle_meme():
    # 等待生成完成，且不会卡死机器人
    try:
        result = await generate_meme("petpet")
        # 发送图片逻辑
        await meme_matcher.send(MessageSegment.image(result))
        print("生成成功！")
    except Exception as e:
        await meme_matcher.finish(f"生成失败: {e}")