# -*- coding: utf-8 -*-
"""
LLM-SEO Pipeline Step 1: Query Pool Generator (v2.0 - Bilingual)
-----------------------------------------------------------------
用途：
生成雙語查詢池（繁體中文 + 英文），並進行語言偵測與 Embedding 向量化。

新功能：
✅ 支援雙語查詢生成（20 中文 + 20 英文）
✅ 分別管理中英文種子查詢
✅ 自動語言檢測
✅ 統一 Embedding 向量化
"""

import os, json, time, sys, io, re
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm
import pandas as pd

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄到路徑
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

# =======================================================
# 初始化與設定
# =======================================================
config.data_dir.mkdir(parents=True, exist_ok=True)

print("\n" + "=" * 60)
print("🌐 雙語查詢池生成器")
print("=" * 60)
print(f"中文主題：{config.topic}")
print(f"英文主題：{config.topic_en}")
print(f"目標查詢數量：{config.query_pool_size}")
print(f"  - 繁體中文：{config.zh_tw_queries}")
print(f"  - 英文：{config.en_queries}")

# 初始化 OpenAI
client = OpenAI(api_key=config.get_openai_key())

# =======================================================
# 查詢種子設定
# =======================================================
BASE_SEEDS_ZH = config.base_seeds_zh
BASE_SEEDS_EN = config.base_seeds_en

print(f"\n📌 種子查詢數量：")
print(f"  - 中文種子：{len(BASE_SEEDS_ZH)}")
print(f"  - 英文種子：{len(BASE_SEEDS_EN)}")

# =======================================================
# 查詢生成提示詞
# =======================================================

PROMPT_ZH = """請產出 {n} 條與「{topic}」相關的**繁體中文**查詢。

**必須涵蓋的 6 大類別**（每類至少 2-3 條）：
1. 產品定義與規格 - 材質、容量、尺寸、壓力、溫度等技術規格相關查詢
2. 應用場景 - 實際使用情境、適用對象、滅菌/處理對象等應用相關查詢
3. 選購指南 - 如何選擇、規格比較、選購要素（避免品牌推薦）
4. 保養維護 - 清潔、校正、故障排除、儲存條件相關查詢
5. 常見問題 (FAQ) - 為什麼、如何解決、安全注意事項、使用期限等疑問
6. 應用標準與流程 - 操作步驟、檢測目標、品質控制相關查詢

**重要規則**：
1. 只產出繁體中文查詢，不要產出英文查詢
2. 使用台灣常用術語
3. 每行一條查詢，請勿加編號、引號或標點
4. 查詢要自然、符合台灣使用者的搜尋習慣
5. 避免「品牌」、「廠商」、「價格」、「哪裡買」等商業化詞彙
6. 應用場景範例僅供參考，請根據產品特性生成合適的查詢

直接輸出查詢，不需要任何前言或說明。"""

PROMPT_EN = """Generate {n} queries related to "{topic}" in **English**.

**Must cover these 6 categories** (at least 2-3 queries per category):
1. Product Definition & Specifications - material, capacity, size, pressure, temperature specs
2. Application Scenarios - medical instruments, laboratory, food processing, specific use cases
3. Buying Guide - how to choose, spec comparison, selection factors (avoid brand recommendations)
4. Maintenance - cleaning, calibration, troubleshooting, storage conditions
5. FAQs - why, how to solve, safety precautions, lifespan
6. Standards & Procedures - operation steps, testing targets, quality control

**Important rules**:
1. Only generate English queries, no Chinese
2. Use international standard terminology
3. One query per line, no numbering or quotes
4. Natural search queries that users would type
5. Avoid "brand", "vendor", "price", "where to buy" commercial terms

Output queries directly, no preamble needed."""

# =======================================================
# 生成查詢池
# =======================================================

