import asyncio, logging, configparser, sys

import uvicorn, aiohttp, requests
from fastapi import FastAPI

from ProxyPool import ProxyPool ,create_proxypool
from ProxyPool.models import ProxyItem


app = FastAPI()
proxy_pool: ProxyPool = None

async def test_proxy():
    async with aiohttp.ClientSession() as session:
        try_count = 0
        while True:
            proxy_item = proxy_pool.get()
            proxy = "http://{ip}:{port}".format(**proxy_item.dict())
            headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36"}
            status_code, content = None, ""
            try_count += 1
            print("Try Count", try_count, proxy_item)
            try:
                async with session.get("https://avhd101.com/", proxy=proxy, headers=headers, timeout=15) as resp:
                    status_code, content = resp.status, await resp.text()
            except Exception as e:
                print("Exception:", e, sys.exc_info())
            if status_code == 200:
                print(content)
                break
@app.on_event("startup")
def on_app_startup():
    # 读取配置
    config = configparser.ConfigParser()
    config.read("pool.cfg", encoding="UTF-8")

    # 启动代理池
    global proxy_pool
    proxy_pool = create_proxypool(
        crawl_job_interval_hour=config.getint("ProxyPool", "crawl_job_interval_hour"),
        validate_job_interval_minute=config.getint("ProxyPool", "validate_job_interval_minute"),
        timeout=config.getint("ProxyPool", "timeout"),
        max_retry_count=config.getint("ProxyPool", "max_retry_count"),
        max_concurrent_request=config.getint("ProxyPool", "max_concurrent_request")
    )
    asyncio.create_task(test_proxy())

@app.get("/proxy", response_model=ProxyItem)
def get_proxy():
    return proxy_pool.get()

if __name__ == "__main__":
    # asyncio.run(main())
    uvicorn.run(
        app, 
        debug=True, 
        # logging 
        use_colors=False,
    )