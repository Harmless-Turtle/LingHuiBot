import json

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed

from ...utils import get_api_httpx,handle_json
from ..check_file import fec_buildId

async def update_buildId():
    raw_data = await get_api_httpx("https://www.furrycons.cn/", raw_response=True)
    soup = BeautifulSoup(raw_data, "html.parser")
    scripts = soup.find("script", id="__NEXT_DATA__")
    new_buildId = json.loads(scripts.string).get("buildId")
    buildId = handle_json(fec_buildId, 'r')
    if buildId != new_buildId:
        handle_json(fec_buildId, 'w', {"buildId": new_buildId})

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_api(endpoint):
    async with httpx.AsyncClient(timeout=30.0) as client:
        buildId = handle_json(fec_buildId, 'r').get("buildId")
        resp = await client.get(f"https://www.furrycons.cn/_next/data/{buildId}/zh-Hans/{endpoint}.json")
        if resp.status_code != 200:
            await update_buildId()
            resp = await client.get(f"https://www.furrycons.cn/_next/data/{buildId}/zh-Hans/{endpoint}.json")
    return resp.json()