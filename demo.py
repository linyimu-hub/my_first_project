import requests
import base64
import os
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# ══════════════════════════════════════════════════════════════════
# 配置区（所有可调参数集中在最顶部，方便维护）
# ══════════════════════════════════════════════════════════════════
load_dotenv()

API_KEY    = os.getenv("BAIDU_API_KEY")
SECRET_KEY = os.getenv("BAIDU_SECRET_KEY")

PARTS_FILE   = "parts_data.xlsx"   # 零件库Excel路径
OUTPUT_FILE  = "search_results.xlsx"  # 结果输出路径
TOP_N        = 3                   # 每次识别返回前N个匹配零件
MIN_SCORE    = 0.1                 # 低于此置信度的识别结果忽略

if not API_KEY or not SECRET_KEY:
    raise EnvironmentError("未找到API Key，请检查.env文件")

# ── 日志配置 ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# 层1：数据层——用pandas读取并清洗零件库
# ══════════════════════════════════════════════════════════════════
def load_and_clean_parts(filepath: str) -> pd.DataFrame:
    """
    读取供应商Excel，执行标准化清洗流程，返回干净的DataFrame。
    
    清洗步骤：
      1. 编号标准化（大写+去空格）
      2. 删除编号为空的行（编号是主键，不能为空）
      3. 规格去首尾空格
      4. 填充缺失值
      5. 去重（以编号为唯一标识）
      6. 重置索引
    """
    logger.info(f"读取零件库: {filepath}")
    
    if not Path(filepath).exists():
        raise FileNotFoundError(f"找不到零件库文件: {filepath}")
    
    df = pd.read_excel(filepath)
    logger.info(f"原始数据: {len(df)} 行，{len(df.columns)} 列")
    logger.info(f"各列空值数:\n{df.isnull().sum().to_string()}")
    
    # Step 1: 字符串标准化
    df["零件编号"] = df["零件编号"].str.upper().str.strip()
    df["规格"]    = df["规格"].str.strip()
    # 零件名称和类别也清理一下
    df["零件名称"] = df["零件名称"].str.strip()
    
    # Step 2: 删除编号为空的行（主键不能缺失）
    before = len(df)
    df = df.dropna(subset=["零件编号"])
    logger.info(f"删除空编号: {before - len(df)} 行")
    
    # Step 3: 填充缺失值
    df["零件名称"] = df["零件名称"].fillna("待补充")
    df["库存"]    = df["库存"].fillna(0).astype(int)
    df["单价"]    = df["单价"].fillna(df["单价"].median())
    
    # Step 4: 去重（保留第一次出现的记录）
    before = len(df)
    df = df.drop_duplicates(subset=["零件编号"])
    logger.info(f"去重: 删除 {before - len(df)} 条重复记录")
    
    # Step 5: 重置索引
    df = df.reset_index(drop=True)
    
    logger.info(f"清洗完成: 剩余 {len(df)} 条有效零件记录")
    return df


