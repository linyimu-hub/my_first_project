import redis
import json
import random

r = redis.Redis(host='localhost', port=6379, password='123456', decode_responses=True)

# ==================== 模拟数据库 ====================
# 数据库里只有这 5 个用户，其他 50 个不存在
DB = {
    'user:1':  {'name': '张三', 'plan': 'VIP'},
    'user:2':  {'name': '李四', 'plan': 'Free'},
    'user:3':  {'name': '王五', 'plan': 'VIP'},
    'user:4':  {'name': '赵六', 'plan': 'Enterprise'},
    'user:5':  {'name': '钱七', 'plan': 'Free'},
}

db_query_count = 0  # 计数器：记录数据库被查了多少次

def query_db(user_key: str):
    """模拟数据库查询"""
    global db_query_count
    db_query_count += 1
    print(f"  ⚠️  【查数据库了！】查询 {user_key}（第 {db_query_count} 次查库）")
    return DB.get(user_key)  # 不存在就返回 None


# ==================== 缓存查询函数（带穿透保护） ====================
def cache_query_with_protection(user_key: str):
    """带空值缓存的查询，防止穿透"""
    # 第一步：查缓存
    cached = r.get(user_key)
    if cached is not None:
        if cached == '__NULL__':
            print(f"  ✅ 命中空值缓存：{user_key} -> 返回 None（不查库）")
            return None
        print(f"  ✅ 命中正常缓存：{user_key} -> {cached}")
        return json.loads(cached)
    
    # 第二步：查数据库
    data = query_db(user_key)
    
    # 第三步：写回缓存
    if data is None:
        # 数据库也没有，缓存空值，60秒过期
        r.setex(user_key, 60, '__NULL__')
        print(f"  📝 缓存空值：{user_key} (过期60秒)")
        return None
    else:
        # 数据库有，正常缓存
        r.setex(user_key, 3600, json.dumps(data))
        print(f"  📝 缓存正常数据：{user_key}")
        return data


# ==================== 测试开始 ====================
print("=" * 60)
print("第一轮查询（50个不存在用户 + 5个存在用户）")
print("=" * 60)

# 构造 50 个不存在的 key + 5 个存在的 key
all_keys = [f'user:{i}' for i in range(6, 56)]  # user:6 ~ user:55 不存在
all_keys += [f'user:{i}' for i in range(1, 6)]   # user:1 ~ user:5 存在
random.shuffle(all_keys)  # 打乱顺序

db_query_count = 0  # 重置计数器

for key in all_keys:
    cache_query_with_protection(key)

print(f"\n第一轮结束，数据库被查询了 {db_query_count} 次")
print(f"（理论上应该 = 55 次，因为缓存里一开始什么都没有）")

# ==================== 第二轮查询（同样的 key） ====================
print("\n" + "=" * 60)
print("第二轮查询（同样的 55 个 key）")
print("=" * 60)

db_query_count = 0  # 重置计数器

for key in all_keys:
    cache_query_with_protection(key)

print(f"\n第二轮结束，数据库被查询了 {db_query_count} 次")
print(f"（理论上应该 = 0 次！因为全部命中缓存，包括空值缓存）")