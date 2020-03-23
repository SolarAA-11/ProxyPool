import asyncio

from .spider import ProxySpider
from .models import ProxyItem
from .validator import ProxyPoolValidator
from .storage import ProxyPoolStorage

# 代理池
class ProxyPool:
    def __init__(
        self,
        *,
        crawl_proxy_interval_hour:int = 24, # 爬取代理网站代理的间隔时间 单位为 小时
        validate_interval_minutes:int = 3, # 验证代理池代理有效性的时间间隔 单位为 分钟
    ):
        self.spider = ProxySpider()
        self.storage = ProxyPoolStorage()
        self.crawl_proxy_interval_hour = crawl_proxy_interval_hour
        self.crawl_task = asyncio.create_task(self.crawl_proxy())

        self.validator:ProxyPoolValidator = ProxyPoolValidator(
            run_interval=validate_interval_minutes,
            max_concurrent_req=5000,
            timout=25
        )
        self.validator.run_detach()
    
    # 获取单个可用代理
    def get_proxy(self):
        return self.storage.get()
    
    # 抓取代理 每隔一段时间运行
    async def crawl_proxy(self):
        while True:
            print("开始爬取")
            proxy_list = await self.spider.get_proxy_list()
            count = 0
            for proxy in proxy_list:
                b = self.storage.add(proxy)
                count += int(b)
            print("本次爬取一共爬取 {} 个".format(count))
            await asyncio.sleep(self.crawl_proxy_interval_hour * 3600)
    
