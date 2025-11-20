# -*- coding: utf-8 -*-
"""
LLM-SEO Pipeline Stage ③: DSPy Analysis Runner (v1.0)
------------------------------------------------------
執行三個 DSPy 模組：
1. ContentSummarizer - 總結競爭者內容
2. GapAnalyzer - 找出內容缺口
3. OutlineGenerator - 生成文章大綱

輸入：data/serp_analysis.json
輸出：data/article_outline.json
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
print("🚀 DSPy Analysis Module - Stage ③")
print("=" * 60)
print(f"主題：{config.topic}")
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
# 載入 SERP 數據
# ================================================
serp_path = config.data_dir / config.output_files["serp_analysis"]
if not serp_path.exists():
    raise FileNotFoundError(f"❌ 找不到 {serp_path}，請先執行 analyze/serp_fetcher.py")

print(f"\n📖 載入 SERP 數據：{serp_path}")
with open(serp_path, "r", encoding="utf-8") as f:
    serp_data = json.load(f)

query_count = serp_data["query_count"]
print(f"✅ 載入 {query_count} 條查詢的 SERP 數據")

# ================================================
# 處理每個查詢
# ================================================
results = []

print("\n" + "=" * 60)
print("🔄 開始處理查詢...")
print("=" * 60)

for idx, item in enumerate(tqdm(serp_data["serp_results"], desc="DSPy 分析"), 1):
    query = item["query"]
    serp = item["serp_data"]
    analysis = item["analysis"]

    print(f"\n[{idx}/{query_count}] {query}")

    # ------------------------------------------------
    # Step 1️⃣: ContentSummarizer
    # ------------------------------------------------
    print("  📝 Step 1: 總結競爭者內容...")
    organic_results = serp.get("organic_results", [])

    if not organic_results:
        print("  ⚠️ 無有機結果，跳過")
        continue

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
    aiseo_triggered = analysis.get("aiseo_triggered", False)

    try:
        gaps = gap_analyzer.forward(
            query=query,
            competitor_summaries=summaries,
            paa_questions=paa_questions,
            aiseo_triggered=aiseo_triggered
        )
        print(f"  ✅ 缺口分析完成：找到 {len(gaps)} 個機會")

        # 顯示前 3 個缺口
        for i, gap in enumerate(gaps[:3], 1):
            print(f"     {i}. [{gap.gap_type}] {gap.description[:50]}... (分數: {gap.opportunity_score:.2f})")

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
            aiseo_triggered=aiseo_triggered
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
        "aiseo_triggered": aiseo_triggered,
        "competitor_summaries": [s.model_dump() for s in summaries],
        "content_gaps": [g.model_dump() for g in gaps],
        "outline": outline,
        "paa_questions": paa_questions,
        "related_searches": serp.get("related_searches", [])
    })

# ================================================
# 輸出最終結果
# ================================================
output_path = config.data_dir / "article_outlines.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
        "topic": config.topic,
        "query_count": len(results),
        "generated_at": str(Path(__file__).stat().st_mtime),
        "outlines": results,
        "summary": {
            "total_gaps_found": sum(len(r["content_gaps"]) for r in results),
            "avg_gaps_per_query": sum(len(r["content_gaps"]) for r in results) / len(results) if results else 0,
            "aiseo_coverage": sum(r["aiseo_triggered"] for r in results) / len(results) if results else 0
        }
    }, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("✅ DSPy 分析完成！")
print("=" * 60)
print(f"📁 輸出檔案：{output_path}")
print(f"📊 處理查詢數：{len(results)}")
print(f"🎯 總缺口數：{sum(len(r['content_gaps']) for r in results)}")
print(f"📈 平均缺口/查詢：{sum(len(r['content_gaps']) for r in results) / len(results):.1f}")
print(f"🤖 AISEO 覆蓋率：{sum(r['aiseo_triggered'] for r in results) / len(results):.1%}")
print("\n🎉 準備進入 Stage ④：文章生成")
print("=" * 60 + "\n")
