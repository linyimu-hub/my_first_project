import redis

r = redis.Redis(host='localhost', port=6379, password='123456', decode_responses=True)

def batch_get_user_data(user_ids: list):
    """
    批量获取多个用户的资料、信用分、未读消息
    参数: user_ids = ['100', '101', '102']
    返回: dict，格式为 {user_id: {'profile': {...}, 'score': '...', 'unread': '...'}}
    """
    # ===== 第一步：创建 Pipeline =====
    pipe = r.pipeline()
    
    # ===== 第二步：把每个用户的三条命令排队 =====
    for uid in user_ids:
        pipe.hgetall(f'user:{uid}:profile')   # Hash 获取所有字段
        pipe.get(f'user:{uid}:score')          # String 获取信用分
        pipe.get(f'user:{uid}:unread')         # String 获取未读消息数
    
    # ===== 第三步：一次性执行 =====
    results = pipe.execute()
    
    # ===== 第四步：解析结果列表 =====
    # results 的顺序和上面排队的顺序完全一致
    # 3 条命令一组，对应一个用户
    user_data = {}
    for i, uid in enumerate(user_ids):
        offset = i * 3  # 每个用户占 3 个位置
        profile = results[offset]       # hgetall 返回的是字典
        score = results[offset + 1]     # get 返回的是字符串
        unread = results[offset + 2]    # get 返回的是字符串
        
        user_data[uid] = {
            'profile': profile if profile else {},
            'score': score if score else '0',
            'unread': unread if unread else '0'
        }
    
    return user_data


# ==================== 测试：写入模拟数据 ====================
# 用户 100
r.hset('user:100:profile', mapping={'name': '张三', 'plan': 'VIP', 'industry': 'AI'})
r.set('user:100:score', 850)
r.set('user:100:unread', 3)

# 用户 101
r.hset('user:101:profile', mapping={'name': '李四', 'plan': 'Free'})
r.set('user:101:score', 620)
r.set('user:101:unread', 0)

# 用户 102（这个用户没任何数据，模拟新用户）
# 不写入任何数据

# ==================== 调用函数 ====================
result = batch_get_user_data(['100', '101', '102'])
for uid, data in result.items():
    print(f"用户 {uid}:")
    print(f"  资料: {data['profile']}")
    print(f"  信用分: {data['score']}")
    print(f"  未读消息: {data['unread']}")
    print()