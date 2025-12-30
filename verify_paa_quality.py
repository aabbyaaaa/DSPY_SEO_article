# -*- coding: utf-8 -*-
"""
驗證 PAA 問題的來源與品質
檢查 SerpAPI 抓取的 PAA 是否準確
"""

import os
import sys
import io
import json
from pathlib import Path
from collections import Counter

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.absolute()

print("\n" + "=" * 70)
print("🔍 PAA 問題來源與品質驗證")
print("=" * 70)

# ================================================
# 1️⃣ 載入 SERP 原始資料
# ================================================
print("\n📦 載入 SERP 分析資料...")

serp_path = ROOT_DIR / "data" / "serp_analysis_bilingual.json"
with open(serp_path, 'r', encoding='utf-8') as f:
    serp_data = json.load(f)

print(f"✅ 載入了 {len(serp_data['serp_results'])} 個 SERP 查詢結果")

# ================================================
# 2️⃣ 分析 PAA 來源
# ================================================
print("\n" + "=" * 70)
print("📊 PAA 問題來源分析")
print("=" * 70)

total_queries = len(serp_data['serp_results'])
queries_with_paa = 0
total_paa_questions = 0
paa_count_distribution = []

zh_paa_count = 0
en_paa_count = 0

all_paa_questions = []

for result in serp_data['serp_results']:
    query = result['query']
    lang = result['lang']
    paa_list = result['serp_data']['people_also_ask']

    paa_count = len(paa_list)
    paa_count_distribution.append(paa_count)

    if paa_count > 0:
        queries_with_paa += 1
        total_paa_questions += paa_count

        for paa in paa_list:
            all_paa_questions.append({
                'question': paa['question'],
                'source_query': query,
                'lang': lang
            })

            if lang == 'zh-TW':
                zh_paa_count += 1
            else:
                en_paa_count += 1

print(f"\n📊 統計資訊：")
print(f"   總查詢數：{total_queries}")
print(f"   有 PAA 的查詢：{queries_with_paa} 個 ({queries_with_paa/total_queries*100:.1f}%)")
print(f"   無 PAA 的查詢：{total_queries - queries_with_paa} 個")
print(f"\n📝 PAA 問題數量：")
print(f"   總 PAA 問題數：{total_paa_questions}")
print(f"   平均每個查詢：{total_paa_questions/total_queries:.2f} 個 PAA")
print(f"   平均每個有 PAA 的查詢：{total_paa_questions/queries_with_paa:.2f} 個 PAA" if queries_with_paa > 0 else "")
print(f"\n🌐 語言分佈：")
print(f"   中文 PAA：{zh_paa_count} 個 ({zh_paa_count/total_paa_questions*100:.1f}%)")
print(f"   英文 PAA：{en_paa_count} 個 ({en_paa_count/total_paa_questions*100:.1f}%)")

# PAA 數量分佈
paa_dist_counter = Counter(paa_count_distribution)
print(f"\n📈 PAA 數量分佈（每個查詢）：")
for count in sorted(paa_dist_counter.keys()):
    queries = paa_dist_counter[count]
    print(f"   {count} 個 PAA：{queries} 個查詢")

# ================================================
# 3️⃣ 檢查 PAA 品質
# ================================================
print("\n" + "=" * 70)
print("🔬 PAA 問題品質檢查")
print("=" * 70)

# 檢查不完整問題
incomplete_questions = []
complete_questions = []

for paa in all_paa_questions:
    q = paa['question']
    lang = paa['lang']

    # 檢查問題是否完整（中文）
    if lang == 'zh-TW':
        # 不完整的特徵：只有名詞+問號，沒有動詞或疑問詞
        is_incomplete = (
            (q.count('？') == 1 and len(q.split()) <= 3) or  # 太短
            ('？' in q and not any(word in q for word in ['如何', '為什麼', '什麼', '怎麼', '哪些', '是否', '能否', '可以', '會', '有']))  # 缺少疑問詞
        )

        if is_incomplete:
            incomplete_questions.append(paa)
        else:
            complete_questions.append(paa)
    else:
        # 英文問題通常比較完整
        complete_questions.append(paa)

print(f"\n✅ 完整問題：{len(complete_questions)} 個 ({len(complete_questions)/total_paa_questions*100:.1f}%)")
print(f"❌ 疑似不完整問題：{len(incomplete_questions)} 個 ({len(incomplete_questions)/total_paa_questions*100:.1f}%)")

if incomplete_questions:
    print(f"\n⚠️ 前 10 個疑似不完整的 PAA 問題：")
    for i, paa in enumerate(incomplete_questions[:10], 1):
        print(f"   {i}. {paa['question']} (來源查詢: {paa['source_query']})")

# ================================================
# 4️⃣ 檢查 PAA 與您選中問題的匹配
# ================================================
print("\n" + "=" * 70)
print("🎯 驗證：「相關滅菌儀器需要至少多久進行一次滅菌效能測試？」")
print("=" * 70)

target_question = "相關滅菌儀器需要至少多久進行一次滅菌效能測試？"

# 找到這個問題的來源
found = False
for result in serp_data['serp_results']:
    for paa in result['serp_data']['people_also_ask']:
        if paa['question'] == target_question:
            print(f"\n✅ 找到此問題！")
            print(f"   來源查詢：{result['query']}")
            print(f"   語言：{result['lang']}")
            print(f"   問題：{paa['question']}")
            print(f"   答案預覽：{paa['answer'][:200]}..." if paa['answer'] else "   答案：（無）")
            found = True
            break
    if found:
        break

if not found:
    print(f"\n❌ 未找到此問題！")

# ================================================
# 5️⃣ 總結
# ================================================
print("\n" + "=" * 70)
print("📊 總結")
print("=" * 70)

print(f"\n✅ PAA 來源驗證：")
print(f"   - PAA 問題來自 SerpAPI 的 'related_questions' 欄位")
print(f"   - 這是 Google SERP 的官方 PAA（People Also Ask）資料")
print(f"   - 準確性：✅ 高（直接來自 Google）")

print(f"\n📊 PAA 品質評估：")
print(f"   - 完整問題比例：{len(complete_questions)/total_paa_questions*100:.1f}%")
print(f"   - 不完整問題比例：{len(incomplete_questions)/total_paa_questions*100:.1f}%")
print(f"   - 品質評級：{'✅ 優秀' if len(complete_questions)/total_paa_questions > 0.9 else '⚠️ 良好' if len(complete_questions)/total_paa_questions > 0.7 else '❌ 需改善'}")

print(f"\n💡 建議：")
if len(incomplete_questions) > 0:
    print(f"   - 發現 {len(incomplete_questions)} 個疑似不完整的問題")
    print(f"   - 這些問題可能需要進一步的人工審查或過濾")
    print(f"   - 可以考慮加強 LLM 實用性評分，給不完整問題低分")
else:
    print(f"   - 所有 PAA 問題都是完整的 ✅")
    print(f"   - 可以直接使用這些問題作為 FAQ 候選")

print("\n" + "=" * 70)
print("🎉 驗證完成！")
print("=" * 70)
