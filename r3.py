import redis
import time
from redis import WatchError

# 连接 Redis
r = redis.Redis(
    host='localhost',
    port=6379,
    password='123456',
    decode_responses=True
)

def deduct_quota_safe(user_id: str) -> bool:
    max_retries = 3

    for attempt in range(max_retries):
        try:
            # ✅ 推荐写法：with 自动管理管道
            with r.pipeline() as pipe:
                pipe.watch('daily_quota')

                # ✅ 直接读取，不通过管道 execute，避免空列表！
                quota = int(pipe.get('daily_quota') or 0)

                if quota <= 0:
                    return False

                # 开启事务
                pipe.multi()
                pipe.decr('daily_quota')
                pipe.sadd('quota_users', user_id)
                pipe.execute()

                print(f"用户 {user_id} 抢到名额！剩余配额：{quota - 1}")
                return True

        except WatchError:
            print(f"用户 {user_id} 冲突，第 {attempt + 1} 次重试...")
            time.sleep(0.1)
            continue

    print(f"用户 {user_id} 重试失败")
    return False


# ==================== 初始化 ====================
r.set('daily_quota', 10)
r.delete('quota_users')

# ==================== 20 个用户并发抢 ====================
import threading
results = []

def user_grab(user_id):
    res = deduct_quota_safe(user_id)
    results.append((user_id, res))

threads = []
for i in range(1, 21):
    t = threading.Thread(target=user_grab, args=(f"user_{i}",))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

# ==================== 结果 ====================
success = [u for u, ok in results if ok]
print("\n" + "="*50)
print(f"总用户：20")
print(f"成功抢到：{len(success)} 人")
print(f"剩余配额：{r.get('daily_quota')}")
print(f"抢到用户：{success}")
