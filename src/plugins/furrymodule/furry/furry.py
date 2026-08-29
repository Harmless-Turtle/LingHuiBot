import os
from pathlib import Path



from ..commands import (
furry_random,
furry_picture,
furry_list,
furry_status,
)
from src.plugins.utils import handle_errors


@furry_random.handle()
@handle_errors
async def furry_random_function():
    pass

@furry_picture.handle()
@handle_errors
async def furry_picture_function():
    pass

@furry_list.handle()
@handle_errors
async def furry_list_function():
    pass

@furry_status.handle()
@handle_errors
async def furry_status_function():
    pass
