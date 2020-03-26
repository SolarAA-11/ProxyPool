import json, random, os
from typing import List

import redis

from .models import ProxyItem


redis_engine = redis.Redis(host="redis" , port=6379) if os.getenv("PROXYPOOL_DEV") else redis.Redis(host="127.0.0.1" , port=6379)
REDIS_PROXY_KEY = "ProxyPool:ProxyItem:SSet" # 国内
# zrange ProxyPool:ProxyItem:SSet 0 -1 withscores
# REDIS_PROXY_KEY = "ProxyPool:ProxyItem:SSet:Foreign" # 国外
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

    # 从指定范围中随机选择
    def get_range_random(self, random_range: int = 30):
        proxy_json_list = redis_engine.zrevrange(REDIS_PROXY_KEY, 0, random_range - 1)
        if len(proxy_json_list) == 0: return None
        else:
            json_repr = proxy_json_list[random.randint(0, len(proxy_json_list) - 1)]
            return ProxyItem(**json.loads(json_repr))

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
        if not self.exist(proxy):
            json_repr = json.dumps(proxy.dict())
            redis_engine.zadd(REDIS_PROXY_KEY, {json_repr: 20})
            return True
        return False

    # 判断代理池中是否存在指定代理
    def exist(self, proxy: ProxyItem) -> bool:
        return redis_engine.zrank(REDIS_PROXY_KEY, proxy.json()) is not None

    # 经过验证 proxy 可用
    def activate(self, proxy: ProxyItem) -> bool:
        if self.exist(proxy):
            json_repr = json.dumps(proxy.dict())
            redis_engine.zadd(REDIS_PROXY_KEY, {json_repr: 100})
            return True
        else: return False

    # 经过验证 proxy 不可用
    def deactivate(self, proxy: ProxyItem):
        if self.exist(proxy):
            json_repr = json.dumps(proxy.dict())
            redis_engine.zincrby(REDIS_PROXY_KEY, -1, json_repr)

            score = redis_engine.zscore(REDIS_PROXY_KEY, json_repr)
            if score <= 0:
                redis_engine.zrem(REDIS_PROXY_KEY, json_repr)
            return True
        else: return False