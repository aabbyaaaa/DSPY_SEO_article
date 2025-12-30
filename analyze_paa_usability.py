# -*- coding: utf-8 -*-
"""
統計 PAA 問題可用性（按頻率層級）
"""

import os
import sys
import io
import json
from pathlib import Path

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.absolute()

# 載入分析結果
with open(ROOT_DIR / "data" / "paa_distribution_analysis.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

# 產品名稱關鍵字
keywords_zh = ['高壓滅菌鍋', '高壓滅菌釜', '高壓消毒鍋', '滅菌鍋', '滅菌釜', '消毒鍋', '高壓滅菌', '高壓蒸氣', '高溫高壓']
keywords_en = ['autoclave', 'autoclaving', 'sterilizer']

def has_product_name(q, lang):
    q_lower = q.lower()
    if lang == 'zh-TW':
        return any(kw in q for kw in keywords_zh)
    else:
        return any(kw in q_lower for kw in keywords_en)

# 統計各頻率層級
stats = {
    'high': {'total': 0, 'has_name': 0, 'pass_sim': 0, 'both': 0, 'questions': []},
    'medium': {'total': 0, 'has_name': 0, 'pass_sim': 0, 'both': 0, 'questions': []},
    'low': {'total': 0, 'has_name': 0, 'pass_sim': 0, 'both': 0, 'questions': []}
}

for paa in data['all_paa_questions']:
    tier = paa['tier']
    has_name = has_product_name(paa['question'], paa['lang'])
    pass_sim = paa['max_similarity'] < 0.7

    stats[tier]['total'] += 1
    if has_name:
        stats[tier]['has_name'] += 1
    if pass_sim:
        stats[tier]['pass_sim'] += 1
    if has_name and pass_sim:
        stats[tier]['both'] += 1
        stats[tier]['questions'].append(paa)

print("\n" + "=" * 70)
print("PAA 問題篩選統計（按頻率層級）")
print("=" * 70)
print()

for tier_name, tier_label in [('high', '高頻 (≥3)'), ('medium', '中頻 (≥2)'), ('low', '低頻 (1)')]:
    s = stats[tier_name]
    print(f'【{tier_label}】')
    print(f'  總數:                {s["total"]} 個')
    print(f'  包含產品名稱:         {s["has_name"]} 個 ({s["has_name"]/s["total"]*100:.1f}%)')
    print(f'  相似度<0.7:          {s["pass_sim"]} 個 ({s["pass_sim"]/s["total"]*100:.1f}%)')
    print(f'  ✅ 兩者都滿足:        {s["both"]} 個 ({s["both"]/s["total"]*100:.1f}%)')
    print()

# 總計
total_both = sum(s['both'] for s in stats.values())
print("=" * 70)
print(f'✅ 總共可用候選（包含產品名稱 + 相似度<0.7）: {total_both} 個 / 127 個')
print("=" * 70)

# 顯示前 15 個可用候選（按頻率排序）
print("\n" + "=" * 70)
print("前 15 個可用候選問題（包含產品名稱 + 相似度<0.7）")
print("=" * 70)

all_usable = []
for tier in ['high', 'medium', 'low']:
    all_usable.extend(stats[tier]['questions'])

# 按頻率排序
all_usable.sort(key=lambda x: x['frequency'], reverse=True)

for i, paa in enumerate(all_usable[:15], 1):
    print(f"\n[{i}] 頻率: {paa['frequency']} | 相似度: {paa['max_similarity']:.3f} | {paa['lang']}")
    print(f"    {paa['question']}")

# 儲存完整可用列表
output_data = {
    "summary": {
        "total_paa": 127,
        "total_usable": total_both,
        "high_freq_usable": stats['high']['both'],
        "medium_freq_usable": stats['medium']['both'],
        "low_freq_usable": stats['low']['both']
    },
    "usable_questions": all_usable
}

output_path = ROOT_DIR / "data" / "paa_usable_candidates.json"
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"\n\n✅ 完整可用候選列表已儲存至：{output_path}")
