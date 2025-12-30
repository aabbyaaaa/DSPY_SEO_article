# -*- coding: utf-8 -*-
"""
驗證提取內容的實際主題分布
"""
import json
import sys
import io
from pathlib import Path
from collections import Counter

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

# 讀取提取的內容
data_path = config.data_dir / "extracted_content_top_queries_3.8.json"
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("📊 提取內容主題分析")
print("=" * 80)

# 分析查詢詞主題
zh_pages = [p for p in data["pages"] if p["lang"] == "zh-TW"]
en_pages = [p for p in data["pages"] if p["lang"] == "en"]

print(f"\n總計：{len(data['pages'])} 篇文章")
print(f"中文：{len(zh_pages)} 篇")
print(f"英文：{len(en_pages)} 篇")

# 分析中文查詢詞的主題分布
print("\n" + "=" * 80)
print("🔍 中文查詢詞主題分析")
print("=" * 80)

query_themes = {
    "故障排查": ["故障", "排查", "異常", "問題", "診斷", "排除"],
    "維修保養": ["維修", "保養", "維護", "清潔", "校正"],
    "操作使用": ["使用", "操作", "步驟", "指南", "流程"],
    "選購配件": ["選購", "推薦", "配件", "替代品", "選擇"],
    "原理知識": ["原理", "定義", "什麼是", "如何工作"],
    "測試驗證": ["測試", "驗證", "確效", "監測"],
    "特定故障": ["漏水", "溫度", "壓力", "顯示器", "水位", "密封"]
}

zh_queries = [p["query"] for p in zh_pages]
unique_zh_queries = sorted(set(zh_queries))

print(f"\n📌 去重後的中文查詢詞數：{len(unique_zh_queries)}")

for theme, keywords in query_themes.items():
    matching_queries = [q for q in unique_zh_queries if any(kw in q for kw in keywords)]
    print(f"\n【{theme}】({len(matching_queries)} 個查詢)")
    for q in matching_queries[:10]:  # 顯示前10個
        count = zh_queries.count(q)
        print(f"  • {q} ({count} 篇)")
    if len(matching_queries) > 10:
        print(f"  ... 還有 {len(matching_queries) - 10} 個")

# 分析英文查詢詞
print("\n" + "=" * 80)
print("🔍 英文查詢詞主題分析")
print("=" * 80)

en_queries = [p["query"] for p in en_pages]
unique_en_queries = sorted(set(en_queries))

print(f"\n📌 去重後的英文查詢詞數：{len(unique_en_queries)}")

en_themes = {
    "Troubleshooting": ["troubleshoot", "error", "problem", "issue", "malfunction", "fix"],
    "Maintenance": ["maintenance", "maintain", "service", "clean", "calibrat"],
    "Operation": ["use", "operate", "run", "start", "load"],
    "Validation": ["validat", "test", "verify", "indicator"],
    "Specific Issues": ["seal", "pressure", "temperature", "leak", "door"]
}

for theme, keywords in en_themes.items():
    matching_queries = [q for q in unique_en_queries if any(kw in q.lower() for kw in keywords)]
    print(f"\n【{theme}】({len(matching_queries)} 個查詢)")
    for q in matching_queries[:8]:
        count = en_queries.count(q)
        print(f"  • {q} ({count} 篇)")
    if len(matching_queries) > 8:
        print(f"  ... 還有 {len(matching_queries) - 8} 個")

# 分析文章標題的主題
print("\n" + "=" * 80)
print("📄 文章標題關鍵字分析（中文前20篇）")
print("=" * 80)

for i, page in enumerate(zh_pages[:20], 1):
    title = page.get("title", "")
    query = page.get("query", "")
    url = page.get("url", "")
    quality = page.get("quality_score", 0)
    domain = url.split('/')[2] if '/' in url else url

    print(f"\n{i}. {title[:60]}")
    print(f"   查詢：{query}")
    print(f"   來源：{domain} (品質分數: {quality})")

    # 檢查標題中的關鍵主題
    themes_found = []
    for theme, keywords in query_themes.items():
        if any(kw in title for kw in keywords):
            themes_found.append(theme)
    if themes_found:
        print(f"   主題：{', '.join(themes_found)}")

# 統計內容長度
print("\n" + "=" * 80)
print("📊 內容統計")
print("=" * 80)

zh_lengths = [len(p.get("content", "")) for p in zh_pages]
en_lengths = [len(p.get("content", "")) for p in en_pages]

print(f"\n中文文章平均長度：{sum(zh_lengths) / len(zh_lengths):.0f} 字符")
print(f"英文文章平均長度：{sum(en_lengths) / len(en_lengths):.0f} 字符")

print(f"\n中文內容長度分布：")
print(f"  最短：{min(zh_lengths)} 字符")
print(f"  最長：{max(zh_lengths)} 字符")
print(f"  中位數：{sorted(zh_lengths)[len(zh_lengths)//2]} 字符")

# 分析來源網站
print("\n" + "=" * 80)
print("🌐 內容來源分析（中文）")
print("=" * 80)

domains = [p["url"].split('/')[2] if '/' in p["url"] else p["url"] for p in zh_pages]
domain_counts = Counter(domains)

print(f"\n前15大來源網站：")
for domain, count in domain_counts.most_common(15):
    print(f"  {domain}: {count} 篇")

print("\n" + "=" * 80)
