"""
LLM-SEO Pipeline Step 1.5: Merge Queries (Semantic Deduplication)
-----------------------------------------------------------------
用途：
依據語義相似度自動合併中英文或近義查詢，
避免後續 semantic_score.py 重複計算或 GPT 重複評分。

輸入：
  data/query_pool.csv
  data/query_vectors.json

輸出：
  data/query_pool_merged.csv
  data/query_vectors_merged.json

規則：
- 使用 cosine similarity 計算語義相似度。
- 相似度閾值從 settings.yaml 載入。
- 保留每群中最短的中文或原始查詢為 main_query。
"""

import os, json, sys, io, numpy as np, pandas as pd
from pathlib import Path
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
# ✅ 基本設定
# =======================================================
THRESHOLD = config.merge_threshold  # 從配置載入語義相似度閾值

POOL_PATH = config.data_dir / config.output_files["query_pool"]
VEC_PATH = config.data_dir / config.output_files["query_vectors"]

OUT_CSV = config.data_dir / config.output_files["merged_queries"]
OUT_JSON = config.data_dir / config.output_files["merged_vectors"]

print("Semantic Merge Started...")
print(f"相似度閾值：{THRESHOLD}\n")

# =======================================================
# 載入資料
# =======================================================
if not os.path.exists(POOL_PATH) or not os.path.exists(VEC_PATH):
    raise FileNotFoundError("❌ 找不到 query_pool.csv 或 query_vectors.json，請先執行 queries.py")

df = pd.read_csv(POOL_PATH)
with open(VEC_PATH, "r", encoding="utf-8") as f:
    vecs = json.load(f)

queries = df["query"].tolist()
vectors = np.array([vecs[q] for q in queries])

print(f"📦 載入 {len(queries)} 條查詢，開始計算語義相似度...")

# =======================================================
# 建立相似度矩陣
# =======================================================
sim_matrix = cosine_similarity(vectors)
merged_groups = []
visited = set()

for i, q in enumerate(tqdm(queries, desc="Merging")):
    if q in visited:
        continue

    group = [q]
    visited.add(q)
    for j in range(i + 1, len(queries)):
        if queries[j] in visited:
            continue
        if sim_matrix[i][j] >= THRESHOLD:
            group.append(queries[j])
            visited.add(queries[j])
    merged_groups.append(group)

# =======================================================
# 建立合併結果
# =======================================================
merged_records = []
merged_vectors = {}

for group in merged_groups:
    # 保留最短的中文（或第一條）作為主查詢
    main_query = min(group, key=len)
    synonyms = [q for q in group if q != main_query]

    merged_records.append({
        "main_query": main_query,
        "synonyms": "; ".join(synonyms)
    })

    # 平均群組向量
    group_vecs = np.array([vecs[q] for q in group])
    merged_vectors[main_query] = group_vecs.mean(axis=0).tolist()

# =======================================================
# 輸出結果
# =======================================================
merged_df = pd.DataFrame(merged_records)
merged_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(merged_vectors, f, ensure_ascii=False, indent=2)

print("\n✅ 語義合併完成！")
print(f"原始查詢：{len(queries)} → 合併後：{len(merged_records)}")
print(f"📁 輸出檔案：")
print(f"   - {OUT_CSV}")
print(f"   - {OUT_JSON}")