def generate_queries(topic: str, n: int, language: str = "zh-TW"):
    """
    生成查詢

    Args:
        topic: 主題
        n: 生成數量
        language: zh-TW 或 en

    Returns:
        查詢列表
    """
    if language == "zh-TW":
        prompt_template = PROMPT_ZH
        seeds = BASE_SEEDS_ZH
        lang_name = "繁體中文"
    else:
        prompt_template = PROMPT_EN
        seeds = BASE_SEEDS_EN
        lang_name = "English"

    print(f"\n🤖 生成 {lang_name} 查詢（主題：{topic}）...")

    prompt = prompt_template.format(topic=topic, n=n)
    resp = client.chat.completions.create(
        model=config.dspy_model_small,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    text = resp.choices[0].message.content.strip()
    extra = [q.strip() for q in text.splitlines() if q.strip()]

    # 合併種子 + 生成的查詢
    queries = seeds + extra

    print(f"✅ LLM 生成 {len(extra)} 條查詢")
    print(f"✅ 總計 {len(queries)} 條查詢（含種子）")

    # 去重
    return list(dict.fromkeys(queries))

# =======================================================
# 語言檢測
# =======================================================

def detect_language(q: str) -> str:
    """
    檢測查詢語言

    Returns:
        "zh-TW" 或 "en"
    """
    # 檢查是否包含中文字符
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', q))

    if has_chinese:
        return "zh-TW"
    else:
        return "en"

def enrich_language(q: str):
    """
    為查詢添加語言標記

    Returns:
        {"query": str, "lang": str} 或 None
    """
    lang = detect_language(q)
    return {"query": q, "lang": lang}

# =======================================================
# Embedding 向量化
# =======================================================

def embed_query(q: str):
    """生成 Embedding 向量"""
    try:
        resp = client.embeddings.create(
            model="text-embedding-3-large",
            input=q
        )
        return resp.data[0].embedding
    except Exception as e:
        print(f"⚠️ 向量生成失敗：{q} ({e})")
        return None

# =======================================================
# 主執行區塊
# =======================================================

def main():
    print("\n" + "=" * 60)
    print("🚀 開始生成雙語查詢池")
    print("=" * 60)

    # 生成中文查詢
    zh_queries = generate_queries(
        topic=config.topic,
        n=config.zh_tw_queries,
        language="zh-TW"
    )

    # 生成英文查詢
    en_queries = generate_queries(
        topic=config.topic_en,
        n=config.en_queries,
        language="en"
    )

    # 合併所有查詢
    all_queries = zh_queries + en_queries

    print("\n" + "=" * 60)
    print(f"📊 查詢池統計")
    print("=" * 60)
    print(f"繁體中文：{len(zh_queries)} 條")
    print(f"English：{len(en_queries)} 條")
    print(f"總計：{len(all_queries)} 條")

    # 語言檢測與標記
    print("\n🌐 進行語言檢測...")
    enriched = []
    for q in tqdm(all_queries, desc="Language detection"):
        result = enrich_language(q)
        if result:
            enriched.append(result)

    # 統計語言分布
    zh_count = sum(1 for item in enriched if item["lang"] == "zh-TW")
    en_count = sum(1 for item in enriched if item["lang"] == "en")

    print(f"✅ 語言檢測完成")
    print(f"   繁體中文：{zh_count} 條")
    print(f"   English：{en_count} 條")

    # Embedding 向量化
    print("\n🧠 建立 Embedding 向量中...")
    vectors = {}

    for item in tqdm(enriched, desc="Embedding"):
        q = item["query"]
        vec = embed_query(q)
        if vec:
            vectors[q] = vec
        time.sleep(0.5)  # API 限流保護

    # 儲存檔案
    csv_path = config.data_dir / config.output_files["query_pool"]
    json_path = config.data_dir / config.output_files["query_vectors"]

    df = pd.DataFrame(enriched)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(vectors, f, ensure_ascii=False, indent=2)

    # 結果報告
    print("\n" + "=" * 60)
    print("✅ 雙語查詢池建立完成！")
    print("=" * 60)
    print(f"📁 {csv_path}（{len(df)} 條）")
    print(f"📁 {json_path}（{len(vectors)} 條）")
    print(f"\n📊 最終統計：")
    print(f"   繁體中文：{zh_count} 條")
    print(f"   English：{en_count} 條")
    print(f"   向量覆蓋率：{len(vectors)}/{len(df)} ({len(vectors)/len(df)*100:.1f}%)")

    # 驗證
    if len(df) == len(vectors):
        print("\n🧩 驗證成功：查詢與向量數量一致 ✅")
    else:
        missing = len(df) - len(vectors)
        print(f"\n⚠️ 有 {missing} 條查詢缺少向量")

    print("\n" + "=" * 60)
    print("🎉 完成！")
    print("=" * 60)

# =======================================================
if __name__ == "__main__":
    main()
