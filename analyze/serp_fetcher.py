# -*- coding: utf-8 -*-
"""
LLM-SEO Pipeline Step 2: SERP Analysis Module (v1.0)
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

print("\nInitializing SERP Fetcher Module...")
print(f"Topic: {config.topic}")
print(f"SERP Top N: {config.serp_top_n}")
print(f"Search Engines: {', '.join(config.serp_search_engines)}")

SERPAPI_KEY = config.get_serpapi_key()

def fetch_serp(query: str, location: str = "Taiwan", lang: str = "zh-TW") -> dict:
    """Fetch Google SERP data using SerpAPI"""

    params = {
        "q": query,
        "location": location,
        "hl": lang,  # Use full language code (zh-TW)
        "gl": config.region.lower(),
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
            "ai_overview": ai_overview,
            "organic_results": organic,
            "people_also_ask": paa,
            "related_searches": related,
            "total_results": results.get("search_information", {}).get("total_results", 0)
        }

    except Exception as e:
        print(f"SERP fetch error: {query} - {e}")
        return {
            "query": query,
            "error": str(e),
            "ai_overview": {"present": False, "content": ""},
            "organic_results": [],
            "people_also_ask": [],
            "related_searches": [],
            "total_results": 0
        }

def analyze_serp_features(serp_data: dict) -> dict:
    """Analyze SERP features for SEO/AISEO/GEO/AIO signals"""

    analysis = {
        "aiseo_triggered": serp_data["ai_overview"]["present"],
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

    if analysis["aiseo_triggered"]:
        analysis["content_gap_signals"].append("AI Overview triggered - AISEO optimization needed")

    if analysis["unique_domains"] < 5:
        analysis["content_gap_signals"].append("Low domain diversity - ranking opportunity")

    return analysis

def main():
    scores_path = config.data_dir / "semantic_scores.csv"
    if not scores_path.exists():
        raise FileNotFoundError(f"File not found: {scores_path}, run semantic_score.py first")

    df = pd.read_csv(scores_path)
    high_potential = df[df["score"] >= 4.0]["query"].tolist()
    print(f"\nLoaded {len(high_potential)} high-potential queries")

    # Cache
    cache_path = config.data_dir / "cache_serp.json"
    cache = {}
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached SERP results")

    # Fetch SERP data
    serp_results = []
    print("\nFetching SERP data...")

    for query in tqdm(high_potential, desc="SERP Fetching"):
        if query in cache:
            serp_data = cache[query]
        else:
            serp_data = fetch_serp(query)
            cache[query] = serp_data
            time.sleep(1)

        features = analyze_serp_features(serp_data)

        serp_results.append({
            "query": query,
            "serp_data": serp_data,
            "analysis": features
        })

    # Save cache
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    # Output analysis
    output_path = config.data_dir / config.output_files["serp_analysis"]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "topic": config.topic,
            "query_count": len(high_potential),
            "serp_results": serp_results,
            "summary": {
                "aiseo_trigger_rate": sum(r["analysis"]["aiseo_triggered"] for r in serp_results) / len(serp_results),
                "avg_paa_per_query": sum(r["analysis"]["paa_count"] for r in serp_results) / len(serp_results),
                "total_content_gaps": sum(len(r["analysis"]["content_gap_signals"]) for r in serp_results)
            }
        }, f, ensure_ascii=False, indent=2)

    print(f"\nSERP analysis complete!")
    print(f"Output: {output_path}")
    print(f"AISEO trigger rate: {sum(r['analysis']['aiseo_triggered'] for r in serp_results) / len(serp_results):.1%}")
    print(f"Avg PAA per query: {sum(r['analysis']['paa_count'] for r in serp_results) / len(serp_results):.1f}")

if __name__ == "__main__":
    main()
