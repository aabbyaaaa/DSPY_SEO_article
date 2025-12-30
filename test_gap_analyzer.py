# -*- coding: utf-8 -*-
"""
測試 GapAnalyzer 模組
診斷為什麼 content_gaps 都是空陣列
"""

import os
import sys
import io
import json
from pathlib import Path

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加入專案根目錄
ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config
from analyze.dspy_modules import init_dspy, GapAnalyzer, ContentSummarizer

print("\n" + "=" * 60)
print("🧪 GapAnalyzer 測試腳本")
print("=" * 60)

# ================================================
# 1. 初始化 DSPy
# ================================================
print("\n📦 初始化 DSPy...")
openai_key = config.get_openai_key()
lm = init_dspy(config.dspy_model_main, openai_key)
print(f"✅ 使用模型：{config.dspy_model_main}")

# ================================================
# 2. 準備測試資料
# ================================================
print("\n📝 準備測試資料...")

# 簡單的競爭者總結（模擬 ContentSummarizer 輸出）
from analyze.dspy_modules import CompetitorSummary

test_summaries = [
    CompetitorSummary(
        position=1,
        domain="example.com",
        key_points=["不鏽鋼材質", "60分鐘定時器", "壓力控制器"],
        content_depth="medium",
        unique_value="無特殊亮點"
    ),
    CompetitorSummary(
        position=2,
        domain="test.com",
        key_points=["高溫滅菌", "適用於實驗室", "安全閥設計"],
        content_depth="shallow",
        unique_value="三安全閥"
    )
]

test_paa = [
    {"question": "高壓滅菌鍋使用方法？", "answer": ""},
    {"question": "高溫高壓滅菌鍋溫度？", "answer": ""}
]

print(f"✅ 準備了 {len(test_summaries)} 個競爭者總結")
print(f"✅ 準備了 {len(test_paa)} 個 PAA 問題")

# ================================================
# 3. 測試 GapAnalyzer
# ================================================
print("\n" + "=" * 60)
print("🔬 測試 GapAnalyzer.forward()")
print("=" * 60)

gap_analyzer = GapAnalyzer()

try:
    print("\n呼叫 GapAnalyzer...")
    result = gap_analyzer.forward(
        query="高壓滅菌鍋",
        competitor_summaries=test_summaries,
        paa_questions=test_paa,
        aiseo_triggered=True
    )

    print(f"\n✅ GapAnalyzer 執行成功！")
    print(f"📊 返回結果類型：{type(result)}")
    print(f"📊 返回結果長度：{len(result) if isinstance(result, list) else 'N/A'}")

    if isinstance(result, list):
        print(f"\n找到 {len(result)} 個內容缺口：")
        for i, gap in enumerate(result, 1):
            print(f"\n  [{i}] {gap.gap_type} (分數: {gap.opportunity_score:.2f})")
            print(f"      目標區塊: {gap.target_block}")
            print(f"      描述: {gap.description[:80]}...")
            print(f"      建議: {gap.recommended_action[:80]}...")
    else:
        print(f"\n⚠️ 返回結果不是 list：{result}")

except Exception as e:
    print(f"\n❌ GapAnalyzer 執行失敗！")
    print(f"錯誤類型：{type(e).__name__}")
    print(f"錯誤訊息：{str(e)}")

    # 印出完整的 traceback
    import traceback
    print(f"\n完整 Traceback：")
    print(traceback.format_exc())

# ================================================
# 4. 測試 DSPy Signature 原始輸出
# ================================================
print("\n" + "=" * 60)
print("🔬 測試 DSPy Signature 原始輸出")
print("=" * 60)

try:
    print("\n直接呼叫 GapAnalyzerSignature...")

    # 準備輸入資料（JSON 格式）
    summaries_json = json.dumps([s.model_dump() for s in test_summaries], ensure_ascii=False)
    paa_json = json.dumps(test_paa, ensure_ascii=False)

    # 計算平均深度
    depth_counts = {"shallow": 0, "medium": 0, "deep": 0}
    for s in test_summaries:
        depth_counts[s.content_depth] = depth_counts.get(s.content_depth, 0) + 1
    avg_depth = max(depth_counts, key=depth_counts.get)

    print(f"輸入資料準備完成：")
    print(f"  - Summaries JSON 長度：{len(summaries_json)} 字符")
    print(f"  - PAA JSON 長度：{len(paa_json)} 字符")
    print(f"  - 平均深度：{avg_depth}")

    # 呼叫 ChainOfThought
    pred = gap_analyzer.analyze(
        query="高壓滅菌鍋",
        competitor_summaries=summaries_json,
        paa_questions=paa_json,
        aiseo_triggered=True,
        avg_content_depth=avg_depth
    )

    print(f"\n✅ DSPy Signature 執行成功！")
    print(f"\n原始輸出：")
    print(f"  - pred.gaps 類型：{type(pred.gaps)}")
    print(f"  - pred.gaps 內容：")
    print(json.dumps(pred.gaps if isinstance(pred.gaps, (list, dict)) else str(pred.gaps), indent=2, ensure_ascii=False)[:1000])

    if hasattr(pred, 'priority_ranking'):
        print(f"\n  - pred.priority_ranking：{pred.priority_ranking}")

except Exception as e:
    print(f"\n❌ DSPy Signature 執行失敗！")
    print(f"錯誤類型：{type(e).__name__}")
    print(f"錯誤訊息：{str(e)}")

    import traceback
    print(f"\n完整 Traceback：")
    print(traceback.format_exc())

print("\n" + "=" * 60)
print("🎉 測試完成！")
print("=" * 60)
