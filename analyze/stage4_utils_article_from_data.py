# -*- coding: utf-8 -*-
"""
根據抓取的內容生成專業 SEO 文章
"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

# 讀取抓取的內容
data_path = config.data_dir / "extracted_content_top_queries_3.8.json"
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 篩選與主題相關的中文頁面
target_keywords = ["高壓滅菌", "滅菌鍋", "滅菌釜", "故障", "排查"]
target_pages = []

for page in data["pages"]:
    if page["lang"] == "zh-TW":
        query = page["query"]
        if any(kw in query for kw in target_keywords):
            target_pages.append(page)

print(f"找到 {len(target_pages)} 個相關中文頁面")
print(f"\n相關查詢詞:")
for i, page in enumerate(target_pages[:10], 1):
    print(f"{i}. {page['query']} (評分: {page['query_score']}, 品質: {page['quality_score']})")

# 統計來源
sources = {}
for page in target_pages:
    domain = page['url'].split('/')[2] if '/' in page['url'] else page['url']
    if domain not in sources:
        sources[domain] = []
    sources[domain].append({
        'title': page['title'],
        'url': page['url'],
        'query': page['query']
    })

print(f"\n\n內容來源統計:")
for domain, pages in sorted(sources.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"\n{domain}: {len(pages)} 篇")
    for p in pages[:2]:
        print(f"  - {p['title'][:50]}...")