# ══════════════════════════════════════════════════════════════════
# 层2：AI层——百度API（复用之前的代码，略作优化）
# ══════════════════════════════════════════════════════════════════
def get_access_token() -> str | None:
    """获取百度Access Token，失败返回None。"""
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type":    "client_credentials",
        "client_id":     API_KEY,
        "client_secret": SECRET_KEY,
    }
    try:
        resp = requests.post(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.error(f"Token错误: {data.get('error_description')}")
            return None
        logger.info("Access Token获取成功")
        return data["access_token"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Token请求失败: {e}")
        return None


def recognize_image(image_path: str, token: str) -> list[dict]:
    """
    调用百度通用物体识别API。
    
    Returns:
        识别结果列表，每项格式: {"keyword": "轴承", "score": 0.95}
        失败返回空列表（而不是None，方便调用方直接遍历）
    """
    # 图片转Base64
    path = Path(image_path)
    if not path.exists():
        logger.error(f"图片不存在: {image_path}")
        return []
    
    with open(path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    url = f"https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general?access_token={token}"
    payload = {"image": image_b64, "baike_num": 0}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        logger.info(f"识别图片: {path.name}")
        resp = requests.post(url, data=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if "error_code" in data:
            logger.error(f"识别API错误 [{data['error_code']}]: {data.get('error_msg')}")
            return []
        
        # 过滤掉置信度太低的结果
        results = [
            item for item in data.get("result", [])
            if item.get("score", 0) >= MIN_SCORE
        ]
        logger.info(f"识别到 {len(results)} 个有效结果（置信度≥{MIN_SCORE}）")
        return results
    
    except requests.exceptions.Timeout:
        logger.error("识别超时")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"识别请求失败: {e}")
        return []


# ══════════════════════════════════════════════════════════════════
# 层3：匹配引擎——把AI关键词和零件库对应起来
# 这是整个Demo最核心的业务逻辑
# ══════════════════════════════════════════════════════════════════
def match_parts(
    ai_results: list[dict],
    parts_df: pd.DataFrame,
    top_n: int = TOP_N
) -> pd.DataFrame:
    """
    用AI识别出的关键词，在零件库里做模糊匹配，返回最相关的零件。
    
    匹配逻辑：
      - 对每个AI关键词，在"零件名称"和"类别"列里做str.contains()匹配
      - 匹配到的行加上对应的AI置信度作为相关性分数
      - 按相关性分数降序排列，返回前top_n条
    
    Args:
        ai_results: recognize_image()返回的列表
        parts_df:   清洗后的零件库DataFrame
        top_n:      最多返回几条匹配结果
    
    Returns:
        包含匹配结果的DataFrame，新增"匹配关键词"和"相关性分数"列
    """
    if not ai_results:
        logger.warning("AI没有返回任何结果，无法匹配")
        return pd.DataFrame()  # 返回空DataFrame
    
    matched_rows = []   # 收集所有匹配到的行
    
    for item in ai_results:
        keyword = item["keyword"]   # 例如："轴承"
        score   = item["score"]     # 例如：0.95
        
        # 在零件名称和类别里同时搜索这个关键词
        # na=False：如果该格是NaN，不报错，当作False处理
        mask = (
            parts_df["零件名称"].str.contains(keyword, case=False, na=False) |
            parts_df["类别"].str.contains(keyword,    case=False, na=False)
        )
        
        matched = parts_df[mask].copy()   # 筛选出匹配的行，copy()避免修改原数据
        
        if matched.empty:
            logger.debug(f"关键词「{keyword}」在零件库中没有匹配")
            continue
        
        # 给每条匹配结果记录上：是被哪个关键词匹配到的、置信度多少
        matched["匹配关键词"] = keyword
        matched["相关性分数"] = score
        matched_rows.append(matched)
        
        logger.info(f"关键词「{keyword}」(置信度{score:.0%}) → 匹配到 {len(matched)} 条零件")
    
    if not matched_rows:
        logger.warning("所有关键词均未匹配到零件库中的记录")
        return pd.DataFrame()
    
    # 合并所有匹配结果
    result_df = pd.concat(matched_rows, ignore_index=True)
    
    # 同一零件可能被多个关键词匹配到，保留相关性分数最高的那条
    result_df = (
        result_df
        .sort_values("相关性分数", ascending=False)
        .drop_duplicates(subset=["零件编号"])   # 每个零件只保留一条
        .head(top_n)
        .reset_index(drop=True)
    )
    
    return result_df


# ══════════════════════════════════════════════════════════════════
# 层4：输出层——格式化打印 + 写入Excel
# ══════════════════════════════════════════════════════════════════
def print_results(image_path: str, ai_results: list, matched_df: pd.DataFrame):
    """在终端漂亮地打印识别和匹配结果。"""
    print("\n" + "="*60)
    print(f"  图片: {Path(image_path).name}")
    print("="*60)
    
    print("\n【AI识别结果】")
    for i, item in enumerate(ai_results[:5], 1):
        bar = "█" * int(item["score"] * 20)
        print(f"  {i}. {item['keyword']:<12} {item['score']:.0%}  {bar}")
    
    print(f"\n【零件库匹配结果（Top {TOP_N}）】")
    if matched_df.empty:
        print("  ❌ 未找到匹配的零件")
    else:
        for _, row in matched_df.iterrows():
            print(f"  ✅ [{row['零件编号']}] {row['零件名称']}")
            print(f"     规格: {row['规格']}  单价: ¥{row['单价']}  库存: {int(row['库存'])}件")
            print(f"     匹配词: 「{row['匹配关键词']}」  相关性: {row['相关性分数']:.0%}")
    
    print("="*60 + "\n")


def save_results(image_path: str, ai_results: list,
                 matched_df: pd.DataFrame, output_file: str):
    """
    把识别结果和匹配结果写入Excel，方便存档和汇报。
    每次运行追加写入，不覆盖历史记录。
    """
    # 构建AI识别结果表
    ai_df = pd.DataFrame(ai_results)
    ai_df.insert(0, "图片文件", Path(image_path).name)  # 第一列插入图片名
    ai_df.insert(1, "识别时间", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 构建匹配结果表
    if not matched_df.empty:
        match_df = matched_df.copy()
        match_df.insert(0, "图片文件", Path(image_path).name)
        match_df["相关性分数"] = match_df["相关性分数"].map("{:.0%}".format)
    else:
        match_df = pd.DataFrame({"图片文件": [Path(image_path).name], "结果": ["未匹配"]})
    
    # 写入Excel，AI结果和匹配结果分两个sheet
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        ai_df.to_excel(writer,    sheet_name="AI识别结果", index=False)
        match_df.to_excel(writer, sheet_name="零件匹配结果", index=False)
    
    logger.info(f"结果已保存到: {output_file}")


# ══════════════════════════════════════════════════════════════════
# 主流程：把四层串起来
# ══════════════════════════════════════════════════════════════════
def run_pipeline(image_path: str):
    """
    完整的以图搜零件流程。
    
    1. 加载并清洗零件库
    2. 获取百度Token
    3. AI识别图片
    4. 关键词匹配零件库
    5. 打印结果 + 保存Excel
    """
    print(f"\n🔍 开始识别: {image_path}")
    
    # 层1：数据层
    parts_df = load_and_clean_parts(PARTS_FILE)
    
    # 层2：获取Token（Token有效期30天，实际项目里应缓存，这里简化）
    token = get_access_token()
    if not token:
        logger.error("无法获取Token，终止")
        return
    
    # 层3：AI识别
    ai_results = recognize_image(image_path, token)
    if not ai_results:
        logger.error("图片识别失败，终止")
        return
    
    # 层4：匹配
    matched_df = match_parts(ai_results, parts_df)
    
    # 层5：输出
    print_results(image_path, ai_results, matched_df)
    save_results(image_path, ai_results, matched_df, OUTPUT_FILE)


# ── 入口 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 换成你自己的图片路径
    TEST_IMAGE = r"C:\Users\lxy15\Desktop\baidu_image_demo\test.jpg"
    run_pipeline(TEST_IMAGE)