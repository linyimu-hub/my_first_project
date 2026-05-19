import requests
import base64
from dotenv import load_dotenv
import os
import logging
import time 
from pathlib import Path
#日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s -%(levelname)s -%(message)s'
)
#创建logger对象
logger=logging.getLogger(__name__)
#加载环境变量
load_dotenv()
API_KEY=os.getenv('BAIDU_API_KEY')
SECRET_KEY=os.getenv('BAIDU_SECRET_KEY')
if not API_KEY or not SECRET_KEY:
    raise EnvironmentError("未找到API_KEY或SECRET_KEY，请检查环境变量配置")
#获取访问令牌
def get_access_token() -> str| None:
    """
    用API Key + Secret Key 换取 Access Token。
    百度的认证方式：OAuth 2.0 客户端模式。
    """
    url=f'https://aip.baidubce.com/oauth/2.0/token'
    params={
        'grant_type':'client_credentials',
        'client_id':API_KEY,
        'client_secret':SECRET_KEY
    }
    try:
        logger.info("正在获取访问令牌...")
        response=requests.post(url,params=params,timeout=10)
        response.raise_for_status()
        data=response.json()
        if 'error' in data:
            logger.error(f"获取访问令牌失败: {data['error_description']}")
            return None
        token=data['access_token']
        # 有效期（秒），通常是2592000秒=30天
        expires_in=data['expires_in']
        logger.info(f"访问令牌获取成功，有效期: {expires_in}秒")
        return token
    except requests.exceptions.Timeout:
        logger.error("请求超时，获取访问令牌失败")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("连接错误，获取访问令牌失败")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f'HTTP错误: {e.response.status_code}，获取访问令牌失败')
        return None
# Part 2：把图片转成Base64编码
# API不接受图片文件本身，要求把图片转成一串字母数字组成的文本
# 类比：把图片"压缩打包"成一封纯文字电报再发出去
def image_to_base64(image_path: str) -> str | None:
    """
    读取本地图片，转为Base64字符串。

    Args:
        image_path: 图片的本地路径，支持jpg/png/bmp
    Returns:
        Base64字符串，失败返回None
    """
    path = Path(image_path)

    if not path.exists():
        logger.error(f"图片文件不存在: {image_path}")
        return None

    # 检查格式（百度支持jpg/png/bmp/gif）
    supported = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
    if path.suffix.lower() not in supported:
        logger.error(f"不支持的图片格式: {path.suffix}")
        return None

    # 检查文件大小（百度限制4MB）
    size_mb = path.stat().st_size / 1024 / 1024
    if size_mb > 4:
        logger.error(f"图片过大: {size_mb:.1f}MB，百度限制4MB以内")
        return None

    with open(path, "rb") as f:         # "rb" = read binary，以二进制模式读取
        image_data = f.read()
        encoded = base64.b64encode(image_data)      # 二进制 → Base64字节
        return encoded.decode("utf-8")              # Base64字节 → 普通字符串


# ══════════════════════════════════════════════════════════════════
# Part 3：调用图像识别API
# 用Token + Base64图片 → 发给百度 → 拿回识别结果
# ══════════════════════════════════════════════════════════════════
def recognize_image(image_path: str, access_token: str) -> list | None:
    """
    调用百度通用物体识别API，返回识别结果列表。

    Args:
        image_path:   本地图片路径
        access_token: 第一步拿到的Token

    Returns:
        识别结果列表，每项包含 keyword（名称）和 score（置信度）
        失败返回None
    """
    # 把图片转Base64
    image_b64 = image_to_base64(image_path)
    if not image_b64:
        return None

    # 百度通用物体和场景识别接口地址
    # access_token直接拼在URL里，这是百度的约定方式
    url = f"https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general?access_token={access_token}"

    # 请求体：用form表单格式（不是JSON！百度这个接口要求application/x-www-form-urlencoded）
    payload = {
        "image":        image_b64,
        "baike_num":    0           # 0=不返回百科信息，加快响应速度
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"  # 必须指定这个格式
    }

    try:
        logger.info(f"正在识别图片: {image_path}")
        response = requests.post(url, data=payload, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()

        # 百度的错误也是200状态码 + error_code字段，必须单独检查
        if "error_code" in data:
            error_messages = {
                110: "Token无效，请重新获取",
                111: "Token已过期，请重新获取",
                216015: "模块关闭，请在控制台开通服务",
                282000: "服务器内部错误，稍后重试",
            }
            code = data["error_code"]
            msg = error_messages.get(code, data.get("error_msg", "未知错误"))
            logger.error(f"识别失败（错误码{code}）: {msg}")
            return None

        results = data.get("result", [])
        logger.info(f"识别完成，返回 {len(results)} 个结果")
        return results

    except requests.exceptions.Timeout:
        logger.error("识别请求超时（图片可能太大）")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP错误: {e.response.status_code}")
        return None
    except requests.exceptions.JSONDecodeError:
        logger.error("返回内容不是JSON，请检查接口地址是否正确")
        return None


# ══════════════════════════════════════════════════════════════════
# Part 4：主流程 + 结果格式化输出
# ══════════════════════════════════════════════════════════════════
def main(image_path: str):
    """
    完整链路：获取Token → 识别图片 → 格式化输出结果
    """
    print("\n" + "="*50)
    print("  百度AI图像识别 Demo")
    print("="*50)

    # Step 1: 拿Token
    token = get_access_token()
    if not token:
        print("❌ 无法获取Token，程序终止")
        return

    # Step 2: 识别图片
    results = recognize_image(image_path, token)
    if not results:
        print("❌ 图片识别失败，程序终止")
        return

    # Step 3: 格式化打印结果
    print(f"\n📷 图片路径: {image_path}")
    print(f"🔍 识别结果（共{len(results)}项）:\n")

    for i, item in enumerate(results, start=1):
        keyword = item.get("keyword", "未知")
        score   = item.get("score", 0)
        bar     = "█" * int(score * 20)   # 用方块画一个简单的进度条
        print(f"  {i}. {keyword:<15} {score:.1%}  {bar}")

    # 置信度最高的结果
    top = results[0]
    print(f"\n✅ 最可能是: 【{top['keyword']}】 置信度 {top['score']:.1%}")
    print("="*50 + "\n")


# ── 程序入口 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    # 把这里换成你电脑上任意一张图片的路径
    # Windows路径示例: r"C:\Users\lxy15\Pictures\test.jpg"
    TEST_IMAGE = r"C:\Users\lxy15\Desktop\baidu_image_demo\test.jpg"

    main(TEST_IMAGE)