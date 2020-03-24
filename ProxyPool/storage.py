import json, random
from typing import List

import redis

from .models import ProxyItem

redis_engine = redis.Redis(host="127.0.0.1", port=6379)
# redis_engine = redis.Redis(host="redis", port=6379)
# REDIS_PROXY_KEY = "ProxyPool:ProxyItem:SSet" # 国内
# zrange ProxyPool:ProxyItem:SSet 0 -1 withscores
REDIS_PROXY_KEY = "ProxyPool:ProxyItem:SSet:Foreign" # 国外
# zrange ProxyPool:ProxyItem:SSet:Foreign 0 -1 withscores
class ProxyPoolStorage:
    '''
    操作 Redis 进行 Proxy 的存储和排序
    '''
    # 获取前三十代理的随机一个
    def get(self) -> ProxyItem:
        proxy_list = self.get_top_30()
        if len(proxy_list) == 0: return None
        else: return proxy_list[random.randint(0, len(proxy_list) - 1)]

    # 获取前三十全部
    def get_top_30(self) -> List[ProxyItem]:
        json_repr_list = redis_engine.zrevrange(REDIS_PROXY_KEY, 0, 30)
        proxy_list = [ ProxyItem(**json.loads(json_repr)) for json_repr in json_repr_list ]
        return proxy_list

    # 获取全部
    def get_all(self) -> List[ProxyItem]:
        json_repr_list = redis_engine.zrange(REDIS_PROXY_KEY, 0, -1)
        proxy_list = [ ProxyItem(**json.loads(json_repr)) for json_repr in json_repr_list ]
        return proxy_list

    # 添加
    def add(self, proxy: ProxyItem) -> bool:
        json_repr = json.dumps(proxy.dict())
        if redis_engine.zrank(REDIS_PROXY_KEY, json_repr) is None:
            # Redis 中不存在需要添加的代理
            redis_engine.zadd(REDIS_PROXY_KEY, {json_repr: 20})
            return True
        return False

    # 经过验证 proxy 可用
    def activate(self, proxy: ProxyItem):
        json_repr = json.dumps(proxy.dict())
        redis_engine.zadd(REDIS_PROXY_KEY, {json_repr: 100})

    # 经过验证 proxy 不可用
    def deactivate(self, proxy: ProxyItem):
        json_repr = json.dumps(proxy.dict())
        redis_engine.zincrby(REDIS_PROXY_KEY, -1, json_repr)

        score = redis_engine.zscore(REDIS_PROXY_KEY, json_repr)
        if score <= 0:
            redis_engine.zrem(REDIS_PROXY_KEY, json_repr)