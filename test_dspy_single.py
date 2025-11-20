# -*- coding: utf-8 -*-
"""
Test DSPy Analysis with a single query
"""

import os, json, sys, io
from pathlib import Path

# Windows UTF-8 support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config
from analyze.dspy_modules import (
    ContentSummarizer,
    GapAnalyzer,
    OutlineGenerator,
    init_dspy
)

print("\n🧪 DSPy Single Query Test")
print("=" * 60)

# 初始化 DSPy
openai_key = config.get_openai_key()
init_dspy(config.dspy_model_main, openai_key)
print(f"✅ DSPy 初始化完成 (model: {config.dspy_model_main})")

# 初始化模組
summarizer = ContentSummarizer()
gap_analyzer = GapAnalyzer()
outline_generator = OutlineGenerator(block_config=config.article_blocks)
print("✅ 三個模組初始化完成")

# 載入 SERP 數據（只取第一個查詢）
serp_path = config.data_dir / config.output_files["serp_analysis"]
with open(serp_path, "r", encoding="utf-8") as f:
    serp_data = json.load(f)

# 只處理第一個查詢
test_item = serp_data["serp_results"][0]
query = test_item["query"]
serp = test_item["serp_data"]
analysis = test_item["analysis"]

print(f"\n📌 測試查詢：{query}")
print(f"   AISEO 觸發：{analysis['aiseo_triggered']}")
print(f"   PAA 數量：{analysis['paa_count']}")
print(f"   有機結果數：{len(serp['organic_results'])}")

# ================================================
# Step 1: ContentSummarizer
# ================================================
print("\n" + "=" * 60)
print("📝 Step 1: ContentSummarizer")
print("=" * 60)

organic_results = serp.get("organic_results", [])
print(f"處理 {len(organic_results)} 個競爭者結果...")

try:
    summaries = summarizer.forward(query, organic_results)
    print(f"✅ 總結完成：{len(summaries)} 個競爭者")

    # 顯示前 2 個總結
    for i, summary in enumerate(summaries[:2], 1):
        print(f"\n競爭者 {i}:")
        print(f"  域名：{summary.domain}")
        print(f"  深度：{summary.content_depth}")
        print(f"  關鍵點：")
        for point in summary.key_points:
            print(f"    - {point}")

except Exception as e:
    print(f"❌ 失敗：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ================================================
# Step 2: GapAnalyzer
# ================================================
print("\n" + "=" * 60)
print("🔍 Step 2: GapAnalyzer")
print("=" * 60)

paa_questions = serp.get("people_also_ask", [])
aiseo_triggered = analysis.get("aiseo_triggered", False)

print(f"分析 {len(summaries)} 個競爭者 + {len(paa_questions)} 個 PAA...")

try:
    gaps = gap_analyzer.forward(
        query=query,
        competitor_summaries=summaries,
        paa_questions=paa_questions,
        aiseo_triggered=aiseo_triggered
    )
    print(f"✅ 找到 {len(gaps)} 個內容缺口")

    # 顯示所有缺口
    for i, gap in enumerate(gaps, 1):
        print(f"\n缺口 {i}: [{gap.gap_type}] (分數: {gap.opportunity_score:.2f})")
        print(f"  {gap.description}")
        print(f"  建議：{gap.recommended_action}")

except Exception as e:
    print(f"❌ 失敗：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ================================================
# Step 3: OutlineGenerator
# ================================================
print("\n" + "=" * 60)
print("📋 Step 3: OutlineGenerator")
print("=" * 60)

print(f"生成文章大綱（4-block 結構）...")

try:
    outline = outline_generator.forward(
        query=query,
        content_gaps=gaps,
        paa_questions=paa_questions,
        aiseo_triggered=aiseo_triggered
    )
    print(f"✅ 大綱生成完成")

    # 顯示大綱結構
    if "blocks" in outline:
        print(f"\n文章結構：{len(outline['blocks'])} 個區塊")
        for block in outline["blocks"]:
            print(f"\n[{block.get('block_name', 'N/A')}]")
            print(f"  標題：{block.get('block_title', 'N/A')}")
            print(f"  字數：{block.get('word_count_target', 'N/A')}")

            subsections = block.get('subsections', [])
            if subsections:
                print(f"  子章節數：{len(subsections)}")
                for sub in subsections[:2]:  # 只顯示前 2 個
                    print(f"    - {sub.get('title', 'N/A')}")

    # 儲存輸出
    output_path = config.data_dir / "test_single_outline.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "query": query,
            "summaries": [s.model_dump() for s in summaries],
            "gaps": [g.model_dump() for g in gaps],
            "outline": outline
        }, f, ensure_ascii=False, indent=2)

    print(f"\n📁 輸出已儲存：{output_path}")

except Exception as e:
    print(f"❌ 失敗：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 測試完成！所有模組運作正常")
print("=" * 60)
