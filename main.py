import asyncio

import aiohttp

from ProxyPool.spider import ProxySpider
from ProxyPool.storage import ProxyPoolStorage
from ProxyPool.validator import ProxyPoolValidator

async def main():
    validator = ProxyPoolValidator()
    # validator.run_detach()
    await validator.start()
    # spider = ProxySpider()
    # proxy_list = await spider.get_proxy_list()

    # # print(proxy_list)
    # print("本轮共抓取代理 {} 个".format(len(proxy_list)))
    # storage = ProxyPoolStorage()
    # added_count = 0
    # for proxy in proxy_list:
    #     b = storage.add(proxy)
    #     added_count += int(b)
    # print("一共添加 {} 个代理".format(added_count))

if __name__ == "__main__":
    asyncio.run(main())