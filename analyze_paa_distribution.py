# -*- coding: utf-8 -*-
"""
📊 PAA 問題分佈分析腳本
分析 127 個 PAA 問題的頻率、語言、類型、與前 5 個區塊的相似度
"""

import os
import sys
import io
import json
import re
from pathlib import Path
from typing import List, Dict
from openai import OpenAI

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄
ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config, load_config

print("\n" + "=" * 60)
print("📊 PAA 問題分佈分析")
print("=" * 60)

# ================================================
# 1️⃣ 載入資料
# ================================================
print("\n📦 載入資料...")

# 載入 article_outlines_bilingual.json
outlines_path = config.data_dir / "article_outlines_bilingual.json"
with open(outlines_path, 'r', encoding='utf-8') as f:
    outlines_data = json.load(f)

# 載入已生成的文章（前 5 個區塊）
article_path = config.data_dir / "final_article.md"
if article_path.exists():
    with open(article_path, 'r', encoding='utf-8') as f:
        article_content = f.read()

    # 提取前 5 個區塊（Quick Summary 到 Maintenance）
    # 假設 FAQ 區塊在 "## 常見問題" 之後
    if "## 常見問題" in article_content:
        previous_blocks = article_content.split("## 常見問題")[0]
    else:
        previous_blocks = article_content
else:
    previous_blocks = ""
    print("⚠️ 找不到 final_article.md，無法分析與前 5 個區塊的相似度")

settings = load_config()

print(f"✅ 載入了 {len(outlines_data['outlines'])} 個查詢大綱")

# ================================================
# 2️⃣ 計算 PAA 頻率
# ================================================
print("\n" + "=" * 60)
print("📈 PAA 頻率分析")
print("=" * 60)

paa_frequency = {}

for outline_item in outlines_data["outlines"]:
    for paa in outline_item.get("paa_questions", []):
        q_text = paa.get("question", "") if isinstance(paa, dict) else paa

        if q_text:
            if q_text not in paa_frequency:
                # 自動檢測語言
                is_english = bool(re.search(r'[a-zA-Z]{3,}', q_text))

                paa_frequency[q_text] = {
                    "question": q_text,
                    "frequency": 0,
                    "lang": "en" if is_english else "zh-TW"
                }
            paa_frequency[q_text]["frequency"] += 1

paa_candidates = list(paa_frequency.values())

