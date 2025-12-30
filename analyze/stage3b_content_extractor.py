# -*- coding: utf-8 -*-
"""
Stage 3b: 內容提取模組 (Content Extractor)
------------------------------------------
從 SERP 結果中篩選高品質頁面並使用 Tavily Extract API 提取完整內容

功能：
1. 讀取 SERP 分析結果
2. 使用 stage3_utils_page_filter.py 篩選每個查詢的 Top 3 高品質頁面
3. 使用 Tavily Extract API 提取完整頁面內容
4. 儲存高品質頁面內容供 Stage 3c DSPy 分析使用
"""

import os
import sys
import io
import json
import time
from pathlib import Path
from typing import List, Dict
import requests
from tqdm import tqdm

# Windows UTF-8 support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config
from analyze.stage3_utils_page_filter import filter_organic_results

print("\n" + "=" * 60)
print("📥 內容提取模組")
print("=" * 60)

TAVILY_API_KEY = config.get_tavily_key()

def extract_content_tavily(url: str) -> dict:
    """
    使用 Tavily Extract API 提取頁面內容

    Args:
        url: 頁面 URL

    Returns:
        提取的內容字典
    """
    try:
        response = requests.post(
            "https://api.tavily.com/extract",
            json={
                "api_key": TAVILY_API_KEY,
                "urls": [url]
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                result = data["results"][0]
                return {
                    "url": url,
                    "success": True,
                    "raw_content": result.get("raw_content", ""),
                    "title": result.get("title", ""),
                    "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }

        return {
            "url": url,
            "success": False,
            "error": f"HTTP {response.status_code}: {response.text[:200]}"
        }

    except Exception as e:
        return {
            "url": url,
            "success": False,
            "error": str(e)
        }

def process_query_pages(query: str, lang: str, organic_results: List[dict], top_n: int = 3) -> List[dict]:
    """
    處理單個查詢的頁面提取

    Args:
        query: 查詢詞
        lang: 語言
        organic_results: SERP 有機結果
        top_n: 保留前幾個頁面

    Returns:
        提取的內容列表
    """
    # 使用 page_filter 篩選高品質頁面
    filtered = filter_organic_results(organic_results, max_results=top_n)

    print(f"\n🔍 查詢：{query}")
    print(f"   語言：{lang}")
    print(f"   原始結果：{len(organic_results)} 個")
    print(f"   篩選後：{len(filtered)} 個")

    extracted_pages = []

    for i, result in enumerate(filtered, 1):
        url = result["link"]
        title = result["title"]
        quality_score = result.get("quality_score", 0)

        print(f"\n   [{i}] {title}")
        print(f"       URL: {url}")
        print(f"       品質分數: {quality_score}")

        # 使用 Tavily Extract 提取內容
        content = extract_content_tavily(url)

        if content["success"]:
            content_length = len(content["raw_content"])
            print(f"       ✅ 提取成功（{content_length} 字符）")

            extracted_pages.append({
                "query": query,
                "lang": lang,
                "position": i,
                "url": url,
                "title": title,
                "quality_score": quality_score,
                "content": content["raw_content"],
                "extracted_at": content["extracted_at"]
            })
        else:
            print(f"       ❌ 提取失敗：{content.get('error', 'Unknown error')}")

        # API 限流
        time.sleep(0.5)

    return extracted_pages

def main():
    # 讀取 SERP 分析結果
    serp_path = config.data_dir / "serp_analysis_bilingual.json"
    if not serp_path.exists():
        raise FileNotFoundError(f"❌ 找不到檔案：{serp_path}，請先執行 serp_fetcher_bilingual.py")

    print(f"\n📂 載入 SERP 分析結果...")
    with open(serp_path, "r", encoding="utf-8") as f:
        serp_data = json.load(f)

    serp_results = serp_data["serp_results"]
    print(f"✅ 載入 {len(serp_results)} 個查詢的 SERP 結果")

    # 快取
    cache_path = config.data_dir / "cache_extracted_content.json"
    cache = {}
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"📦 載入 {len(cache)} 個快取的提取結果")

    # 處理每個查詢
    all_extracted_pages = []

    print("\n" + "=" * 60)
    print("🚀 開始提取頁面內容")
    print("=" * 60)

    for result in tqdm(serp_results, desc="Processing queries"):
        query = result["query"]
        lang = result["lang"]
        organic_results = result["serp_data"]["organic_results"]

        cache_key = f"{query}_{lang}"

        # 檢查快取
        if cache_key in cache:
            print(f"\n💾 使用快取：{query}")
            extracted = cache[cache_key]
        else:
            # 提取內容
            extracted = process_query_pages(query, lang, organic_results, top_n=3)
            cache[cache_key] = extracted

            # 儲存快取（即時更新）
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

        all_extracted_pages.extend(extracted)

    # 儲存最終結果
    output_path = config.data_dir / "extracted_content_60_pages.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_queries": len(serp_results),
            "total_pages_extracted": len(all_extracted_pages),
            "pages": all_extracted_pages
        }, f, ensure_ascii=False, indent=2)

    # 統計報告
    print("\n" + "=" * 60)
    print("✅ 內容提取完成！")
    print("=" * 60)
    print(f"📁 輸出檔案：{output_path}")
    print(f"📁 快取檔案：{cache_path}")
    print(f"\n📊 統計資訊：")
    print(f"   處理查詢數：{len(serp_results)}")
    print(f"   提取頁面數：{len(all_extracted_pages)}")
    print(f"   目標頁面數：{len(serp_results) * 3}")

    zh_pages = [p for p in all_extracted_pages if p["lang"] == "zh-TW"]
    en_pages = [p for p in all_extracted_pages if p["lang"] == "en"]

    print(f"\n   繁體中文頁面：{len(zh_pages)}")
    print(f"   English 頁面：{len(en_pages)}")

    # 計算平均內容長度
    if all_extracted_pages:
        avg_length = sum(len(p["content"]) for p in all_extracted_pages) / len(all_extracted_pages)
        print(f"\n   平均內容長度：{avg_length:.0f} 字符")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
