# -*- coding: utf-8 -*-
"""
LLM-SEO Pipeline Stage ③: DSPy Analysis Runner (v2.0 - Bilingual with Full Content)
------------------------------------------------------------------------------------
執行 DSPy 分析，使用完整頁面內容而非僅 SERP snippets

特點：
1. 支援雙語（繁體中文 + 英文）
2. 使用 Tavily 提取的完整頁面內容
3. 為每個查詢生成文章大綱

輸入：
- data/serp_analysis_bilingual.json
- data/extracted_content_60_pages.json

輸出：
- data/article_outlines_bilingual.json
"""

import os, json, sys, io
from pathlib import Path
from tqdm import tqdm

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config
from analyze.dspy_modules import (
    ContentSummarizer,
    GapAnalyzer,
    OutlineGenerator,
    init_dspy
)

# ================================================
# 初始化
# ================================================
print("\n" + "=" * 60)
print("🚀 DSPy 雙語分析模組 - Stage ③ (v2.0)")
print("=" * 60)
print(f"中文主題：{config.topic}")
print(f"英文主題：{config.topic_en}")
print(f"DSPy 主模型：{config.dspy_model_main}")
print(f"DSPy 小模型：{config.dspy_model_small}")

# 初始化 DSPy
openai_key = config.get_openai_key()
init_dspy(config.dspy_model_main, openai_key)

# 初始化三個模組
print("\n📦 初始化 DSPy 模組...")
summarizer = ContentSummarizer()
gap_analyzer = GapAnalyzer()
outline_generator = OutlineGenerator(block_config=config.article_blocks)

print("✅ 模組初始化完成")

# ================================================
# 載入資料
# ================================================

# 1. SERP 分析資料
serp_path = config.data_dir / "serp_analysis_bilingual.json"
if not serp_path.exists():
    raise FileNotFoundError(f"❌ 找不到 {serp_path}，請先執行 analyze/serp_fetcher_bilingual.py")

print(f"\n📖 載入 SERP 資料：{serp_path}")
with open(serp_path, "r", encoding="utf-8") as f:
    serp_data = json.load(f)

# 2. 提取的完整內容
content_path = config.data_dir / "extracted_content_60_pages.json"
if not content_path.exists():
    raise FileNotFoundError(f"❌ 找不到 {content_path}，請先執行 analyze/content_extractor.py")

print(f"📖 載入提取的頁面內容：{content_path}")
with open(content_path, "r", encoding="utf-8") as f:
    content_data = json.load(f)

query_count = len(serp_data["serp_results"])
page_count = len(content_data["pages"])

print(f"✅ 載入 {query_count} 條查詢的 SERP 資料")
print(f"✅ 載入 {page_count} 個頁面的完整內容")

# ================================================
# 建立查詢 -> 內容的映射
# ================================================

print("\n🔗 建立查詢與內容的映射...")
query_content_map = {}

for page in content_data["pages"]:
    query = page["query"]
    if query not in query_content_map:
        query_content_map[query] = []
    query_content_map[query].append(page)

print(f"✅ {len(query_content_map)} 個查詢有對應的內容")

# ================================================
# 處理每個查詢
# ================================================
results = []

print("\n" + "=" * 60)
print("🔄 開始處理查詢...")
print("=" * 60)

