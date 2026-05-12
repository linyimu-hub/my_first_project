import redis
import json
import time
import threading
import random

r = redis.Redis(host='localhost', port=6379, password='123456', decode_responses=True)

# ==================== 发布者：推理 Worker ====================
def inference_worker_with_progress(task_id: str, prompt: str):
    """
    执行推理，同时向指定频道实时推送进度
    """
    channel = f'task:progress:{task_id}'
    
    # 模拟推理的各个阶段
    stages = [
        (0, "开始预处理输入"),
        (20, "正在分词和编码"),
        (40, "模型正在推理中"),
        (70, "解码输出结果"),
        (90, "后处理和格式化"),
    ]
    
    for percent, description in stages:
        # 实际生产中，这里做耗时的推理步骤...
        time.sleep(random.uniform(0.5, 1.5))
        
        # 构造进度消息
        progress_msg = json.dumps({
            'task_id': task_id,
            'percent': percent,
            'description': description,
            'timestamp': time.time()
        })
        
        # 发布到频道
        r.publish(channel, progress_msg)
        print(f"📡 已推送进度: {percent}% - {description}")
    
    # 最终完成
    time.sleep(1)  # 最后一步生成
    final_msg = json.dumps({
        'task_id': task_id,
        'percent': 100,
        'description': '推理完成',
        'result': f'这是关于"{prompt}"的完整回答，共1500字...'
    })
    r.publish(channel, final_msg)
    print(f"🎉 任务 {task_id} 完成！")


# ==================== 订阅者：模拟前端接收进度 ====================
def progress_listener(task_id: str):
    """
    订阅推理进度，模拟前端实时更新
    """
    channel = f'task:progress:{task_id}'
    
    # 创建一个 PubSub 对象，并订阅频道
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    
    print(f"👂 开始监听任务 {task_id} 的进度...")
    
    # 循环监听消息
    for message in pubsub.listen():
        # pubsub.listen() 返回的格式：
        # {'type': 'subscribe', ...}  # 订阅确认
        # {'type': 'message', 'channel': '...', 'data': '...'}  # 真正的消息
        
        if message['type'] == 'message':
            progress = json.loads(message['data'])
            print(f"📊 进度更新: {progress['percent']}% - {progress['description']}")
            
            if progress['percent'] == 100:
                print(f"✅ 最终结果: {progress.get('result', '')}")
                break  # 任务完成，退出监听
    
    pubsub.unsubscribe(channel)
    print(f"🔇 已停止监听 {channel}")


# ==================== 启动演示 ====================
if __name__ == '__main__':
    TASK_ID = 'demo_task_001'
    
    # 启动订阅者线程（模拟前端 WebSocket）
    listener_thread = threading.Thread(target=progress_listener, args=(TASK_ID,), daemon=True)
    listener_thread.start()
    
    # 等一下订阅者准备好
    time.sleep(0.5)
    
    # 启动推理 Worker（主线程）
    inference_worker_with_progress(TASK_ID, prompt="什么是Redis?")
    
    # 等待监听线程结束
    listener_thread.join()