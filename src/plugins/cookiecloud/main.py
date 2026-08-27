import os
import json
import gzip
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


@app.get("/api/config")
async def config():
    return {"enable": True}


@app.post("/update")
async def update(request: Request):
    # 读取原始请求体
    body = await request.body()

    # 检查是否是 gzip 压缩的数据，如果是则解压
    if request.headers.get("content-encoding") == "gzip":
        body = gzip.decompress(body)

    # 解析 JSON
    data = json.loads(body)

    uuid = data.get("uuid")
    if not uuid:
        raise HTTPException(status_code=400, detail="UUID is required")

    with open(os.path.join(DATA_DIR, f"{uuid}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f)

    return {"msg": "ok"}


@app.get("/get/{uuid}")
async def get(uuid: str):
    file_path = os.path.join(DATA_DIR, f"{uuid}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Not found")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)