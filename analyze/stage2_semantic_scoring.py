# -*- coding: utf-8 -*-
"""
LLM-SEO Pipeline Stage ②: Semantic Scoring v2.0 (Bilingual)
-------------------------------------------------------------
新架構三維評分系統：AI Coverage + Relevance + SERP Signal

特點：
1. 支援雙語（繁體中文 + 英文）
2. AI Coverage: 使用 Tavily 檢測 AI 引擎內容可用性
3. Relevance: 使用 OpenAI Embeddings 計算主題相關性（含負面關鍵字過濾）
4. SERP Signal: 模擬 PAA + AI Overview + Ads 信號
5. 方案 B: 標記但保留所有查詢（quality_tier）

輸入：
- data/query_pool_merged.csv
- data/query_vectors_merged.json

輸出：
- data/semantic_scores.csv
"""

import os, json, sys, io, time
import numpy as np
import pandas as pd
from pathlib import Path
from openai import OpenAI
from tavily import TavilyClient
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

# ================================================
# 初始化
# ================================================
print("\n" + "=" * 60)
print("🎯 語義評分 v2.0 - 雙語版")
print("=" * 60)
print(f"中文主題：{config.topic}")
print(f"英文主題：{config.topic_en}")

# 初始化 API
tavily = TavilyClient(api_key=config.get_tavily_key())
client = OpenAI(api_key=config.get_openai_key())

# 讀取配置
weights = config._config["semantic_scoring"]["weights"]
thresholds = config._config["semantic_scoring"]["thresholds"]
negative_keywords = config._config["semantic_scoring"]["negative_keywords"]

print(f"\n📊 評分權重：")
print(f"   AI Coverage: {weights['ai_coverage']:.0%}")
print(f"   Relevance: {weights['relevance']:.0%}")
print(f"   SERP Signal: {weights['serp_signal']:.0%}")

print(f"\n📌 品質分級閾值：")
print(f"   High Tier: ≥ {thresholds['high_tier']}")
print(f"   Medium Tier: ≥ {thresholds['medium_tier']}")
print(f"   Low Tier: < {thresholds['medium_tier']}")

# ================================================
# 載入查詢池與向量
# ================================================
pool_path = config.data_dir / "query_pool.csv"
vec_path = config.data_dir / "query_vectors.json"

if not pool_path.exists():
    raise FileNotFoundError(f"❌ 找不到 {pool_path}，請先執行 analyze/stage1_query_generation.py")
if not vec_path.exists():
    raise FileNotFoundError(f"❌ 找不到 {vec_path}，請先執行 analyze/stage1_query_generation.py")

print(f"\n📂 載入查詢池：{pool_path}")
pool_df = pd.read_csv(pool_path)

print(f"📂 載入向量：{vec_path}")
with open(vec_path, "r", encoding="utf-8") as f:
    vecs = json.load(f)

queries = pool_df["query"].tolist()
vectors = np.array([vecs[q] for q in queries])

# 語言檢測
languages = []
for q in queries:
    if any('\u4e00' <= c <= '\u9fff' for c in q):
        languages.append("zh-TW")
    else:
        languages.append("en")

zh_count = languages.count("zh-TW")
en_count = languages.count("en")

print(f"\n✅ 載入 {len(queries)} 個查詢")
print(f"   繁體中文：{zh_count}")
print(f"   English：{en_count}")

# 快取檔案
cache_path = config.data_dir / "cache_semantic_v2.json"
cache = {}
if cache_path.exists():
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)
    print(f"\n📦 載入 {len(cache)} 個快取結果")

# ================================================
# Step 1️⃣: AI Coverage Score (Tavily)
# ================================================
print("\n" + "=" * 60)
print("📡 Step 1: AI Coverage - Tavily 內容檢測")
print("=" * 60)

ai_coverage_scores = []
tavily_max = config._config["semantic_scoring"]["ai_coverage"]["tavily_max_results"]

# 用於統計的調試數據
debug_sources_count = []
debug_avg_scores = []

