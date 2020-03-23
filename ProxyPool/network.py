import asyncio
from asyncio import Semaphore, Event, Queue

import aiohttp

from .models import ProxyItem, JobBase, CrawlJob, ValidateJob, JobType
from .storage import ProxyPoolStorage

# 消费 CrawlJobFactory 以及 ValidateJobFactory 产生的任务
# 管理网络请求
class NetManager:

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
        self.event_crawl_job_finish = Event()
        self.event_validate_job_finish = Event()

    # 启动 consumer 
    def run(self):
        asyncio.gather(self.crawl_job_consumer(), self.validate_job_consumer())

    # 向队列中添加任务 不同任务添加到不同队列中
    def append_job(self, job: JobBase) -> None:
        if job.job_type == JobType.CRAWL: self.crawl_job_queue.put_nowait(job)
        else: self.validate_job_queue.put_nowait(job)

    # 向互联网中请求 url 数据
    async def fetch_content(self, url: str, proxy_item: ProxyItem) -> str:
        status_code, content = None, None
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36"}
            proxy = "http://{ip}:{port}".format(**proxy_item.dict()) if proxy_item else None
            async with self.semaphore_max_concurrent_request:
                async with self.session.get(
                    url, 
                    headers=headers,
                    proxy=proxy,
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
            html_content = task.result()

            if html_content != "": # 正确获取 url 内容 调用回调
                crawl_job.callback(html_content)
            elif crawl_job.retry_count < self.max_retry_count: # 请求失败 且重试次数小于指定值 重新入队 等待下次调度
                crawl_job.retry_count += 1
                self.append_job(crawl_job)
            del task2job[task]

            # 触发 crawl job 全部完成事件
            if len(task2job) == 0 and self.crawl_job_queue.qsize() == 0:
                self.event_crawl_job_finish.set()
                print("Finish crawl_job")
        
        while True: # 循环监听队列
            crawl_job: CrawlJob = await self.crawl_job_queue.get()
            task = asyncio.create_task(self.fetch_content(crawl_job.target_url, self.storage.get()))
            task.add_done_callback(_on_completed)
            task2job[task] = crawl_job

    # 消费 ValidateJob
    async def validate_job_consumer(self):
        task2job: Dict[asyncio.Task, ValidateJob] = dict()
        # task callback
        def _on_completed(task: asyncio.Task):
            validate_job: ValidateJob = task2job[task]
            html_content = task.result()
            validate_job.callback(html_content, validate_job.proxy_item)
            del task2job[task]

            # 触发 crawl job 全部完成事件
            if len(task2job) == 0 and self.validate_job_queue.qsize() == 0:
                self.event_validate_job_finish.set()
                print("Finish validate job")

        while True: # 循环监听队列
            validate_job: ValidateJob = await self.validate_job_queue.get()
            task = asyncio.create_task(self.fetch_content("https://httpbin.org/ip", validate_job.proxy_item))
            task.add_done_callback(_on_completed)
            task2job[task] = validate_job