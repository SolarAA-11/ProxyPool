from typing import List, Callable
import json, logging, configparser

from bs4 import BeautifulSoup

from .storage import ProxyPoolStorage
from .models import JobBase, CrawlJob, ValidateJob, ProxyItem

# JobFactory MetaClass
class JobFactoryMetaClass(type):
    def __new__(cls, name, classes, attrs):
        attrs["__Produce_Func__"] = list()
        for k, v in attrs.items():
            if k.startswith("produce_"):
                attrs["__Produce_Func__"].append(v)
        return type.__new__(cls, name, classes, attrs)

# JobFactory 基类
class JobFactory(object, metaclass=JobFactoryMetaClass):
    def get_jobs(self) -> List[JobBase]:
        job_list: List[JobBase] = list()
        for func in getattr(self, "__Produce_Func__"):
            job_list.extend(func(self))
        return job_list

# CrawlJob 工厂
class CrawlJobFactory(JobFactory):
    
    def __init__(
        self,
        *,
        crawl_page_count_for_xici = 10, # 抓取的 XICIDAILI 的数量
    ):
        self.storage = ProxyPoolStorage()
        self.page_count_for_xici = crawl_page_count_for_xici
    
    # 生产用户抓取 xicidaili 的 job
    def produce_job_for_xicidaili(self) -> List[CrawlJob]:
        # job callback
        def crawl_xici_job_callback(content: str):
            count_of_added_proxy = 0
            soup = BeautifulSoup(content, "lxml")
            for tr_node in soup.select("#ip_list tr")[1:]:
                td_node_list = tr_node.select("td")
                proxy_item = ProxyItem(
                    ip=td_node_list[1].string,
                    port=td_node_list[2].string,
                    https=td_node_list[5].string == "HTTPS"
                )
                is_added = self.storage.add(proxy_item)
                count_of_added_proxy += int(is_added)
            return count_of_added_proxy
        
        crawl_job_list: List[CrawlJob] = list()
        url_template = "https://www.xicidaili.com/nn/{}"
        for index in range(self.page_count_for_xici):
            target_url = url_template.format(index + 1)
            crawl_job_list.append(CrawlJob(target_url=target_url, callback=crawl_xici_job_callback))
        return crawl_job_list
    
    # 为 free proxy list 生成抓取任务
    # https://free-proxy-list.net/
    def produce_job_for_FreeProxyList(self) -> List[CrawlJob]:
        # callback
        def crawl_FreeProxyList_callback(content: str):
            count_of_added_proxy = 0
            soup = BeautifulSoup(content, "lxml")
            for tr_node in soup.select("#proxylisttable tbody>tr"):
                td_node_list = tr_node.select("td")
                proxy_item = ProxyItem(
                    ip=td_node_list[0].string,
                    port=td_node_list[1].string,
                    https=td_node_list[6].string == "yes"
                )
                is_added = self.storage.add(proxy_item)
                count_of_added_proxy += int(is_added)
            return count_of_added_proxy
        target_url = "https://free-proxy-list.net/"
        return [CrawlJob(target_url=target_url, callback=crawl_FreeProxyList_callback),]



# ValidateJob 工厂 
class ValidateJobFactory(JobFactory):

    def __init__(self):
        self.storage = ProxyPoolStorage()

    # 生产 ValidateJob
    def produce_validate_jobs(self) -> List[ValidateJob]:
        # job callback 
        def validate_job_callback(html_content: str, proxy_item: ProxyItem) -> bool:
            # 验证响应是否有效
            is_valide = False
            try:
                if html_content != "":
                    json_dict = json.loads(html_content)
                    is_valide = json_dict.get("origin", "") == proxy_item.ip
            except ValueError:
                pass

            # 通知 Storage
            if is_valide: self.storage.activate(proxy_item)
            else: self.storage.deactivate(proxy_item)
            return is_valide
        
        validate_jobs: List[ValidateJob] = list()
        for proxy in self.storage.get_all():
            validate_jobs.append(ValidateJob(proxy_item=proxy, callback=validate_job_callback))
        
        # 没有任何代理存在 造成死锁 返回一个 FakeProxyValidateJob
        if len(validate_jobs) == 0:
            fake_validate_job = ValidateJob(
                proxy_item=ProxyItem(
                    ip="0.0.0.0",
                    port="0",
                    https=False
                ), 
                callback=validate_job_callback
            )
            return [fake_validate_job, ]
        else: return validate_jobs
