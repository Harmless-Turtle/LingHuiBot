import json
import re

import httpx
from bs4 import BeautifulSoup
from nonebot import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from ...utils import get_api_httpx,handle_json
from ..check_file import fec_buildId_path

async def update_buildId():
    raw_data = await get_api_httpx("https://www.furrycons.cn/", raw_response=True)
    soup = BeautifulSoup(raw_data, "html.parser")
    scripts = soup.find("script", id="__NEXT_DATA__")
    new_buildId = json.loads(scripts.string).get("buildId")
    buildId = handle_json(fec_buildId_path, 'r')
    if buildId != new_buildId:
        handle_json(fec_buildId_path, 'w', {"buildId": new_buildId})

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_api(endpoint):
    async with httpx.AsyncClient(timeout=30.0) as client:
        buildId = handle_json(fec_buildId_path, 'r').get("buildId")
        resp = await client.get(f"https://www.furrycons.cn/_next/data/{buildId}/zh-Hans/{endpoint}.json")
        if resp.status_code != 200:
            await update_buildId()
            resp = await client.get(f"https://www.furrycons.cn/_next/data/{buildId}/zh-Hans/{endpoint}.json")
    return resp.json()

def solve_cookies(html):
    m = re.search(r"<script>(.*?)</script>", html, re.S)
    if not m:
        return {}
    js = m.group(1)
    e = re.search(r"WTKkN:(\d+),bOYDu:(\d+),dtzqS:function\(a,n\)\{return a\+n\},wyeCN:(\d+)", js)
    if not e:
        return {}
    tst = int(e.group(1)) + int(e.group(2)) + int(e.group(3))
    ss = re.search(r"\(t,(\d+)\)", js)
    ssid = ss.group(1) if ss else ""
    return {"__tst_status": f"{tst}#", "EO_Bot_Ssid": ssid}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def download_image(url, save_path):
    async with httpx.AsyncClient(
        timeout=30.0,
        headers=headers,
        follow_redirects=True
    ) as client:
        logger.info(f"Downloading image from {url}")
        # 第一次请求
        response = await client.get(url)
        content_type = response.headers.get("content-type", "")
        # 正常图片
        if "image" in content_type:
            img_data = response.content
        else:
            logger.warning(f"Got challenge page: {content_type}")
            cookies = solve_cookies(response.text)
            logger.info(f"Solved cookies: {cookies}")
            # 第二次请求
            response = await client.get(url,cookies=cookies)
            content_type = response.headers.get("content-type","")
            if "image" not in content_type:
                raise RuntimeError(f"Still not image: {content_type}")
            img_data = response.content
        with open(save_path, "wb") as f:
            f.write(img_data)
        logger.info(f"Image saved {save_path}, size={len(img_data)}")
        return save_path