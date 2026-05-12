import redis
import time
r=redis.Redis(
    host='localhost',
    port=6379,
    password='123456',
    decode_responses=True
)
def deduct_quota(user_id:int) ->bool:
    max_retries=3
    for attempt in range(max_retries):
        try:
            with r.pipeline() as pipe:
                '''有 watch → 管道变成即时执行，get 能拿到值
没 watch → 管道是批量缓存，get 只返回管道对象'''
                pipe.watch('daily_quota')
                quota=int(pipe.get('daily_quota'))
                if quota<=0:
                    return False
                pipe.multi()
                pipe.decr('daily_quota')
                pipe.sadd('quota_users',user_id)
                pipe.execute()
                print(f"用户{user_id}抢到名额，剩余配额{quota-1}")
                return True
        except redis.WatchError:
            #并发抢票冲突时，暂停 0.1 秒再重试，防止 CPU 空转、Redis 被打崩，让系统更稳定
            print(f"用户 {user_id} 冲突，第 {attempt + 1} 次重试...")
            time.sleep(0.1)

            continue
    print(f"用户{user_id}抢票失败，重试次数已达上限")
    return False
r.set('daily_quota',10)
#清空上一轮的中奖用户列表，保证本次抢票数据赶紧不混乱
r.delete('quota_users')
#模拟20个人同时抢票
import threading
results=[]
def user_grab(user_id):
    res=deduct_quota(user_id)
    results.append((user_id,res))
threads=[]
for i in range(1,21):
    #threading.Thread 的 args 参数 必须传 元组（tuple）！
    t=threading.Thread(target=user_grab,args=(f"user_{i}",))
    threads.append(t)
    t.start()
    '''放错位置 = 排队抢票
放对位置 = 并发抢票'''
for t in threads:
    t.join()
    
success = [u for u, ok in results if ok]
print("\n" + "="*50)
print(f"总用户：20")
print(f"成功抢到：{len(success)} 人")
print(f"剩余配额：{r.get('daily_quota')}")
print(f"抢到用户：{success}")


