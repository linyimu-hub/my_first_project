import redis
import threading
import time
r=redis.Redis(
    host='localhost',
    port=6379,
    password='123456',
    decode_responses=True
)
def tranfer(user_id,money):
    target_account='account:common:balance'
    #开启Redis事务
    with r.pipeline() as pipe:
        while True:
            try:
                pipe.watch(target_account)
                current_balance=pipe.get(target_account)
                print(f"用户{user_id}当前余额：{current_balance}")
                pipe.multi()
                pipe.incrby(target_account,money)
                pipe.execute()
                print(f"用户{user_id}成功转入{money}元")
                break
            except redis.WatchError:
                print(f"用户{user_id}转账失败，重试中...")
                time.sleep(0.1)
#模拟多个用户同时转账
r.set('account:common:balance',10000)
if __name__=="__main__":
    t1=threading.Thread(target=tranfer,args=(1,100))
    t2=threading.Thread(target=tranfer,args=(2,200))
    t3=threading.Thread(target=tranfer,args=(3,300))
    t1.start()
    t2.start()
    t3.start()
    t1.join()
    t2.join()
    t3.join()
    final=r.get('account:common:balance')
    print(f"最终公共账户余额：{final}")
