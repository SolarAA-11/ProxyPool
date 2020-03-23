import asyncio
from asyncio import Semaphore
from typing import Tuple, List

import aiohttp

from .models import ProxyItem
from .storage import ProxyPoolStorage

# 代理池验证器
class ProxyPoolValidator:
    def __init__(
        self, 
        *, 
        run_interval: int = 5, # 验证的间隔时间
        max_concurrent_req: int = 1000, # 最大并发请求量
        timout: int = 20, # 验证超时时间
    ):
        self.run_interval = 5
        self.storage = ProxyPoolStorage()
        self.total_proxy_count = 0
        self.activate_proxy_count = 0
        self.current_finish_check_count = 0
        self.session: aiohttp.ClientSession = None
        self.run_task: asyncio.Task = None
        self.semaphore_max_concurrent_req: Semaphore = Semaphore(max_concurrent_req)
        self.timeout = timout

    def run_detach(self):
        self.run_task = asyncio.create_task(self.start())

    # 验证代理是否有效
    async def check_proxy_item(self, proxy: ProxyItem) -> bool:
        is_activated = False
        status_code, content = None, None

        try:
            proxy_url = "http://{ip}:{port}".format(**proxy.dict())
            async with self.semaphore_max_concurrent_req:
                # async with self.session.get(
                #         "https://httpbin.org/ip", 
                #         proxy=proxy_url, 
                #         timeout=self.timeout
                #     ) as resp:
                #     status_code, content = resp.status, await resp.json()
                async with self.session.get(
                        "https://www.baidu.com", 
                        proxy=proxy_url, 
                        timeout=self.timeout
                    ) as resp:
                    status_code, content = resp.status,{"origin": proxy.ip}
            # print(status_code, content)
            # print(proxy)
        except Exception as e:
            pass
            # print("Exception", e)

        if status_code == 200 and content and content.get("origin", "") == proxy.ip:
            is_activated = True
        return is_activated

    # 开始验证整个代理池
    async def validate_proxy_pool(self) -> Tuple[int, int]:
        # 获取代理池全部代理列表
        proxy_list: List[ProxyItem] = self.storage.get_all()
        self.total_proxy_count = len(proxy_list)

        
        task2proxy: Dict[asyncio.Task, ProxyItem] = dict()

        # task 的 回调函数 将检测结果反馈至数据库
        def _on_complete(task: asyncio.Task):
            proxy = task2proxy[task]
            if task.result(): 
                self.storage.activate(proxy)
                self.activate_proxy_count += 1
                print("OK")
            else: self.storage.deactivate(proxy)
            self.current_finish_check_count += 1
            print("代理池验证器: {}/{}".format(self.current_finish_check_count, self.total_proxy_count))


        # 迭代列表 构造并行任务 
        for proxy in proxy_list:
            task = asyncio.create_task(self.check_proxy_item(proxy))
            task.add_done_callback(_on_complete)
            task2proxy[task] = proxy

        # await 等待并行任务结束
        await asyncio.gather(*task2proxy.keys())

        return self.activate_proxy_count, self.total_proxy_count


    # 启动验证协程 
    async def start(self):
        async with aiohttp.ClientSession() as self.session:
            while True:
                self.total_proxy_count = 0
                self.activate_proxy_count = 0
                self.current_finish_check_count = 0

                activated, total = await self.validate_proxy_pool()
                print("代理池验证器: 一共 {} 个， 有效 {} 个".format(total, activated))

                await asyncio.sleep(self.run_interval)