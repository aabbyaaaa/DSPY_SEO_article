# -*- coding: utf-8 -*-
"""
查詢池品質分析工具
"""

import sys, io
from pathlib import Path
import pandas as pd
import json
from collections import Counter

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config, load_config

# =======================================================
# 載入資料
# =======================================================

settings = load_config()
csv_path = config.data_dir / "query_pool.csv"
df = pd.read_csv(csv_path)

print("\n" + "=" * 60)
print("📊 查詢池品質分析報告")
print("=" * 60)

# =======================================================
# 1️⃣ 基本統計
# =======================================================

print("\n【1️⃣ 基本統計】")
print(f"總查詢數：{len(df)}")
print(f"中文查詢：{len(df[df['lang']=='zh-TW'])} 條")
print(f"英文查詢：{len(df[df['lang']=='en'])} 條")

# =======================================================
# 2️⃣ 負面關鍵字檢測
# =======================================================

print("\n【2️⃣ 負面關鍵字檢測】")

negative_keywords = settings["semantic_scoring"]["negative_keywords"]
negative_queries = []

for idx, row in df.iterrows():
    query = row['query']
    matched_keywords = [kw for kw in negative_keywords if kw in query]
    if matched_keywords:
        negative_queries.append({
            'query': query,
            'keywords': matched_keywords
        })

if negative_queries:
    print(f"⚠️ 發現 {len(negative_queries)} 條查詢包含負面關鍵字：")
    for item in negative_queries[:10]:  # 只顯示前 10 個
        print(f"  - {item['query']} → {', '.join(item['keywords'])}")
else:
    print("✅ 無負面關鍵字")

# =======================================================
# 3️⃣ 查詢意圖分類（簡易版）
# =======================================================

print("\n【3️⃣ 查詢意圖分類】")

# 定義關鍵字模式
intent_patterns = {
    '產品定義': ['是什麼', '定義', '介紹', 'what is', 'definition'],
    '規格參數': ['規格', '尺寸', '容量', '材質', '溫度', '壓力', 'specifications', 'capacity'],
    '使用方法與應用': ['如何使用', '操作', '應用', '用途', 'how to use', 'application', 'uses'],
    '選購指南': ['如何選', '選購', '挑選', '比較', 'how to choose', 'buying guide', 'comparison'],
    '保養維護': ['保養', '維護', '清潔', '校正', '故障', 'maintenance', 'cleaning', 'troubleshoot'],
    '常見問題': ['常見問題', '為什麼', '怎麼辦', 'FAQ', 'why', 'common issues']
}

intent_counts = Counter()
query_intents = {}

for idx, row in df.iterrows():
    query = row['query'].lower()
    matched_intents = []

    for intent, keywords in intent_patterns.items():
        if any(kw.lower() in query for kw in keywords):
            matched_intents.append(intent)

    if not matched_intents:
        matched_intents = ['其他']

    query_intents[row['query']] = matched_intents
    for intent in matched_intents:
        intent_counts[intent] += 1

print("\n意圖分布：")
for intent, count in intent_counts.most_common():
    percentage = (count / len(df)) * 100
    print(f"  {intent}: {count} 條 ({percentage:.1f}%)")

# =======================================================
# 4️⃣ 6 類別覆蓋度檢查
# =======================================================

print("\n【4️⃣ 6 類別覆蓋度檢查】")

required_categories = [
    '產品定義',
    '規格參數',
    '使用方法與應用',
    '選購指南',
    '保養維護',
    '常見問題'
]

print("\n各類別覆蓋情況：")
for category in required_categories:
    count = intent_counts.get(category, 0)
    if count == 0:
        print(f"  ❌ {category}: 0 條（缺失）")
    elif count < 3:
        print(f"  ⚠️ {category}: {count} 條（不足）")
    else:
        print(f"  ✅ {category}: {count} 條")

# =======================================================
# 5️⃣ 查詢長度分析
# =======================================================

print("\n【5️⃣ 查詢長度分析】")

df['query_length'] = df['query'].apply(len)

zh_queries = df[df['lang'] == 'zh-TW']
en_queries = df[df['lang'] == 'en']

if len(zh_queries) > 0:
    print(f"\n中文查詢長度：")
    print(f"  平均：{zh_queries['query_length'].mean():.1f} 字")
    print(f"  最短：{zh_queries['query_length'].min()} 字")
    print(f"  最長：{zh_queries['query_length'].max()} 字")

if len(en_queries) > 0:
    print(f"\n英文查詢長度：")
    print(f"  平均：{en_queries['query_length'].mean():.1f} 字符")
    print(f"  最短：{en_queries['query_length'].min()} 字符")
    print(f"  最長：{en_queries['query_length'].max()} 字符")

# =======================================================
# 6️⃣ 顯示各類別範例
# =======================================================

print("\n【6️⃣ 各類別查詢範例】")

for category in required_categories:
    print(f"\n▸ {category}：")
    examples = [q for q, intents in query_intents.items() if category in intents]
    for example in examples[:5]:  # 每類顯示 5 個
        lang = df[df['query'] == example]['lang'].values[0]
        print(f"  [{lang}] {example}")

# =======================================================
# 7️⃣ 品質總結
# =======================================================

print("\n" + "=" * 60)
print("📋 品質總結")
print("=" * 60)

issues = []

# 檢查類別覆蓋
missing_categories = [cat for cat in required_categories if intent_counts.get(cat, 0) == 0]
low_categories = [cat for cat in required_categories if 0 < intent_counts.get(cat, 0) < 3]

if missing_categories:
    issues.append(f"❌ 缺失類別：{', '.join(missing_categories)}")
if low_categories:
    issues.append(f"⚠️ 覆蓋不足：{', '.join(low_categories)}")
if negative_queries:
    issues.append(f"⚠️ {len(negative_queries)} 條查詢包含負面關鍵字")

if issues:
    print("\n發現問題：")
    for issue in issues:
        print(f"  {issue}")
    print("\n建議：優化 Stage 1 的 Prompt，確保 6 類別均衡覆蓋")
else:
    print("\n✅ 查詢池品質良好！")

print("\n" + "=" * 60)
