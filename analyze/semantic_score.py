"""
LLM-SEO Pipeline Step 3: Semantic Scoring (v1.3 - Config Unified)
-----------------------------------------------------------------
以 Coverage + Relevance + Density 三指標綜合評分查詢潛力。

設定：
- Coverage：使用 Tavily API 實際抓取搜尋結果數
- Relevance：Embedding + GPT 混合打分（20 條樣本）
- Density：Embedding 群聚密度
- 所有配置從 config_loader 統一載入
"""

import os, json, time, sys, io, numpy as np, pandas as pd
from pathlib import Path
from openai import OpenAI
from tavily import TavilyClient
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄到路徑
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

# =======================================================
# 初始化 API
# =======================================================
print("\nInitializing Semantic Scoring Module...")

tavily = TavilyClient(api_key=config.get_tavily_key())
client = OpenAI(api_key=config.get_openai_key())

print(f"主題：{config.topic}")
print(f"權重配置 - Coverage: {config.coverage_w}, Relevance: {config.relevance_w}, Density: {config.density_w}")
print(f"混合評分 - Embedding: {config.embedding_weight}, LLM: {config.llm_weight}")

# =======================================================
# 載入查詢池與向量
# =======================================================
pool_path = config.data_dir / config.output_files["query_pool"]
vec_path = config.data_dir / config.output_files["query_vectors"]

if not pool_path.exists():
    raise FileNotFoundError(f"❌ 找不到 {pool_path}，請先執行 analyze/queries.py")
if not vec_path.exists():
    raise FileNotFoundError(f"❌ 找不到 {vec_path}，請先執行 analyze/queries.py")

pool_df = pd.read_csv(pool_path)
with open(vec_path, "r", encoding="utf-8") as f:
    vecs = json.load(f)

queries = pool_df["query"].tolist()
vectors = np.array([vecs[q] for q in queries])

# 快取檔案
cache_tavily = config.data_dir / "cache_tavily.json"
cache_relevance = config.data_dir / "cache_relevance.json"

tavily_cache = json.load(open(cache_tavily, "r", encoding="utf-8")) if cache_tavily.exists() else {}
relevance_cache = json.load(open(cache_relevance, "r", encoding="utf-8")) if cache_relevance.exists() else {}

# =======================================================
# Step 1️⃣ Coverage Score - Tavily 搜尋覆蓋度
# =======================================================
coverage_scores = {}
print("\n🌐 [Step 1] Tavily Coverage 檢查中...")

for q in tqdm(queries, desc="Tavily Search"):
    if q in tavily_cache:
        coverage_scores[q] = tavily_cache[q]
        continue
    try:
        res = tavily.search(q, max_results=10)
        num = len(res.get("results", []))
        score = min(num / 10 * 5, 5)
        coverage_scores[q] = round(score, 2)
        tavily_cache[q] = coverage_scores[q]
        time.sleep(0.5)
    except Exception as e:
        coverage_scores[q] = 0
        print(f"❌ Tavily error @ {q}: {e}")

with open(cache_tavily, "w", encoding="utf-8") as f:
    json.dump(tavily_cache, f, ensure_ascii=False, indent=2)

# =======================================================
# Step 2️⃣ Relevance Score - Embedding + GPT 混合
# =======================================================
print("\n🧠 [Step 2] 計算 Relevance 分數（Embedding + GPT 混合）...")

topic_vec = np.mean(vectors, axis=0)
similarities = cosine_similarity(vectors, topic_vec.reshape(1, -1)).flatten()
embed_scores = (similarities * 5).clip(0, 5)

# 分群抽樣（20 條）
kmeans = KMeans(n_clusters=5, random_state=42, n_init="auto").fit(vectors)
sample_indices = []
for i in range(5):
    cluster_indices = np.where(kmeans.labels_ == i)[0]
    picks = np.random.choice(cluster_indices, size=min(4, len(cluster_indices)), replace=False)
    sample_indices.extend(picks)
sample_queries = [queries[i] for i in sample_indices]

# GPT 打分
for q in tqdm(sample_queries, desc=f"{config.dspy_model_small} 評分"):
    if q in relevance_cache:
        continue
    prompt = f"""主題為「{config.topic}」。
請以 0–5 分評估以下查詢與主題的語意相關程度。
查詢：「{q}」"""
    try:
        resp = client.chat.completions.create(
            model=config.dspy_model_small,  # 使用配置的小模型
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        txt = resp.choices[0].message.content.strip()
        score = next((int(c) for c in txt if c.isdigit()), 3)
        relevance_cache[q] = score
        time.sleep(0.5)
    except Exception as e:
        relevance_cache[q] = 3
        print(f"❌ GPT error @ {q}: {e}")

with open(cache_relevance, "w", encoding="utf-8") as f:
    json.dump(relevance_cache, f, ensure_ascii=False, indent=2)

# 混合加權（使用配置的權重）
relevance_scores = []
for q, emb_score in zip(queries, embed_scores):
    if q in relevance_cache:
        llm_score = relevance_cache[q]
    else:
        q_vec = np.array(vecs[q]).reshape(1, -1)
        sample_vecs = np.array([vecs[sq] for sq in sample_queries])
        sims = cosine_similarity(q_vec, sample_vecs).flatten()
        nearest = np.argmax(sims)
        llm_score = relevance_cache.get(sample_queries[nearest], 3)
    final_score = config.embedding_weight * emb_score + config.llm_weight * llm_score
    relevance_scores.append(round(final_score, 2))

# =======================================================
# Step 3️⃣ Density Score - 群聚密度
# =======================================================
print("\n🔍 [Step 3] 計算 Density（群聚密度）...")
cos_matrix = cosine_similarity(vectors)
density_raw = cos_matrix.mean(axis=1)
density_norm = (density_raw / density_raw.max()) * 5
density_scores = [round(s, 2) for s in density_norm]

# =======================================================
# Step 4️⃣ 綜合評分（使用配置的權重）
# =======================================================
final_scores, decisions = [], []
for q in queries:
    c = coverage_scores.get(q, 0)
    r = relevance_scores[queries.index(q)]
    d = density_scores[queries.index(q)]
    score = round(
        c * config.coverage_w +
        r * config.relevance_w +
        d * config.density_w, 2
    )
    if score >= 4.0:
        decision = "✅ 高潛力"
    elif score >= 3.0:
        decision = "🟡 中潛力"
    elif score >= 2.0:
        decision = "⚪ 低潛力"
    else:
        decision = "🔴 無潛力"
    final_scores.append(score)
    decisions.append(decision)

# =======================================================
# Step 5️⃣ 輸出結果
# =======================================================
out_df = pd.DataFrame({
    "query": queries,
    "coverage": [coverage_scores.get(q, 0) for q in queries],
    "relevance": relevance_scores,
    "density": density_scores,
    "score": final_scores,
    "decision": decisions
})
out_path = config.data_dir / "semantic_scores.csv"
out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

high_count = sum(out_df["score"] >= 4.0)
avg_score = round(out_df["score"].mean(), 2)

print("\n✅ 已完成語意潛力打分！")
print(f"共處理 {len(queries)} 條查詢。")
print(f"平均分數：{avg_score}")
print(f"高潛力查詢：{high_count} 條（已標示 ✅）")
print(f"輸出檔案：{out_path}\n")
