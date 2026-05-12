import redis, json, time, threading, random

r = redis.Redis(host='localhost', port=6379, password='123456', decode_responses=True)

# ==================== 生产者：用户提交推理任务 ====================
def submit_inference_task(user_id: str, prompt: str):
    """
    用户提交任务 -> 立刻进队列 -> 返回确认信息
    这是同步的，但极快（微秒级）
    """
    task = {
        'task_id': f'task_{int(time.time()*1000)}',
        'user_id': user_id,
        'prompt': prompt,
        'status': 'pending',
        'created_at': time.time()
    }
    
    # 把任务 JSON 序列化后，塞进队列尾
    r.lpush('task:queue', json.dumps(task))
    print(f"✅ 任务 {task['task_id']} 已提交：{prompt}")
    return task['task_id']

# ==================== 消费者：后台 Worker 处理任务 ====================
def inference_worker():
    """
    死循环，不断从队列头取任务处理
    """
    print("🤖 Worker 启动，等待任务...")
    while True:
        # brpop 是阻塞式取出：队列空就等着，有任务立刻取出
        result = r.brpop('task:queue', timeout=0)  # timeout=0 表示永远等
        if result is None:
            continue
        
        queue_name, task_json = result
        task = json.loads(task_json)
        
        # 模拟推理
        task['status'] = 'processing'
        print(f"⚙️  正在处理 {task['task_id']}: {task['prompt']}")
        time.sleep(random.uniform(0.5, 2))  # 模拟耗时推理
        
        # 推理完成，存结果
        task['status'] = 'done'
        task['result'] = f"这是“{task['prompt']}”的推理结果"
        r.setex(f'result:{task["task_id"]}', 3600, json.dumps(task))
        print(f"🎉 任务 {task['task_id']} 完成！")

# ==================== 启动 ====================
# 在实际项目中，生产者和消费者是分开部署的。
# 这里为了演示，我们起一个线程跑 Worker。
worker_thread = threading.Thread(target=inference_worker, daemon=True)
worker_thread.start()

# 模拟用户提交 3 个任务
submit_inference_task('user_1', '介绍一下Redis')
submit_inference_task('user_2', 'Python如何连接大模型')
submit_inference_task('user_3', '解释一下分布式锁')

# 主线程等一会儿，让 Worker 执行完
time.sleep(5)

# 查看结果
for task_id in ['task_1', 'task_2', 'task_3']:
    result = r.get(f'result:{task_id}')
    if result:
        print(f"📖 最终结果: {json.loads(result)}")

import redis, json, time, random, threading

r = redis.Redis(host='localhost', port=6379, password='123456', decode_responses=True)

STREAM_KEY = 'task:stream'
GROUP_NAME = 'inference_workers'
CONSUMER_NAME = f'worker_{random.randint(1,1000)}'

# ==================== 初始化消费者组（只需要执行一次） ====================
try:
    r.xgroup_create(STREAM_KEY, GROUP_NAME, id='0', mkstream=True)
    print(f"✅ 创建消费者组: {GROUP_NAME}")
except redis.ResponseError as e:
    if 'BUSYGROUP' in str(e):
        print(f"ℹ️ 消费者组 {GROUP_NAME} 已存在")
    else:
        raise


# ==================== 生产者：提交任务到 Stream ====================
def submit_task_stream(user_id: str, prompt: str):
    task = {
        'user_id': user_id,
        'prompt': prompt,
        'status': 'pending',
        'created_at': str(time.time())
    }
    # XADD 把任务消息追加到 Stream 里，返回消息 ID
    msg_id = r.xadd(STREAM_KEY, task)
    print(f"✅ 任务已提交 (ID: {msg_id}): {prompt}")
    return msg_id


# ==================== 消费者：Stream 模式 Worker ====================
def inference_worker_stream():
    print(f"🤖 Worker [{CONSUMER_NAME}] 启动...")
    while True:
        try:
            # 用消费者组模式读取消息
            # ">" 表示"只取新消息，不取已分配给别人的"
            # count=1 表示一次取一条
            # block=5000 表示阻塞等待，最多等 5000 毫秒
            msgs = r.xreadgroup(
                GROUP_NAME, CONSUMER_NAME,
                {STREAM_KEY: '>'},  # 只读新消息
                count=1, block=5000
            )
            
            if not msgs:
                continue
            
            for stream_name, messages in msgs:
                for msg_id, msg_data in messages:
                    print(f"⚙️  [{CONSUMER_NAME}] 处理任务 {msg_id}: {msg_data['prompt']}")
                    
                    # 模拟推理
                    time.sleep(random.uniform(0.5, 2))
                    
                    # 存结果
                    result_key = f'result:{msg_id}'
                    msg_data['status'] = 'done'
                    msg_data['result'] = f"推理完成: {msg_data['prompt']}"
                    r.setex(result_key, 3600, json.dumps(msg_data))
                    
                    # *** 关键步骤：消息确认！***
                    r.xack(STREAM_KEY, GROUP_NAME, msg_id)
                    print(f"🎉 [{CONSUMER_NAME}] 任务 {msg_id} 完成并确认")
                    
        except Exception as e:
            print(f"❌ Worker 出错: {e}")
            time.sleep(1)
