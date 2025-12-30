# -*- coding: utf-8 -*-
"""
分析 FAQ 問題來源
檢查規則式提取能提取多少問題
"""

import os
import sys
import io
import json
import re
from pathlib import Path

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄
ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

print("\n" + "=" * 60)
print("📊 FAQ 問題來源分析")
print("=" * 60)

# ================================================
# 1️⃣ 載入資料
# ================================================
print("\n📦 載入資料...")

# cache_extracted_content.json
content_path = ROOT_DIR / "data" / "cache_extracted_content.json"
with open(content_path, 'r', encoding='utf-8') as f:
    content_data_raw = json.load(f)

# article_outlines_bilingual.json
outlines_path = ROOT_DIR / "data" / "article_outlines_bilingual.json"
with open(outlines_path, 'r', encoding='utf-8') as f:
    outlines_data = json.load(f)

# 將 content_data 轉換為統一格式
all_pages = []
for lang_key, pages_list in content_data_raw.items():
    if isinstance(pages_list, list):
        all_pages.extend(pages_list)

print(f"✅ 載入了 {len(all_pages)} 個頁面")
print(f"✅ 載入了 {len(outlines_data['outlines'])} 個查詢大綱")

# ================================================
# 2️⃣ 分析 Extracted Content
# ================================================
print("\n" + "=" * 60)
print("📄 Extracted Content 分析")
print("=" * 60)

# 語言分佈
lang_dist = {}
quality_by_lang = {"zh-TW": [], "en": []}

for page in all_pages:
    lang = page.get('lang', 'unknown')
    quality = page.get('quality_score', 0)

    lang_dist[lang] = lang_dist.get(lang, 0) + 1
    if lang in quality_by_lang:
        quality_by_lang[lang].append(quality)

print(f"\n語言分佈：")
for lang, count in lang_dist.items():
    avg_quality = sum(quality_by_lang.get(lang, [0])) / len(quality_by_lang.get(lang, [1]))
    print(f"  - {lang}: {count} 頁 (平均 quality_score: {avg_quality:.2f})")

# ================================================
# 3️⃣ 規則式提取測試（中文）
# ================================================
print("\n" + "=" * 60)
print("🔍 規則式提取測試（中文）")
print("=" * 60)

patterns_zh = [
    (r"(為什麼[^？\n]{5,50}？)", "why"),
    (r"(如何[^？\n]{5,50}？)", "how"),
    (r"(什麼是[^？\n]{5,50}？)", "what"),
    (r"([^？\n]{5,50}嗎？)", "yes_no"),
    (r"Q[:：]\s*([^？\n]+？)", "faq"),
    (r"問[:：]\s*([^？\n]+？)", "faq"),
]

extracted_zh = []

for page in all_pages:
    if page.get('lang') != 'zh-TW':
        continue

    content = page['content']
    quality = page.get('quality_score', 0.5)

    for pattern, q_type in patterns_zh:
        matches = re.findall(pattern, content)
        for match in matches:
            question_text = match.strip()
            if 10 < len(question_text) < 100:
                extracted_zh.append({
                    "question": question_text,
                    "type": q_type,
                    "quality_score": quality,
                    "source_url": page['url'][:60] + "..."
                })

print(f"✅ 提取到 {len(extracted_zh)} 個中文問題")

# 顯示前 10 個（按 quality_score 排序）
extracted_zh.sort(key=lambda x: x['quality_score'], reverse=True)
print(f"\n前 10 個高品質中文問題：")
for i, q in enumerate(extracted_zh[:10], 1):
    print(f"\n  [{i}] ({q['type']}, quality: {q['quality_score']:.2f})")
    print(f"      {q['question']}")
    print(f"      來源: {q['source_url']}")

# ================================================
# 4️⃣ 規則式提取測試（英文）
# ================================================
print("\n" + "=" * 60)
print("🔍 規則式提取測試（英文）")
print("=" * 60)

patterns_en = [
    (r"(Why [^?\n]{10,80}\?)", "why"),
    (r"(How [^?\n]{10,80}\?)", "how"),
    (r"(What is [^?\n]{10,80}\?)", "what"),
    (r"(Can [^?\n]{10,80}\?)", "yes_no"),
    (r"Q[:]\s*([^?\n]+\?)", "faq"),
]

extracted_en = []

for page in all_pages:
    if page.get('lang') != 'en':
        continue

    content = page['content']
    quality = page.get('quality_score', 0.5)

    for pattern, q_type in patterns_en:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            question_text = match.strip()
            if 10 < len(question_text) < 100:
                extracted_en.append({
                    "question": question_text,
                    "type": q_type,
                    "quality_score": quality,
                    "source_url": page['url'][:60] + "..."
                })

print(f"✅ 提取到 {len(extracted_en)} 個英文問題")

# 顯示前 10 個（按 quality_score 排序）
extracted_en.sort(key=lambda x: x['quality_score'], reverse=True)
print(f"\n前 10 個高品質英文問題：")
for i, q in enumerate(extracted_en[:10], 1):
    print(f"\n  [{i}] ({q['type']}, quality: {q['quality_score']:.2f})")
    print(f"      {q['question']}")
    print(f"      來源: {q['source_url']}")

# ================================================
# 5️⃣ PAA 問題統計
# ================================================
print("\n" + "=" * 60)
print("📝 PAA 問題統計")
print("=" * 60)

paa_frequency = {}

for outline_item in outlines_data["outlines"]:
    for paa in outline_item.get("paa_questions", []):
        q_text = paa.get("question", "") if isinstance(paa, dict) else paa

        if q_text:
            if q_text not in paa_frequency:
                paa_frequency[q_text] = {
                    "question": q_text,
                    "frequency": 0
                }
            paa_frequency[q_text]["frequency"] += 1

paa_candidates = list(paa_frequency.values())
paa_candidates.sort(key=lambda x: x["frequency"], reverse=True)

print(f"✅ 收集到 {len(paa_candidates)} 個不重複的 PAA 問題")
print(f"\n前 15 個高頻 PAA 問題：")
for i, paa in enumerate(paa_candidates[:15], 1):
    print(f"  [{i}] (頻率: {paa['frequency']}) {paa['question']}")

# ================================================
# 6️⃣ 總結
# ================================================
print("\n" + "=" * 60)
print("📊 總結")
print("=" * 60)

print(f"\n候選問題池組成：")
print(f"  - PAA 問題：{len(paa_candidates)} 個")
print(f"  - 規則式提取（中文）：{len(extracted_zh)} 個")
print(f"  - 規則式提取（英文）：{len(extracted_en)} 個")
print(f"  - 總候選池：{len(paa_candidates) + len(extracted_zh) + len(extracted_en)} 個")

print(f"\n品質分佈：")
print(f"  - 中文平均 quality_score: {sum([q['quality_score'] for q in extracted_zh]) / len(extracted_zh) if extracted_zh else 0:.2f}")
print(f"  - 英文平均 quality_score: {sum([q['quality_score'] for q in extracted_en]) / len(extracted_en) if extracted_en else 0:.2f}")

print("\n" + "=" * 60)
print("🎉 分析完成！")
print("=" * 60)
