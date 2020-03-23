import asyncio

from fastapi import FastAPI
import uvicorn
from ProxyPool import ProxyPool, ProxyItem

app = FastAPI()
proxy_pool: ProxyPool = None

@app.on_event("startup")
async def startup_event():
    global proxy_pool
    proxy_pool = ProxyPool()

@app.get("/item", response_model=ProxyItem)
async def get_one_proxy():
    return proxy_pool.get_proxy() 


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)