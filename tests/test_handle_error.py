from nonebot import logger
from nonebot.plugin.on import on_command, on_message
from nonebot.rule import to_me

from src.plugins.utils import handle_errors

# testmsg = on_message(to_me())

@testmsg.handle
@handle_errors
async def test_function(matcher:Matcher):
    raise Exception("This is a test exception.")
    # logger.info("Test function executed successfully.")
    # await testmsg.finish("This is a test message from the test plugin.")

