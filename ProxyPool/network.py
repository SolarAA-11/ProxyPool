import asyncio, logging, sys
from asyncio import Semaphore, Event, Queue
from typing import Dict

import aiohttp

from .models import ProxyItem, JobBase, CrawlJob, ValidateJob, JobType
from .storage import ProxyPoolStorage

logger = logging.getLogger(__name__)

# 消费 CrawlJobFactory 以及 ValidateJobFactory 产生的任务
# 管理网络请求
class NetManager:

    # Crawl Job 全部处理完毕 事件
    class EventCrawlJobFinish(Event):
        def __init__(self, *args, **kwargs):
            self.count_of_crawl_page = 0    # 爬取的页面数量
            self.count_of_crawl_fail = 0    # 爬取失败的页面数量
            self.count_of_added_proxy = 0   # 添加到 Storage 中的代理数量
            Event.__init__(self, *args, **kwargs)
        # 重置
        def clear(self):
            self.count_of_crawl_page = 0
            self.count_of_crawl_fail = 0
            self.count_of_added_proxy = 0
            Event.clear(self)
        # 添加爬取的 proxy 数量
        def add_proxy_count(self, count: int = 1):
            self.count_of_added_proxy += count
        # 添加爬取的 页面 的数量
        def add_page_count(self, count: int = 1):
            self.count_of_crawl_page += count
        # 添加爬取失败的 页面 的数量
        def add_page_fail_count(self, count: int = 1):
            self.count_of_crawl_fail += count

    # Validate Job 全部处理完毕 事件
    class EventValidateJobFinish(Event):
        def __init__(self, *args, **kwargs):
            self.count_of_total_proxy = 0 # 验证的代理总数
            self.count_of_activated_proxy = 0 # 验证激活的代理总数
            Event.__init__(self, *args, **kwargs)
        # 重置
        def clear(self):
            self.count_of_total_proxy = 0
            self.count_of_activated_proxy = 0
            Event.clear(self)
        # 设置总爬取数量
        def add_count_total_proxy(self, count: int = 1):
            self.count_of_total_proxy += count
        # 激活代理数量加一
        def add_count_activated_proxy(self, count: int = 1):
            self.count_of_activated_proxy += count
    def __init__(
        self,
        *,
        timeout = 20, # 请求超时时间
        max_retry_count = 10, # CrawlJob 最多尝试次数
        max_concurrent_request = 2000, # 最大并发请求数量
    ):
        self.crawl_job_queue = Queue()
        self.validate_job_queue = Queue()
        self.timeout = timeout
        self.max_retry_count = max_retry_count
        self.semaphore_max_concurrent_request = Semaphore(max_concurrent_request)
        self.storage = ProxyPoolStorage()
        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.event_crawl_job_finish = NetManager.EventCrawlJobFinish()
        self.event_validate_job_finish = NetManager.EventValidateJobFinish()

    # 启动 consumer 
    def run(self):
        asyncio.gather(self.crawl_job_consumer(), self.validate_job_consumer())

    # 向队列中添加任务 不同任务添加到不同队列中
    def append_job(self, job: JobBase) -> None:
        if job.job_type == JobType.CRAWL: self.crawl_job_queue.put_nowait(job)
        else: self.validate_job_queue.put_nowait(job)

    # 向互联网中请求 url 数据
    async def fetch_content(self, url: str, proxy_item: ProxyItem) -> str:
        # if url == "https://free-proxy-list.net/":
        #     with open("freeproxy.html") as f:
        #         return f.read()
        logging.debug("url: {} proxy: {}".format(url, proxy_item))
        
        status_code, content = None, ""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36"}
            proxy = "http://{ip}:{port}".format(**proxy_item.dict()) if proxy_item else None
            async with self.semaphore_max_concurrent_request:
                async with self.session.get(
                    url, 
                    proxy=proxy,
                    headers=headers,
                    timeout=self.timeout
                ) as resp:
                    status_code, content = resp.status, await resp.text()
        except Exception as e:
            pass
        return content if status_code == 200 else ""
    
    # 消费 CrawlJob
    async def crawl_job_consumer(self):
        task2job: Dict[asyncio.Task, CrawlJob] = dict()
        # task callback
        def _on_completed(task: asyncio.Task):
            crawl_job: CrawlJob = task2job[task]
            html_content:str = task.result()

            if html_content != "": # 正确获取 url 内容 调用回调
                count_added_proxy = crawl_job.callback(html_content)
                self.event_crawl_job_finish.add_page_count()
                self.event_crawl_job_finish.add_proxy_count(count_added_proxy)
            elif crawl_job.retry_count < self.max_retry_count: # 请求失败 且重试次数小于指定值 重新入队 等待下次调度
                crawl_job.retry_count += 1
                self.append_job(crawl_job)
            else: # 请求失败 耗尽重试次数
                self.event_crawl_job_finish.add_page_fail_count()
            del task2job[task]

            # 触发 crawl job 全部完成事件
            if len(task2job) == 0 and self.crawl_job_queue.qsize() == 0:
                self.event_crawl_job_finish.set()
        
        while True: # 循环监听队列
            crawl_job: CrawlJob = await self.crawl_job_queue.get()
            task = asyncio.create_task(self.fetch_content(crawl_job.target_url, self.storage.get()))
            logging.info(crawl_job)
            task.add_done_callback(_on_completed)
            task2job[task] = crawl_job

    # 消费 ValidateJob
    async def validate_job_consumer(self):
        task2job: Dict[asyncio.Task, ValidateJob] = dict()
        # task callback
        def _on_completed(task: asyncio.Task):
            validate_job: ValidateJob = task2job[task]
            html_content: str = task.result()
            is_activated = validate_job.callback(html_content, validate_job.proxy_item)
            if is_activated:
                self.event_validate_job_finish.add_count_activated_proxy()
            
            del task2job[task]

            # 触发 validate job 全部完成事件
            if len(task2job) == 0 and self.validate_job_queue.qsize() == 0:
                self.event_validate_job_finish.set()

        while True: # 循环监听队列
            validate_job: ValidateJob = await self.validate_job_queue.get()
            self.event_validate_job_finish.add_count_total_proxy()
            task = asyncio.create_task(self.fetch_content("https://httpbin.org/ip", validate_job.proxy_item))
            task.add_done_callback(_on_completed)
            task2job[task] = validate_job