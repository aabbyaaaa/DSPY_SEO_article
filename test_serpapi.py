# -*- coding: utf-8 -*-
"""Test SerpAPI connection and parameters"""

import sys, io
from pathlib import Path
from serpapi import GoogleSearch
import json

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

SERPAPI_KEY = config.get_serpapi_key()
print(f"API Key: {SERPAPI_KEY[:10]}...{SERPAPI_KEY[-5:]}")

# Test simple query
params = {
    "q": "微量吸管",
    "location": "Taiwan",
    "hl": "zh-TW",
    "gl": "tw",
    "api_key": SERPAPI_KEY,
    "num": 10
}

print("\nTest Parameters:")
print(json.dumps(params, indent=2, ensure_ascii=False))

try:
    search = GoogleSearch(params)
    results = search.get_dict()

    print("\n=== API Response Keys ===")
    print(list(results.keys()))

    if "error" in results:
        print(f"\n❌ API Error: {results['error']}")

    if "search_information" in results:
        print(f"\n✅ Total Results: {results['search_information'].get('total_results', 0)}")

    if "organic_results" in results:
        print(f"✅ Organic Results: {len(results['organic_results'])} items")
        if results['organic_results']:
            print("\nFirst result:")
            print(f"  Title: {results['organic_results'][0].get('title', 'N/A')}")
            print(f"  Link: {results['organic_results'][0].get('link', 'N/A')}")
    else:
        print("\n❌ No organic_results in response")

    # Save full response for debugging
    with open("test_serp_response.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n📁 Full response saved to test_serp_response.json")

except Exception as e:
    print(f"\n❌ Exception: {e}")
