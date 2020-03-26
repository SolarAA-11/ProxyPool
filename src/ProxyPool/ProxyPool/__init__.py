import asyncio, time, logging

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
        **kwargs # 剩下参数全为 抓取任务的配置参数
    ):
        self.storage = ProxyPoolStorage()
        self.crawl_job_factory = CrawlJobFactory(
            **kwargs
        )
        self.validate_job_factory = ValidateJobFactory()
        self.net_manager = NetManager(
            timeout=timeout,
            max_retry_count=max_retry_count,
            max_concurrent_request=max_concurrent_request
        )
        self.crawl_job_interval = crawl_job_interval_hour * 3600
        self.validate_job_interval = validate_job_interval_minute * 60

    # 启动 线程池 并行运行
    def detach_run(self):
        # 启动 netmanager 模块
        self.net_manager.run()
        # 并发运行 两个 consumer 协程
        asyncio.gather(
            self.crawljob_producer(), 
            self.validatejob_producer()
        )


    # crawljob 生产协程 根据设置 每隔一段时间 向网络模块中入队任务
    async def crawljob_producer(self):
        while True:
            start_time = time.time()
            self.net_manager.event_crawl_job_finish.clear()
            for crawl_job in self.crawl_job_factory.get_jobs():
                self.net_manager.append_job(crawl_job)
            await self.net_manager.event_crawl_job_finish.wait()
            finish_time = time.time()

            logging.info("代理爬取完成 爬取 {} 个页面 添加代理 {} 个 爬取失败 {} 个 耗时 {}".format(
                self.net_manager.event_crawl_job_finish.count_of_crawl_page,
                self.net_manager.event_crawl_job_finish.count_of_added_proxy,
                self.net_manager.event_crawl_job_finish.count_of_crawl_fail,
                finish_time - start_time
            ))
            await asyncio.sleep(self.crawl_job_interval)

    # validate job 生产协程 每隔一段时间 向网络模块中入队任务
    async def validatejob_producer(self):
        while True:
            start_time = time.time()
            self.net_manager.event_validate_job_finish.clear()
            for validate_job in self.validate_job_factory.get_jobs():
                self.net_manager.append_job(validate_job)
            await self.net_manager.event_validate_job_finish.wait()
            finish_time = time.time()

            logging.info("代理池验证完成 验证 {} 个代理 有效激活代理 {} 个 耗时 {}".format(
                self.net_manager.event_validate_job_finish.count_of_total_proxy,
                self.net_manager.event_validate_job_finish.count_of_activated_proxy,
                finish_time - start_time
            ))
            await asyncio.sleep(self.validate_job_interval)

    # 从代理池中获取代理
    def get(self):
        return self.storage.get()


# 返回 经过初始化的 ProxyPool 实例
def create_proxypool(
    *,
    crawl_job_interval_hour = 24, # 代理抓取任务间隔时间 小时
    validate_job_interval_minute = 5, # 代理池验证任务间隔时间 分钟
    timeout = 20, # 请求超时时间
    max_retry_count = 10, # CrawlJob 最多尝试次数
    max_concurrent_request = 500, # 最大并发请求数量
    **kwargs, # 抓取任务配置参数 全部传递给 CrawlJobFactory
) -> ProxyPool:
    proxy_pool = ProxyPool(
        crawl_job_interval_hour=crawl_job_interval_hour,
        validate_job_interval_minute=validate_job_interval_minute,
        timeout=timeout,
        max_retry_count=max_retry_count,
        max_concurrent_request=max_concurrent_request,
        **kwargs
    )
    proxy_pool.detach_run()
    return proxy_pool

