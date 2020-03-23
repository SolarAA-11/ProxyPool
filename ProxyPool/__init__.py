import asyncio

from .storage import ProxyPoolStorage
from .jobfactory import CrawlJobFactory, ValidateJobFactory
from .network import NetManager
# 综合调度 网络模块 工厂模块
class ProxyPool:
    
    def __init__(
        self,
        *,
        crawl_job_interval_hour = 24, # 代理抓取任务间隔时间 小时
        validate_job_interval_minute = 5, # 代理池验证任务间隔时间 分钟
        timeout = 20, # 请求超时时间
        max_retry_count = 10, # CrawlJob 最多尝试次数
        max_concurrent_request = 500, # 最大并发请求数量
    ):
        self.storage = ProxyPoolStorage()
        self.crawl_job_factory = CrawlJobFactory()
        self.validate_job_factory = ValidateJobFactory()
        self.net_manager = NetManager(
            timeout=timeout,
            max_retry_count=max_retry_count,
            max_concurrent_request=max_concurrent_request
        )
        self.crawl_job_interval = crawl_job_interval_hour * 3600
        self.validate_job_interval = validate_job_interval_minute * 60


    # crawljob 生产协程 根据设置 每隔一段时间 向网络模块中入队任务
    async def crawljob_producer(self):
        self.net_manager.event_crawl_job_finish.clear()

        for crawl_job in self.crawl_job_factory.get_jobs():
            self.net_manager.append_job(crawl_job)
        
        await self.net_manager.event_crawl_job_finish.wait()
        await asyncio.sleep(self.crawl_job_interval)

    # validate job 生产协程 每隔一段时间 向网络模块中入队任务
    async def validatejob_producer(self):
        self.net_manager.event_validate_job_finish.clear()

        for validate_job in self.validate_job_factory.get_jobs():
            self.net_manager.append_job(validate_job)
        
        await self.net_manager.event_validate_job_finish.wait()
        await asyncio.sleep(self.validate_job_interval)

    # 从代理池中获取代理
    def get(self):
        return self.storage.get()


# 返回 经过初始化的 ProxyPool 实例
async def create_proxypool(
    *,
    crawl_job_interval_hour = 24, # 代理抓取任务间隔时间 小时
    validate_job_interval_minute = 5, # 代理池验证任务间隔时间 分钟
    timeout = 20, # 请求超时时间
    max_retry_count = 10, # CrawlJob 最多尝试次数
    max_concurrent_request = 500, # 最大并发请求数量
) -> ProxyPool:
    proxy_pool = ProxyPool(
        crawl_job_interval_hour=crawl_job_interval_hour,
        validate_job_interval_minute=validate_job_interval_minute,
        timeout=timeout,
        max_retry_count=max_retry_count,
        max_concurrent_request=max_concurrent_request
    )
    proxy_pool.net_manager.run()
    await asyncio.gather(
        proxy_pool.crawljob_producer(), 
        proxy_pool.validatejob_producer()
    )
    return proxy_pool

