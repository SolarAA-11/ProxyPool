import asyncio, logging, configparser, os

from ProxyPool import ProxyPool ,create_proxypool
from ProxyPool.models import ProxyItem


async def main():
    # 读取配置
    config = configparser.ConfigParser()
    config.read(["./production/config/.cfg", "./production/config/production.cfg"], encoding="UTF-8")

    # 日志配置
    numeric_level = getattr(logging, config.get("ProxyPool", "log_level").upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(
        filename="./production/log/proxypool.log" if os.getenv("PRODUCTION_ENV") else "proxypool.log",
        filemode="w",
        level=numeric_level,
        format="%(levelname)s - %(asctime)s : %(filename)s %(message)s",
    )

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
    asyncio.run(main())