import asyncio, logging, configparser

from ProxyPool import ProxyPool ,create_proxypool
from ProxyPool.models import ProxyItem


async def main():
    # 读取配置
    config = configparser.ConfigParser()
    # 默认配置文件
    config.read(".cfg", encoding="UTF-8")
    # 获取自定义配置文件
    config.read("./production/config/production.cfg", encoding="UTF-8")

    # 启动代理池
    proxy_pool = create_proxypool(
        crawl_job_interval_hour=config.getint("ProxyPool", "crawl_job_interval_hour"),
        validate_job_interval_minute=config.getint("ProxyPool", "validate_job_interval_minute"),
        timeout=config.getint("ProxyPool", "timeout"),
        max_retry_count=config.getint("ProxyPool", "max_retry_count"),
        max_concurrent_request=config.getint("ProxyPool", "max_concurrent_request"),
        crawl_page_count_for_xici=config.getint("CrawlJobFactory", "xicidaili_page_count")
    )
    
    # 等待两个生产协程对应的 Task
    await proxy_pool.task_for_produce_crawl_validate_job

if __name__ == "__main__":
    # asyncio.run(main())
    uvicorn.run(
        app, 
        debug=True, 
        # logging 
        use_colors=False,
        log_level="debug",
    )