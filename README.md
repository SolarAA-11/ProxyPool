# ProxyPool

1. 克隆仓库
2. 安装 Docker 以及 Docker Compose
3. 终端输入 `docker-compose up -d`
4. 浏览器地址栏中输入 localhost:5050/proxy ，即可获得 代理的 Json 格式

## 抓取的网站

1. [FreeProxyList](https://free-proxy-list.net/)
2. [Xici](https://www.xicidaili.com/)

## 配置

配置文件在目录 `/production/config/production.cfg` 内部

## Redis

Redis 持久化数据保存在 `/production/data` 内部

## 添加新抓取网站

文件 `./ProxyPool/jobfactory.py` 中，向类 `CrawlJobFactory` 添加 以 `produce_` 开头的方法，返回 `CrawlJob` 实例的列表。每个 `CrawlJob` 中的属性如下：

- job_type：任务类型，对于 CrawlJob 实例，值为 JobType.CRAWL
- target_url：目标抓取的 URL
- callback：network 模块抓取 URL 的内容，以返回的内容调用此回调函数。函数格式为 `[[str], int]`，返回添加到数据库中的代理数量
- retry_count：此 target_url 被重试的次数，构建实例直接使用默认值即可

抓取 FreeProxyList 的例子：

``` python
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

## TODO

- [ ] 随机返回的代理，在代理池中的范围。使此项可配置；
- [ ] 添加 API 反馈功能。通过 API 获取代理之后，可以通过 POST 将代理返回给 Web API，告知代理池此代理的使用情况：可用还是不可用。代理次将其激活或降权；
- [ ] 分离 ProxyPool 和 Web API，提高 WebAPI 的并发能力。计划分成不同的 Service，WEB API 复用 Storage 模块；

## WebAPI

与 proxyPool 分离的服务，接收网络 RESTful 请求，完成下列功能：

- 返回随机的高可用性的代理。能够接受参数，指定从排名前多少的范围内随机选取；
- 返回按可用性排名的前一部分代理；
- 接收代理 Json 格式，将此代理激活；
- 接收代理 Json 格式，将此代理降权；
- 返回全部代理；

| api | method | Description | QueryArg | Body |
| :--- | :--- | :--- | :--- | :--- |
| / | GET | 获取前 30 随机代理 | 无 | 无 |
| /random?{range} | GET | 获取指定范围内的随机代理 | range 表示代理的范围 | 无 |
| /all | GET | 返回全部代理 | 无 | 无 |
| /activate | POST | 激活代理 | 无 | ProxyItem |
| /deactivate | POST | 代理降权 | 无 | ProxyItem |

**ProxyItem** JSON 格式：

```javascript
{
    "ip": "99.0.0.23",
    "port": 9999,
    "https": false
}
```
