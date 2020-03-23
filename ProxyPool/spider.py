import asyncio, sys
from asyncio import Event
from typing import List, Callable, Tuple

import aiohttp
from bs4 import BeautifulSoup  

from .models import ProxyItem
from .storage import ProxyPoolStorage


class SpiderMeta(type):
    def __new__(cls, name, bases, attrs):
        attrs["__Crawl_Func__"]: List[Callable] = list()
        for k, v in attrs.items():
            if k.startswith("crawl_"):
                attrs["__Crawl_Func__"].append(v)
        return type.__new__(cls, name, bases, attrs)


class ProxySpider(object, metaclass=SpiderMeta):
    def __init__(self):
        self.session: aiohttp.ClientSession = None
        self.storage = ProxyPoolStorage()
        self.max_retry_count = 8 # 最多重复尝试获取次数


    # 调用全部爬取函数 获取代理列表
    async def get_proxy_list(self) -> List[ProxyItem]:
        proxy_list: List[ProxyItem] = list()

        async with aiohttp.ClientSession() as self.session:
            for func in getattr(self, "__Crawl_Func__"):
                proxy_list += await func(self)
        
        return proxy_list
    
    # 通过代理获取 url 内容
    async def fetch_through_proxy(self, url: str, current_retry_count: int) -> Tuple[str, str, str]:
        status_code, content = None, ""

        # 构造代理连接
        proxy_item = self.storage.get()
        proxy_url = "http://{ip}:{port}".format(**proxy_item.dict()) if proxy_item else None
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36"}
        print("第 {} 次尝试获取 {} 使用代理 ".format(current_retry_count, url), proxy_item)
        try:
            # 请求资源
            async with self.session.get(url, proxy=proxy_url, headers=headers, timeout=15) as resp:
                status_code, content = resp.status, await resp.text()
        except Exception as e:
            pass

        # 判断是否获取成功
        if status_code != 200:
            content = ""
        # 返回资源
        return content, url, current_retry_count

    # 解析 xicidaili 的结构 提取出代理列表
    def extract_xicidaili(self, content: str) -> List[ProxyItem]:
        proxy_list = list()
        soup = BeautifulSoup(content, "lxml")
        for tr_node in soup.select("#ip_list tr")[1:]:
            td_node_list = tr_node.select("td")
            proxy = ProxyItem(ip=td_node_list[1].string, port=td_node_list[2].string, https=(td_node_list[5].string == "HTTPS"))
            proxy_list.append(proxy)
        return proxy_list

    # 获取 xicidaili 的免费代理
    async def _crawl_xicidaili(self) -> List[ProxyItem]:
        proxy_list: List[ProxyItem] = list()
        url_template = "https://www.xicidaili.com/nn/{}"

        # event 等待 task 的回调函数 将 url_todo_set 清空 表示全部任务完成
        event_url_fetch_finish = Event()
        url_todo_set = set()

        # task 的回调函数
        def _on_completed(task: asyncio.Task):
            content, url, current_retry_count = task.result()
            is_to_remove_from_todo = False
            if content == "":
                # url 获取失败重新尝试
                if current_retry_count >= self.max_retry_count:
                    # 超过最大重试次数 将 url 从 todo 中移除
                    is_to_remove_from_todo = True
                else:
                    # 重试
                    task = asyncio.create_task(self.fetch_through_proxy(url, current_retry_count + 1))
                    task.add_done_callback(_on_completed)
            else:
                # url 获取成功 解析 内容 并将 url 从 url_todo_set 中移除
                proxy_list.extend(self.extract_xicidaili(content))
                is_to_remove_from_todo = True
                print("经过 {} 次尝试 成功获取 {}".format(current_retry_count, url))
            
            if is_to_remove_from_todo:
                url_todo_set.remove(url)
                if len(url_todo_set) == 0:
                    # url 全部处理完成 触发事件
                    event_url_fetch_finish.set()

        # 构造并行 task 和 url_todo_set
        for index in range(50):
            url = url_template.format(index + 1)
            task = asyncio.create_task(self.fetch_through_proxy(url, 0))
            task.add_done_callback(_on_completed)
            url_todo_set.add(url)

        # 等待 url 全部处理完成
        await event_url_fetch_finish.wait()

        return proxy_list

    # 获取 free proxy list 的代理
    async def crawl_free_proxy_list(self) -> List[ProxyItem]:
        proxy_list: List[ProxyItem] = list()
        url = "https://free-proxy-list.net/"
        retry_count, content = 0, ""

        while retry_count <= self.max_retry_count:
            content, _, _ = await self.fetch_through_proxy(url, retry_count)
            if content != "": break
            retry_count += 1
        
        if content != "":
            soup = BeautifulSoup(content, "lxml")
            for tr_node in soup.select("#proxylisttable tbody>tr"):
                td_node_list = tr_node.select("td")
                proxy_item = ProxyItem(ip=td_node_list[0].string, port=td_node_list[1].string, https=td_node_list[6].string == "yes")
                proxy_list.append(proxy_item)
        
        return proxy_list


