import redis
import re
from uuid import UUID
import json
r=redis.Redis(
    host='localhost',
    port=6379,
    password='123456',
    decode_responses=True
)
def is_valid_uuid(conv_id:str)->bool:
    try: 
        UUID(conv_id)
        return True
    except ValueError:
        return False
#(1)缓存空值
def get_conversation(conv_id:str)->dict|None:
     # ✅ 新增：第一道防线，参数校验
    if not is_valid_uuid(conv_id):
        return None  # 非法参数直接返回，不碰缓存和数据库
    key=f'conv:{conv_id}'
    cached=r.get(key)
    if cached is not None:
        if cached=='__NULL__':
            return None
        return json.loads(cached)
    #模拟数据库查询
    conv=db.query_conversation(conv_id)
    if conv is None:
        r.setex(key,'__NULL__',3600)
    r.setex(key,json.dumps(conv),3600)
    return conv
from pybloom_live import BloomFilter
bloom=BloomFilter(capacity=1000000,error_rate=0.001)
for conv_id in all_conv_ids:
    bloom.add(conv_id)
def get_conversation_bloom(conv_id:str):
    if conv_id not in bloom:
        return None
    key=f'conv:{conv_id}'
    cached=r.get(key)
    if cached is not None:
        if cached=='__NULL__':
            return None
        return json.loads(cached)
    #模拟数据库查询
    conv=db.query_conversation(conv_id)
    if conv is None:
        r.setex(key,'__NULL__',3600)
    r.setex(key,json.dumps(conv),3600)
    return conv
    

import threading
def get_hot_data(key:str)->dict:
    cached=r.hgetall(key)
    if cached and time.time()< float(cached['expired_at']):
        return json.loads(cached['data'])
    lock_key=f'lock:{key}'
    lock_acquired=r.set(lock_key,'1',nx=True,ex=10)
    if lock_acquired:
        try:
            data=db.query_hot_data(key)
            r.hset(key,mapping={
                'data':json.dumps(data),
                'exppired_at':time.time()+3600
            })
            return data
        finally:
            r.delete(lock_key)#释放锁
    else:
        time.sleep(0.05)
        return get_hot_data(key)
#防雪崩
import random
def cached_with_random_ttl(key:str,data:dict,base_ttl:int=3600):
    random_offset=random.randint(0,600)
    actual_ttl=base_ttl+random_offset
    r.setex(key,json.dumps(data),actual_ttl)
    print(f"缓存 {key}，过期时间: {actual_ttl} 秒 (基础{base_ttl} + 随机{random_offset})")
def get_data_with_fallback(key: str) -> dict:
    try:
        return r.get(key)
    except redis.RedisError:
        # Redis 挂了，启用兜底方案
        return {"message": "系统繁忙，请稍后再试", "data": get_static_fallback(key)}