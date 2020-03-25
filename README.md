# ProxyPool

1. 克隆仓库
2. 安装 Docker 以及 Docker Compose
3. 终端输入 `docker-compose up -d`
4. 浏览器地址栏中输入 localhost:5050/proxy ，即可获得 代理的 Json 格式

# 抓取的网站

1. [FreeProxyList](https://free-proxy-list.net/)
2. [Xici](https://www.xicidaili.com/)

# 配置

配置文件在目录 `/production/config/production.cfg` 内部

# Redis

Redis 持久化数据保存在 `/production/data` 内部

# 添加新抓取网站

文件 `./ProxyPool/jobfactory.py` 中，向类 `CrawlJobFactory` 添加 以 `produce_` 开头的方法，返回 `CrawlJob` 实例的列表。每个 `CrawlJob` 中的属性如下：
- job_type：任务类型，对于 CrawlJob 实例，值为 JobType.CRAWL
- target_url：目标抓取的 URL
- callback：network 模块抓取 URL 的内容，以返回的内容调用此回调函数。函数格式为 `[[str], int]`，返回添加到数据库中的代理数量
- retry_count：此 target_url 被重试的次数，构建实例直接使用默认值即可

抓取 FreeProxyList 的例子：

```
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
```