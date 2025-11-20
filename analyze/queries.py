"""
LLM-SEO Pipeline Step 1: Query Pool Generator (v1.4)
---------------------------------------------------
用途：
依據設定主題 (config/settings.yaml) + 手動定義的 BASE_SEEDS，
生成中英混合的查詢池，並進行語言偵測、反向翻譯與 Embedding 向量化。

重要原則：
✅ LLM 只「理解 topic」，不會自動塞入 BASE_SEEDS。
✅ BASE_SEEDS 完全由使用者人工控制（避免語義偏移）。
✅ 統一使用 config_loader 載入配置。
"""

import os, json, time, sys, io, re
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm
import pandas as pd

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄到路徑，確保可以載入 config
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

# =======================================================
# 初始化與設定
# =======================================================
# 確保資料目錄存在
config.data_dir.mkdir(parents=True, exist_ok=True)

print(f"主題：{config.topic}")
print(f"目標查詢數量：{config.query_pool_size}")

# === 初始化 OpenAI ===
client = OpenAI(api_key=config.get_openai_key())

# =======================================================
# 查詢種子設定（從 settings.yaml 載入）
# =======================================================
BASE_SEEDS = config.base_seeds

assert isinstance(BASE_SEEDS, list) and len(BASE_SEEDS) > 0, \
    "❌ BASE_SEEDS 不可為空，請在 config/settings.yaml 的 query_generation.base_seeds 設定至少 1 個查詢種子。"

print(f"📌 手動種子數量：{len(BASE_SEEDS)}")

# =======================================================
# 查詢生成提示詞
# =======================================================
PROMPT = """請產出 {n} 條與「{topic}」相關的**繁體中文**查詢，
涵蓋 資訊/商業/比較/維護/校正/錯誤排查/替代品/配件/常見問題。

**重要規則**：
1. 只產出繁體中文查詢，不要產出英文查詢
2. 使用台灣常用術語（例如：微量吸管、移液管、吸管尖）
3. 每行一條查詢，請勿加編號、引號或標點
4. 查詢要自然、符合台灣使用者的搜尋習慣"""

# =======================================================
# 生成查詢池
# =======================================================
def generate_queries(topic: str, n: int):
    print(f"\n🤖 生成查詢中（主題：{topic}）...")
    prompt = PROMPT.format(topic=topic, n=n)
    resp = client.chat.completions.create(
        model=config.dspy_model_small,  # 使用配置的小模型
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    text = resp.choices[0].message.content.strip()
    extra = [q.strip() for q in text.splitlines() if q.strip()]
    queries = BASE_SEEDS + extra
    print(f"✅ LLM 生成 {len(extra)} 條查詢")
    return list(dict.fromkeys(queries))  # 去重

# =======================================================
# 語言檢測（簡化版 - 只處理繁體中文）
# =======================================================
def enrich_language(q):
    """
    簡化版語言檢測：只處理繁體中文查詢
    使用正則判斷是否包含中文字符
    """
    # 檢查是否包含中文字符
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', q))

    if has_chinese:
        # 中文查詢，直接返回
        return {"query": q, "lang": "zh-TW"}
    else:
        # 如果出現英文查詢（不應該發生），發出警告
        print(f"⚠️ 發現非中文查詢：{q}，將跳過此查詢")
        return None

# =======================================================
# Embedding 向量化
# =======================================================
def embed_query(q):
    try:
        resp = client.embeddings.create(model="text-embedding-3-large", input=q)
        return resp.data[0].embedding
    except Exception as e:
        print(f"⚠️ 向量生成失敗：{q} ({e})")
        return None

# =======================================================
# 主執行區塊
# =======================================================
def main():
    all_queries = generate_queries(config.topic, config.query_pool_size)
    enriched = []
    vectors = {}

    print("\n🌐 檢查查詢語言...")
    for q in tqdm(all_queries, desc="Language check"):
        result = enrich_language(q)
        if result is not None:  # 只保留中文查詢
            enriched.append(result)

    print(f"✅ 保留 {len(enriched)} 條繁體中文查詢")

    print("\n🧠 建立 Embedding 向量中...")
    for item in tqdm(enriched, desc="Embedding"):
        q = item["query"]
        vec = embed_query(q)
        if vec:
            vectors[q] = vec
        time.sleep(0.5)

    # === 儲存檔案（使用配置的路徑）===
    csv_path = config.data_dir / config.output_files["query_pool"]
    json_path = config.data_dir / config.output_files["query_vectors"]

    df = pd.DataFrame(enriched)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(vectors, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 查詢池與向量建立完成！")
    print(f"📁 {csv_path}（{len(df)} 條）")
    print(f"📁 {json_path}（{len(vectors)} 條）")

    # === 驗證資料一致性 ===
    if len(df) == len(vectors):
        print("🧩 驗證成功：查詢與向量數量一致 ✅")
    else:
        missing = len(df) - len(vectors)
        print(f"⚠️ 有 {missing} 條查詢缺少向量，建議執行 repair_vectors.py 修復。")

# =======================================================
if __name__ == "__main__":
    main()