for idx, item in enumerate(tqdm(serp_data["serp_results"], desc="DSPy 分析"), 1):
    query = item["query"]
    lang = item["lang"]
    serp = item["serp_data"]
    analysis = item["analysis"]

    lang_label = "繁中" if lang == "zh-TW" else "英文"
    print(f"\n[{idx}/{query_count}] ({lang_label}) {query}")

    # ------------------------------------------------
    # Step 1️⃣: ContentSummarizer
    # ------------------------------------------------
    print("  📝 Step 1: 總結競爭者內容...")
    organic_results = serp.get("organic_results", [])

    if not organic_results:
        print("  ⚠️ 無有機結果，跳過")
        continue

    # 增強 organic_results：如果有完整內容，加入摘要
    pages = query_content_map.get(query, [])

    # 為每個 organic result 添加完整內容（如果有的話）
    for result in organic_results:
        result_url = result.get("link", "")
        # 尋找對應的完整頁面內容
        matching_page = next((p for p in pages if p["url"] == result_url), None)
        if matching_page:
            # 截取前 500 字作為增強的 snippet
            content_preview = matching_page["content"][:500]
            result["enhanced_snippet"] = f"{result.get('snippet', '')} [完整內容預覽: {content_preview}...]"
        else:
            result["enhanced_snippet"] = result.get("snippet", "")

    try:
        summaries = summarizer.forward(query, organic_results)
        print(f"  ✅ 總結完成：{len(summaries)} 個競爭者")
    except Exception as e:
        print(f"  ❌ ContentSummarizer 失敗：{e}")
        continue

    # ------------------------------------------------
    # Step 2️⃣: GapAnalyzer
    # ------------------------------------------------
    print("  🔍 Step 2: 分析內容缺口...")
    paa_questions = serp.get("people_also_ask", [])
    # AIO (Google AI Overview) 檢測
    aio_triggered = analysis.get("aio_triggered", analysis.get("aiseo_triggered", False))

    try:
        gaps = gap_analyzer.forward(
            query=query,
            competitor_summaries=summaries,
            paa_questions=paa_questions,
            aiseo_triggered=aio_triggered  # 傳入 AIO 狀態
        )
        print(f"  ✅ 缺口分析完成：找到 {len(gaps)} 個機會")

        # 顯示前 3 個缺口
        for i, gap in enumerate(gaps[:3], 1):
            gap_desc = gap.description[:50] if len(gap.description) > 50 else gap.description
            print(f"     {i}. [{gap.gap_type}] {gap_desc}... (分數: {gap.opportunity_score:.2f})")

    except Exception as e:
        print(f"  ❌ GapAnalyzer 失敗：{e}")
        gaps = []

    # ------------------------------------------------
    # Step 3️⃣: OutlineGenerator
    # ------------------------------------------------
    print("  📋 Step 3: 生成文章大綱...")

    try:
        outline = outline_generator.forward(
            query=query,
            content_gaps=gaps,
            paa_questions=paa_questions,
            aiseo_triggered=aio_triggered  # 傳入 AIO 狀態
        )
        print(f"  ✅ 大綱生成完成")

        # 顯示區塊結構
        if "blocks" in outline:
            print(f"     結構：{len(outline['blocks'])} 個區塊")
            for block in outline["blocks"]:
                print(f"       - {block.get('block_name', 'N/A')}: {block.get('word_count_target', 'N/A')} 字")

    except Exception as e:
        print(f"  ❌ OutlineGenerator 失敗：{e}")
        outline = outline_generator._default_outline(query)

    # ------------------------------------------------
    # 儲存結果
    # ------------------------------------------------
    results.append({
        "query": query,
        "lang": lang,
        "aio_triggered": aio_triggered,  # AIO (Google AI Overview)
        "aiseo_triggered": aio_triggered,  # 保留向後兼容
        "competitor_summaries": [s.model_dump() for s in summaries],
        "content_gaps": [g.model_dump() for g in gaps],
        "outline": outline,
        "paa_questions": paa_questions,
        "related_searches": serp.get("related_searches", []),
        "extracted_pages": [
            {
                "url": p["url"],
                "title": p["title"],
                "content_length": len(p["content"])
            }
            for p in pages
        ]
    })

# ================================================
# 輸出最終結果
# ================================================
output_path = config.data_dir / "article_outlines_bilingual.json"

# 計算統計
total_gaps = sum(len(r["content_gaps"]) for r in results)
avg_gaps = total_gaps / len(results) if results else 0
aio_coverage = sum(r["aio_triggered"] for r in results) / len(results) if results else 0
aiseo_coverage = aio_coverage  # 保留向後兼容

zh_results = [r for r in results if r["lang"] == "zh-TW"]
en_results = [r for r in results if r["lang"] == "en"]

with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
        "topic_zh": config.topic,
        "topic_en": config.topic_en,
        "query_count": len(results),
        "zh_count": len(zh_results),
        "en_count": len(en_results),
        "outlines": results,
        "summary": {
            "total_gaps_found": total_gaps,
            "avg_gaps_per_query": avg_gaps,
            "aio_coverage": aio_coverage,  # AIO (Google AI Overview)
            "zh_aio_rate": sum(r["aio_triggered"] for r in zh_results) / len(zh_results) if zh_results else 0,
            "en_aio_rate": sum(r["aio_triggered"] for r in en_results) / len(en_results) if en_results else 0,
            # 保留舊欄位以向後兼容
            "aiseo_coverage": aiseo_coverage,
            "zh_aiseo_rate": sum(r["aiseo_triggered"] for r in zh_results) / len(zh_results) if zh_results else 0,
            "en_aiseo_rate": sum(r["aiseo_triggered"] for r in en_results) / len(en_results) if en_results else 0
        }
    }, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("✅ DSPy 雙語分析完成！")
print("=" * 60)
print(f"📁 輸出檔案：{output_path}")
print(f"\n📊 處理統計：")
print(f"   總查詢數：{len(results)}")
print(f"   繁體中文：{len(zh_results)}")
print(f"   English：{len(en_results)}")
print(f"\n🎯 內容缺口：")
print(f"   總缺口數：{total_gaps}")
print(f"   平均缺口/查詢：{avg_gaps:.1f}")
print(f"\n🤖 AIO (Google AI Overview) 覆蓋率：")
print(f"   整體：{aio_coverage:.1%}")
print(f"   中文：{sum(r['aio_triggered'] for r in zh_results) / len(zh_results):.1%}" if zh_results else "   中文：N/A")
print(f"   英文：{sum(r['aio_triggered'] for r in en_results) / len(en_results):.1%}" if en_results else "   英文：N/A")
print("\n🎉 準備進入 Stage ④：文章生成")
print("=" * 60 + "\n")
