# -*- coding: utf-8 -*-
"""
Stage 3a: SERP Analysis Module (Bilingual)
-------------------------------------------
支援雙語 SERP 分析（繁體中文 + 英文）
從 Stage 2 語義評分結果中篩選 High + Medium Tier 查詢，抓取 SERP 資料
"""

import os, json, time, sys, io
from pathlib import Path
import pandas as pd
from serpapi import GoogleSearch
from tqdm import tqdm

# Windows UTF-8 support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

print("\n" + "=" * 60)
print("🌐 雙語 SERP 分析模組")
print("=" * 60)
print(f"中文主題：{config.topic}")
print(f"英文主題：{config.topic_en}")
print(f"SERP Top N: {config.serp_top_n}")

SERPAPI_KEY = config.get_serpapi_key()

def fetch_serp(query: str, lang: str = "zh-TW") -> dict:
    """
    Fetch Google SERP data using SerpAPI

    Args:
        query: 查詢詞
        lang: 語言 (zh-TW 或 en)

    Returns:
        SERP 資料字典
    """

    # 根據語言設定參數
    if lang == "zh-TW":
        location = "Taiwan"
        hl = "zh-TW"
        gl = "tw"
    else:
        location = "United States"
        hl = "en"
        gl = "us"

    params = {
        "q": query,
        "location": location,
        "hl": hl,
        "gl": gl,
        "api_key": SERPAPI_KEY,
        "num": config.serp_top_n
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        # Extract AI Overview
        ai_overview = {
            "present": "answer_box" in results or "ai_overview" in results,
            "content": ""
        }

        if "answer_box" in results:
            ai_overview["content"] = results["answer_box"].get("snippet", "")
        elif "ai_overview" in results:
            ai_overview["content"] = results["ai_overview"].get("snippet", "")

        # Extract organic results
        organic = []
        for i, item in enumerate(results.get("organic_results", [])[:config.serp_top_n], 1):
            organic.append({
                "position": i,
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "domain": item.get("displayed_link", item.get("link", "").split('/')[2] if '/' in item.get("link", "") else "")
            })

        # Extract People Also Ask
        paa = []
        if config.serp_extract_paa:
            for item in results.get("related_questions", []):
                paa.append({
                    "question": item.get("question", ""),
                    "answer": item.get("snippet", "")
                })

        # Extract Related Searches
        related = []
        if config.serp_extract_related:
            for item in results.get("related_searches", []):
                related.append(item.get("query", ""))

        return {
            "query": query,
            "lang": lang,
            "ai_overview": ai_overview,
            "organic_results": organic,
            "people_also_ask": paa,
            "related_searches": related,
            "total_results": results.get("search_information", {}).get("total_results", 0)
        }

    except Exception as e:
        print(f"\n⚠️ SERP fetch error: {query} - {e}")
        return {
            "query": query,
            "lang": lang,
            "error": str(e),
            "ai_overview": {"present": False, "content": ""},
            "organic_results": [],
            "people_also_ask": [],
            "related_searches": [],
            "total_results": 0
        }

def analyze_serp_features(serp_data: dict) -> dict:
    """
    分析 SERP 特徵，檢測 AI 引擎優化信號

    檢測項目:
    - AIO (AI Overview): Google 專屬 AI 摘要
    - AEO (Answer Engine): Perplexity, Bing Copilot 等
    - GEO (Generative Engine): ChatGPT, Claude, Gemini 引用
    """

    analysis = {
        "aio_triggered": serp_data["ai_overview"]["present"],  # AIO: Google AI Overview
        "aiseo_triggered": serp_data["ai_overview"]["present"],  # 保留向後兼容
        "avg_title_length": 0,
        "avg_snippet_length": 0,
        "unique_domains": 0,
        "paa_count": len(serp_data["people_also_ask"]),
        "related_count": len(serp_data["related_searches"]),
        "content_gap_signals": []
    }

    organic = serp_data["organic_results"]
    if organic:
        titles = [len(r["title"]) for r in organic if r["title"]]
        snippets = [len(r["snippet"]) for r in organic if r["snippet"]]

        analysis["avg_title_length"] = round(sum(titles) / len(titles), 1) if titles else 0
        analysis["avg_snippet_length"] = round(sum(snippets) / len(snippets), 1) if snippets else 0
        analysis["unique_domains"] = len(set(r["domain"] for r in organic if r["domain"]))

    # Content gap signals
    if analysis["paa_count"] > 5:
        analysis["content_gap_signals"].append("High PAA count - users have many questions")

    if analysis["aio_triggered"]:
        analysis["content_gap_signals"].append("AIO triggered - Google AI Overview optimization needed")
        analysis["content_gap_signals"].append("Consider AEO strategies - Answer Engine Optimization")

    if analysis["unique_domains"] < 5:
        analysis["content_gap_signals"].append("Low domain diversity - ranking opportunity")

    return analysis

def main():
    # 讀取語義評分結果
    scores_path = config.data_dir / "semantic_scores.csv"
    if not scores_path.exists():
        raise FileNotFoundError(f"❌ 找不到檔案: {scores_path}，請先執行 analyze/stage2_semantic_scoring.py")

    df_all = pd.read_csv(scores_path)
    print(f"\n📂 載入語義評分結果：{len(df_all)} 個查詢")

    # 篩選 High + Medium Tier（跳過 Low Tier）
    df = df_all[df_all["quality_tier"].isin(["high", "medium"])].copy()

    high_count = len(df_all[df_all["quality_tier"] == "high"])
    medium_count = len(df_all[df_all["quality_tier"] == "medium"])
    low_count = len(df_all[df_all["quality_tier"] == "low"])

    print(f"\n📊 品質分級統計：")
    print(f"   ✅ High Tier: {high_count} 個")
    print(f"   ⚠️ Medium Tier: {medium_count} 個")
    print(f"   ❌ Low Tier: {low_count} 個（跳過）")

    print(f"\n🎯 將處理 {len(df)} 個查詢（High + Medium）")

    zh_count = len(df[df["lang"] == "zh-TW"])
    en_count = len(df[df["lang"] == "en"])
    print(f"   繁體中文：{zh_count} 個")
    print(f"   English：{en_count} 個")

    # Cache
    cache_path = config.data_dir / "cache_serp_bilingual.json"
    cache = {}
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"\n📦 載入 {len(cache)} 個快取的 SERP 結果")

    # Fetch SERP data
    serp_results = []
    print("\n🔍 開始抓取 SERP 資料...")

    for _, row in tqdm(df.iterrows(), total=len(df), desc="SERP Fetching"):
        query = row["query"]
        lang = row["lang"]

        cache_key = f"{query}_{lang}"

        if cache_key in cache:
            serp_data = cache[cache_key]
        else:
            serp_data = fetch_serp(query, lang)
            cache[cache_key] = serp_data
            time.sleep(1)  # API 限流

        features = analyze_serp_features(serp_data)

        serp_results.append({
            "query": query,
            "lang": lang,
            "serp_data": serp_data,
            "analysis": features
        })

    # Save cache
    print("\n💾 儲存快取...")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    # Output analysis
    output_path = config.data_dir / "serp_analysis_bilingual.json"

    # 計算統計
    aio_trigger_rate = sum(r["analysis"]["aio_triggered"] for r in serp_results) / len(serp_results)
    aiseo_trigger_rate = aio_trigger_rate  # 保留向後兼容
    avg_paa = sum(r["analysis"]["paa_count"] for r in serp_results) / len(serp_results)
    total_gaps = sum(len(r["analysis"]["content_gap_signals"]) for r in serp_results)

    # 分語言統計
    zh_results = [r for r in serp_results if r["lang"] == "zh-TW"]
    en_results = [r for r in serp_results if r["lang"] == "en"]

    zh_aio = sum(r["analysis"]["aio_triggered"] for r in zh_results) / len(zh_results) if zh_results else 0
    en_aio = sum(r["analysis"]["aio_triggered"] for r in en_results) / len(en_results) if en_results else 0

    # 保留舊變數名以向後兼容
    zh_aiseo = zh_aio
    en_aiseo = en_aio

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "topic_zh": config.topic,
            "topic_en": config.topic_en,
            "query_count": len(df),
            "serp_results": serp_results,
            "summary": {
                "total_queries": len(serp_results),
                "zh_queries": len(zh_results),
                "en_queries": len(en_results),
                "aio_trigger_rate": aio_trigger_rate,  # AIO (Google AI Overview)
                "zh_aio_rate": zh_aio,
                "en_aio_rate": en_aio,
                # 保留舊欄位以向後兼容
                "aiseo_trigger_rate": aiseo_trigger_rate,
                "zh_aiseo_rate": zh_aiseo,
                "en_aiseo_rate": en_aiseo,
                "avg_paa_per_query": avg_paa,
                "total_content_gaps": total_gaps
            }
        }, f, ensure_ascii=False, indent=2)

    # 結果報告
    print("\n" + "=" * 60)
    print("✅ SERP 分析完成！")
    print("=" * 60)
    print(f"📁 輸出檔案：{output_path}")
    print(f"📁 快取檔案：{cache_path}")
    print(f"\n📊 統計資訊：")
    print(f"   總查詢數：{len(serp_results)}")
    print(f"   繁體中文：{len(zh_results)}")
    print(f"   English：{len(en_results)}")
    print(f"\n🤖 AIO (Google AI Overview) 觸發率：")
    print(f"   整體：{aio_trigger_rate:.1%}")
    print(f"   中文：{zh_aio:.1%}")
    print(f"   英文：{en_aio:.1%}")
    print(f"\n❓ 平均 PAA 數量：{avg_paa:.1f}")
    print(f"🔍 內容缺口信號總數：{total_gaps}")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