for q in tqdm(queries, desc="Tavily 搜尋"):
    cache_key = f"ai_coverage_{q}"
    cache_detail_key = f"ai_coverage_detail_{q}"

    if cache_key in cache and cache_detail_key in cache:
        # 從快取讀取
        detail = cache[cache_detail_key]
        num_sources = detail["num_sources"]
        avg_tavily_score = detail["avg_score"]

        # 使用新評分邏輯重新計算（即使有舊快取）
        quantity_score = min(3, num_sources * 0.3)
        quality_score = avg_tavily_score * 7
        score = round(quantity_score + quality_score, 2)

        debug_sources_count.append(num_sources)
        debug_avg_scores.append(avg_tavily_score)
    else:
        try:
            res = tavily.search(q, max_results=tavily_max)
            results = res.get("results", [])
            num_sources = len(results)

            # 調試輸出：記錄來源數量
            debug_sources_count.append(num_sources)

            # 調試輸出：記錄 Tavily 品質分數
            if num_sources > 0:
                tavily_scores = [r.get("score", 0) for r in results]
                avg_tavily_score = sum(tavily_scores) / num_sources
                debug_avg_scores.append(avg_tavily_score)
            else:
                avg_tavily_score = 0
                debug_avg_scores.append(0)

            # 新評分邏輯：數量基礎分 (30%) + 品質加權分 (70%)
            # 來源數量分 (最多 3 分)
            quantity_score = min(3, num_sources * 0.3)

            # 品質加權分 (最多 7 分)
            quality_score = avg_tavily_score * 7

            # 總分 = 數量分 + 品質分
            score = round(quantity_score + quality_score, 2)

            # 保存分數和詳細資訊到快取
            cache[cache_key] = score
            cache[cache_detail_key] = {
                "num_sources": num_sources,
                "avg_score": avg_tavily_score,
                "quantity_score": quantity_score,
                "quality_score": quality_score
            }
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Tavily error @ {q}: {e}")
            score = 0
            cache[cache_key] = 0
            cache[cache_detail_key] = {"num_sources": 0, "avg_score": 0}
            debug_sources_count.append(0)
            debug_avg_scores.append(0)

    ai_coverage_scores.append(score)