# 動態計算閾值（與 stage4 相同邏輯）
freq_distribution = [p["frequency"] for p in paa_candidates]
max_freq = max(freq_distribution)
median_freq = sorted(freq_distribution)[len(freq_distribution) // 2]

high_threshold = max(3, median_freq + 1)
medium_threshold = max(2, median_freq)

# 分層統計
high_freq_questions = []
medium_freq_questions = []
low_freq_questions = []

for paa in paa_candidates:
    freq = paa["frequency"]

    if freq >= high_threshold:
        paa["tier"] = "high"
        paa["base_score"] = 15.0
        high_freq_questions.append(paa)
    elif freq >= medium_threshold:
        paa["tier"] = "medium"
        paa["base_score"] = 12.0
        medium_freq_questions.append(paa)
    else:
        paa["tier"] = "low"
        paa["base_score"] = 8.0
        low_freq_questions.append(paa)

print(f"\n✅ 總共 {len(paa_candidates)} 個不重複 PAA 問題")
print(f"📈 頻率範圍：{min(freq_distribution)}-{max_freq} 次")
print(f"📊 中位數：{median_freq}")
print(f"🎯 動態閾值：高頻 ≥{high_threshold}, 中頻 ≥{medium_threshold}")
print(f"\n📊 分層統計：")
print(f"   - 高頻（base_score=15）：{len(high_freq_questions)} 個")
print(f"   - 中頻（base_score=12）：{len(medium_freq_questions)} 個")
print(f"   - 低頻（base_score=8）：{len(low_freq_questions)} 個")

# 顯示前 10 高頻問題
paa_candidates.sort(key=lambda x: x["frequency"], reverse=True)
print(f"\n🏆 前 10 高頻 PAA 問題：")
for i, paa in enumerate(paa_candidates[:10], 1):
    print(f"   {i}. [{paa['lang']}] (頻率 {paa['frequency']}, tier: {paa['tier']}) {paa['question'][:70]}...")

# ================================================
# 3️⃣ 語言分佈
# ================================================
print("\n" + "=" * 60)
print("🌐 語言分佈分析")
print("=" * 60)

zh_questions = [p for p in paa_candidates if p['lang'] == 'zh-TW']
en_questions = [p for p in paa_candidates if p['lang'] == 'en']

print(f"\n語言分佈：")
print(f"   - 中文：{len(zh_questions)} 個 ({len(zh_questions)/len(paa_candidates)*100:.1f}%)")
print(f"   - 英文：{len(en_questions)} 個 ({len(en_questions)/len(paa_candidates)*100:.1f}%)")

# 按頻率層級分語言
zh_high = [p for p in zh_questions if p['tier'] == 'high']
zh_medium = [p for p in zh_questions if p['tier'] == 'medium']
zh_low = [p for p in zh_questions if p['tier'] == 'low']

en_high = [p for p in en_questions if p['tier'] == 'high']
en_medium = [p for p in en_questions if p['tier'] == 'medium']
en_low = [p for p in en_questions if p['tier'] == 'low']

print(f"\n中文問題分佈：")
print(f"   - 高頻：{len(zh_high)} 個")
print(f"   - 中頻：{len(zh_medium)} 個")
print(f"   - 低頻：{len(zh_low)} 個")

print(f"\n英文問題分佈：")
print(f"   - 高頻：{len(en_high)} 個")
print(f"   - 中頻：{len(en_medium)} 個")
print(f"   - 低頻：{len(en_low)} 個")

# ================================================
# 4️⃣ 問題類型分類（用 LLM）
# ================================================
print("\n" + "=" * 60)
print("🔍 問題類型分析（用 LLM 自動分類）")
print("=" * 60)

client = OpenAI(api_key=config.get_openai_key())

def classify_question_type(question: str) -> str:
    """用 GPT-4o-mini 分類問題類型"""
    prompt = f"""請將以下問題分類為以下 5 種類型之一：

問題：{question}

類型選項：
1. How（操作方法）：如何使用、如何操作、怎麼做
2. Troubleshooting（故障排除）：問題診斷、錯誤處理、故障修復
3. Specification（規格選擇）：規格、參數、溫度、壓力、尺寸
4. Safety（安全注意）：安全事項、注意事項、風險、預防
5. Comparison（比較差異）：比較、差異、不同、區別、優缺點

只輸出類型名稱（How / Troubleshooting / Specification / Safety / Comparison），不要任何說明。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=10
        )

        result = response.choices[0].message.content.strip()
        # 標準化輸出
        if "how" in result.lower():
            return "How"
        elif "troubleshoot" in result.lower():
            return "Troubleshooting"
        elif "specification" in result.lower():
            return "Specification"
        elif "safety" in result.lower():
            return "Safety"
        elif "comparison" in result.lower():
            return "Comparison"
        else:
            return "Other"
    except Exception as e:
        print(f"   ⚠️ 分類失敗：{e}")
        return "Unknown"

print(f"\n開始分類 {len(paa_candidates)} 個問題...")
print(f"（這可能需要幾分鐘，使用 gpt-4o-mini）")

type_distribution = {
    "How": [],
    "Troubleshooting": [],
    "Specification": [],
    "Safety": [],
    "Comparison": [],
    "Other": []
}

for i, paa in enumerate(paa_candidates, 1):
    q_type = classify_question_type(paa['question'])
    paa['type'] = q_type
    type_distribution[q_type].append(paa)

    if i % 20 == 0:
        print(f"   進度：{i}/{len(paa_candidates)}")

print(f"\n✅ 分類完成！")
print(f"\n📊 問題類型分佈：")
for q_type, questions in type_distribution.items():
    if questions:
        print(f"   - {q_type}：{len(questions)} 個 ({len(questions)/len(paa_candidates)*100:.1f}%)")
        # 顯示該類型的前 3 個問題
        print(f"      範例：")
        for j, q in enumerate(questions[:3], 1):
            print(f"         {j}. [{q['lang']}] (頻率 {q['frequency']}) {q['question'][:50]}...")

# ================================================
# 5️⃣ 與前 5 個區塊的相似度分析
# ================================================
if previous_blocks:
    print("\n" + "=" * 60)
    print("🚫 與前 5 個區塊重複度分析")
    print("=" * 60)

    # 將前 5 個區塊拆成句子
    sentences = re.split(r'[。！？\n]', previous_blocks)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    print(f"\n前 5 個區塊句子數：{len(sentences)} 個")

    # 計算 Embedding
    questions = [p["question"] for p in paa_candidates]
    all_texts = questions + sentences

    print(f"計算 {len(all_texts)} 個文本的 Embeddings...")

    try:
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=all_texts
        )
        embeddings = [item.embedding for item in response.data]

        question_embeddings = embeddings[:len(questions)]
        sentence_embeddings = embeddings[len(questions):]

        print(f"✅ Embedding 計算完成")

        # 計算每個問題與前面區塊的最大相似度
        import numpy as np

        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        for i, paa in enumerate(paa_candidates):
            max_similarity = 0

            for sent_emb in sentence_embeddings:
                similarity = cosine_similarity(question_embeddings[i], sent_emb)
                max_similarity = max(max_similarity, similarity)

            paa['max_similarity'] = max_similarity

        # 統計相似度分佈（threshold=0.7）
        threshold = 0.7
        would_be_filtered = [p for p in paa_candidates if p['max_similarity'] >= threshold]
        would_pass = [p for p in paa_candidates if p['max_similarity'] < threshold]

        print(f"\n📊 相似度分佈（threshold={threshold}）：")
        print(f"   - 會被過濾（≥{threshold}）：{len(would_be_filtered)} 個 ({len(would_be_filtered)/len(paa_candidates)*100:.1f}%)")
        print(f"   - 會通過（<{threshold}）：{len(would_pass)} 個 ({len(would_pass)/len(paa_candidates)*100:.1f}%)")

        # 顯示會被過濾的高頻問題（這些很可惜）
        high_freq_filtered = [p for p in would_be_filtered if p['tier'] == 'high']
        if high_freq_filtered:
            print(f"\n⚠️ 會被過濾的高頻問題（{len(high_freq_filtered)} 個）：")
            for i, paa in enumerate(high_freq_filtered[:5], 1):
                print(f"   {i}. (頻率 {paa['frequency']}, 相似度 {paa['max_similarity']:.2f}) {paa['question'][:60]}...")

        # 顯示會通過的高頻問題（這些是好候選）
        high_freq_pass = [p for p in would_pass if p['tier'] == 'high']
        if high_freq_pass:
            print(f"\n✅ 會通過的高頻問題（{len(high_freq_pass)} 個）：")
            high_freq_pass.sort(key=lambda x: x['frequency'], reverse=True)
            for i, paa in enumerate(high_freq_pass[:10], 1):
                print(f"   {i}. (頻率 {paa['frequency']}, 相似度 {paa['max_similarity']:.2f}, {paa['type']}) {paa['question'][:60]}...")

    except Exception as e:
        print(f"❌ Embedding 計算失敗：{e}")

# ================================================
# 6️⃣ 最終候選池預測
# ================================================
print("\n" + "=" * 60)
print("🎯 最終候選池預測（基於你的策略）")
print("=" * 60)

print(f"\n你的策略：")
print(f"   1️⃣ 主題新穎性（最重要）：絕對不能與前 5 個區塊重複（threshold=0.7）")
print(f"   2️⃣ 頻率（Google 認為重要）：高頻 PAA 優先")
print(f"   3️⃣ 實用性（LLM 覺得重要）：問題完整且符合用戶需求")

if previous_blocks:
    # 過濾與前 5 個區塊重複的問題
    final_candidates = [p for p in paa_candidates if p.get('max_similarity', 0) < 0.7]

    print(f"\n📊 候選池狀態：")
    print(f"   - 原始 PAA 問題：{len(paa_candidates)} 個")
    print(f"   - 過濾重複後：{len(final_candidates)} 個")

    # 按頻率排序
    final_candidates.sort(key=lambda x: x['frequency'], reverse=True)

    print(f"\n🏆 預測的前 10 個 FAQ 問題（按頻率排序）：")
    for i, paa in enumerate(final_candidates[:10], 1):
        print(f"\n   {i}. [{paa['lang']}] (頻率 {paa['frequency']}, {paa['type']}, base_score {paa['base_score']:.1f})")
        print(f"      {paa['question']}")
        print(f"      相似度: {paa.get('max_similarity', 0):.2f}")
else:
    print(f"\n⚠️ 無法預測最終候選池（缺少前 5 個區塊資料）")

# ================================================
# 7️⃣ 儲存分析結果
# ================================================
print("\n" + "=" * 60)
print("💾 儲存分析結果")
print("=" * 60)

output_path = config.data_dir / "paa_distribution_analysis.json"

analysis_result = {
    "total_paa_questions": len(paa_candidates),
    "frequency_distribution": {
        "max": max_freq,
        "median": median_freq,
        "high_threshold": high_threshold,
        "medium_threshold": medium_threshold,
        "high_freq_count": len(high_freq_questions),
        "medium_freq_count": len(medium_freq_questions),
        "low_freq_count": len(low_freq_questions)
    },
    "language_distribution": {
        "zh_TW": len(zh_questions),
        "en": len(en_questions),
        "zh_TW_percentage": len(zh_questions)/len(paa_candidates)*100,
        "en_percentage": len(en_questions)/len(paa_candidates)*100
    },
    "type_distribution": {
        q_type: len(questions) for q_type, questions in type_distribution.items()
    },
    "similarity_analysis": {
        "threshold": 0.7,
        "would_be_filtered": len(would_be_filtered) if previous_blocks else None,
        "would_pass": len(would_pass) if previous_blocks else None
    } if previous_blocks else None,
    "top_10_predicted": [
        {
            "question": p['question'],
            "frequency": p['frequency'],
            "lang": p['lang'],
            "type": p.get('type', 'Unknown'),
            "tier": p['tier'],
            "base_score": p['base_score'],
            "max_similarity": p.get('max_similarity', 0)
        }
        for p in (final_candidates[:10] if previous_blocks else paa_candidates[:10])
    ],
    "all_paa_questions": [
        {
            "question": p['question'],
            "frequency": p['frequency'],
            "lang": p['lang'],
            "type": p.get('type', 'Unknown'),
            "tier": p['tier'],
            "base_score": p['base_score'],
            "max_similarity": p.get('max_similarity', 0)
        }
        for p in paa_candidates
    ]
}

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(analysis_result, f, ensure_ascii=False, indent=2)

print(f"\n✅ 分析結果已儲存至：{output_path}")

print("\n" + "=" * 60)
print("🎉 分析完成！")
print("=" * 60)
