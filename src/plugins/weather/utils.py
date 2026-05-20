import httpx

from src.plugins.utils import handle_errors


@handle_errors
async def http_get(name:str,url: str, headers: dict) -> dict:
    """
    发送HTTP GET请求并返回响应对象。

    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"未能正确请求{name} API。[HTTP {response.status_code}]")
        return response.json()