# 即時儲存快取
with open(cache_path, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print(f"✅ AI Coverage 平均分數：{np.mean(ai_coverage_scores):.2f}/10")
print(f"   最小分數：{min(ai_coverage_scores):.2f}/10")
print(f"   最大分數：{max(ai_coverage_scores):.2f}/10")
print(f"   標準差：{np.std(ai_coverage_scores):.2f}")

# 調試統計報告
if debug_sources_count:
    print(f"\n🔍 Tavily 來源數量統計：")
    print(f"   最小值：{min(debug_sources_count)} 個")
    print(f"   最大值：{max(debug_sources_count)} 個")
    print(f"   平均值：{np.mean(debug_sources_count):.2f} 個")
    print(f"   中位數：{np.median(debug_sources_count):.1f} 個")

    # 分布統計
    from collections import Counter
    dist = Counter(debug_sources_count)
    print(f"\n   來源數量分布：")
    for count in sorted(dist.keys()):
        print(f"      {count} 個來源：{dist[count]} 個查詢 ({dist[count]/len(debug_sources_count):.1%})")

if debug_avg_scores:
    print(f"\n🔍 Tavily 品質分數統計（0-1）：")
    print(f"   最小值：{min(debug_avg_scores):.3f}")
    print(f"   最大值：{max(debug_avg_scores):.3f}")
    print(f"   平均值：{np.mean(debug_avg_scores):.3f}")
    print(f"   中位數：{np.median(debug_avg_scores):.3f}")

print(f"\n📐 評分公式：數量分(30%) + 品質分(70%)")
print(f"   數量分 = min(3, num_sources * 0.3)")
print(f"   品質分 = avg_tavily_score * 7")
print(f"   總分 = 數量分 + 品質分")

# ================================================
# Step 2️⃣: Relevance Score (Embedding + 負面關鍵字)
# ================================================
print("\n" + "=" * 60)
print("🧠 Step 2: Relevance - Embedding 相關性")
print("=" * 60)

# 分語言計算主題向量
zh_queries = [q for q, lang in zip(queries, languages) if lang == "zh-TW"]
en_queries = [q for q, lang in zip(queries, languages) if lang == "en"]

zh_vectors = np.array([vecs[q] for q in zh_queries]) if zh_queries else None
en_vectors = np.array([vecs[q] for q in en_queries]) if en_queries else None

# 中文主題向量
if zh_vectors is not None:
    zh_topic_vec = np.mean(zh_vectors, axis=0)
    print(f"✅ 計算中文主題向量（{len(zh_queries)} 個查詢）")
else:
    zh_topic_vec = None
    print(f"⚠️ 無中文查詢")

# 英文主題向量
if en_vectors is not None:
    en_topic_vec = np.mean(en_vectors, axis=0)
    print(f"✅ 計算英文主題向量（{len(en_queries)} 個查詢）")
else:
    en_topic_vec = None
    print(f"⚠️ 無英文查詢")

# 計算相關性分數
relevance_scores = []
neg_penalty = config._config["semantic_scoring"]["relevance"]["negative_keyword_penalty"]

for q, q_vec, lang in zip(queries, vectors, languages):
    # 選擇對應語言的主題向量
    if lang == "zh-TW" and zh_topic_vec is not None:
        topic_vec = zh_topic_vec
    elif lang == "en" and en_topic_vec is not None:
        topic_vec = en_topic_vec
    else:
        # 預設使用全體平均
        topic_vec = np.mean(vectors, axis=0)

    # 計算 cosine similarity
    similarity = cosine_similarity(q_vec.reshape(1, -1), topic_vec.reshape(1, -1))[0][0]

    # 分數：0-10 分
    score = similarity * 10

    # 負面關鍵字懲罰
    if any(kw in q for kw in negative_keywords):
        score *= neg_penalty
        print(f"⚠️ 負面關鍵字懲罰：{q[:30]}... ({score:.2f})")

    relevance_scores.append(round(score, 2))

print(f"✅ Relevance 平均分數：{np.mean(relevance_scores):.2f}/10")

# ================================================
# Step 3️⃣: SERP Signal Score (模擬)
# ================================================
print("\n" + "=" * 60)
print("🔍 Step 3: SERP Signal - PAA + AI Overview")
print("=" * 60)
print("⚠️ 此階段為模擬分數（實際 SERP 信號將在 Stage 3 獲取）")
print("⚠️ 注意：不考慮 Google Ads 作為評分因素")

# 模擬 SERP Signal 分數（基於查詢特徵）
serp_signal_scores = []

for q in queries:
    # 簡單啟發式規則（實際應從 SERP API 獲取）
    score = 5.0  # 預設基準分

    # 長尾查詢通常有更多 PAA
    if len(q.split()) >= 5 or len(q) >= 15:
        score += 2.0

    # 問題型查詢 (更可能觸發 PAA 和 AI Overview)
    question_words = ["如何", "怎麼", "為什麼", "是什麼", "how", "why", "what", "when"]
    if any(qw in q.lower() for qw in question_words):
        score += 1.5

    # 故障/問題類型（高 PAA + AI Overview 機率）
    problem_words = ["故障", "問題", "異常", "錯誤", "不", "無法", "error", "issue", "problem", "fail"]
    if any(pw in q.lower() for pw in problem_words):
        score += 1.5

    serp_signal_scores.append(min(10, round(score, 2)))

print(f"✅ SERP Signal 平均分數：{np.mean(serp_signal_scores):.2f}/10")

# ================================================
# Step 4️⃣: 綜合評分與品質分級
# ================================================
print("\n" + "=" * 60)
print("📊 Step 4: 綜合評分與品質分級")
print("=" * 60)

final_scores = []
quality_tiers = []

for q, ai_cov, rel, serp in zip(queries, ai_coverage_scores, relevance_scores, serp_signal_scores):
    # 加權計算
    score = (
        ai_cov * weights["ai_coverage"] +
        rel * weights["relevance"] +
        serp * weights["serp_signal"]
    )
    score = round(score, 2)
    final_scores.append(score)

    # 品質分級
    if score >= thresholds["high_tier"]:
        tier = "high"
    elif score >= thresholds["medium_tier"]:
        tier = "medium"
    else:
        tier = "low"
    quality_tiers.append(tier)

# ================================================
# Step 5️⃣: 輸出結果
# ================================================
out_df = pd.DataFrame({
    "query": queries,
    "lang": languages,
    "ai_coverage_score": ai_coverage_scores,
    "relevance_score": relevance_scores,
    "serp_signal_score": serp_signal_scores,
    "score": final_scores,
    "quality_tier": quality_tiers
})

out_path = config.data_dir / "semantic_scores.csv"
out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

# 統計報告
high_count = sum(out_df["quality_tier"] == "high")
medium_count = sum(out_df["quality_tier"] == "medium")
low_count = sum(out_df["quality_tier"] == "low")

zh_df = out_df[out_df["lang"] == "zh-TW"]
en_df = out_df[out_df["lang"] == "en"]

print("\n" + "=" * 60)
print("✅ 語義評分完成！")
print("=" * 60)
print(f"📁 輸出檔案：{out_path}")
print(f"\n📊 整體統計：")
print(f"   總查詢數：{len(queries)}")
print(f"   平均分數：{np.mean(final_scores):.2f}/10")

print(f"\n🎯 品質分級：")
print(f"   ✅ High Tier: {high_count} ({high_count/len(queries):.1%})")
print(f"   ⚠️ Medium Tier: {medium_count} ({medium_count/len(queries):.1%})")
print(f"   ❌ Low Tier: {low_count} ({low_count/len(queries):.1%})")

print(f"\n🌐 語言分布：")
print(f"   繁體中文：{len(zh_df)} 個 (平均分數: {zh_df['score'].mean():.2f})")
print(f"   English：{len(en_df)} 個 (平均分數: {en_df['score'].mean():.2f})")

print(f"\n💡 後續處理建議：")
print(f"   - Stage 3 將只處理 High + Medium Tier ({high_count + medium_count} 個查詢)")
print(f"   - Low Tier 查詢已保留在檔案中供分析使用")

print("\n🎉 準備進入 Stage ③：SERP 分析")
print("=" * 60 + "\n")
