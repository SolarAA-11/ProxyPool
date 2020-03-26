from enum import Enum
from typing import Callable, NoReturn
from pydantic import BaseModel, Field

class ProxyItem(BaseModel):
    ip: str
    port: int
    https: bool

# 任务类型
class JobType(Enum):
    CRAWL = 1       # 抓取代理
    VALIDATE = 2    # 验证代理

# 任务的基类
class JobBase(BaseModel):
    job_type: JobType

# 描述代理抓取任务 CrawlJobFactor 产生任务 将其
class CrawlJob(JobBase):
    job_type: JobType = Field(JobType.CRAWL)
    target_url: str # 抓取的目标页面路径
    # 回调函数 将 html 解析后 将代理添加到Storage中 
    # 参数 str 为抓取的页面 html 内容 返回值为插入到 storage 中代理的数量
    callback: Callable[[str],int] 
    retry_count: int = Field(0) # 当前重试次数

# 描述验证任务
class ValidateJob(JobBase):
    job_type: JobType = Field( JobType.VALIDATE )
    proxy_item: ProxyItem   # 被验证的代理
    # 回调函数 验证响应数据的正确与否 判断是否激活数据库中的代理
    # 参数 str 为验证的响应返回值 ProxyItem 为当前验证的代理对象
    # 返回值为是否激活
    callback: Callable[ [ str, ProxyItem ], bool ] 