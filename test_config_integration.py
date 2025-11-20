"""
測試配置整合 - 驗證所有 analyze 模組都能正確載入配置
"""
import sys
import io

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config_loader import config

print("=" * 60)
print("配置整合測試")
print("=" * 60)

# 測試基本配置
print("\n[基本配置]")
print(f"  語言: {config.lang}")
print(f"  地區: {config.region}")
print(f"  主題: {config.topic}")

# 測試查詢生成配置
print("\n[查詢生成配置]")
print(f"  查詢池大小: {config.query_pool_size}")
print(f"  合併閾值: {config.merge_threshold}")
print(f"  手動種子數量: {len(config.base_seeds)}")
print(f"  種子內容: {config.base_seeds[:3]}...")

# 測試 SERP 配置
print("\n[SERP 分析配置]")
print(f"  啟用狀態: {config.serp_enabled}")
print(f"  Top N: {config.serp_top_n}")
print(f"  搜尋引擎: {config.serp_search_engines}")

# 測試語義評分配置
print("\n[語義評分配置]")
print(f"  Embedding 權重: {config.embedding_weight}")
print(f"  LLM 權重: {config.llm_weight}")
print(f"  Coverage 權重: {config.coverage_w}")
print(f"  Relevance 權重: {config.relevance_w}")
print(f"  Density 權重: {config.density_w}")

# 測試 DSPy 配置
print("\n[DSPy 配置]")
print(f"  啟用狀態: {config.dspy_enabled}")
print(f"  小模型: {config.dspy_model_small}")
print(f"  主模型: {config.dspy_model_main}")

# 測試文章結構配置
print("\n[文章結構配置]")
print(f"  結構類型: {config.article_structure}")
print(f"  總字數範圍: {config.total_word_count_min}-{config.total_word_count_max}")
blocks = config.article_blocks
for block_name, block_config in blocks.items():
    wc_min = block_config.get('word_count_min', 'N/A')
    wc_max = block_config.get('word_count_max', 'N/A')
    print(f"  {block_name}: {wc_min}-{wc_max} 字")

# 測試去 AI 化配置
print("\n[去 AI 化配置]")
print(f"  啟用狀態: {config.de_ai_enabled}")
print(f"  目標 AI 分數: {config.target_ai_score}")
print(f"  移除模式數量: {len(config.de_ai_patterns)}")

# 測試輸出配置
print("\n[輸出配置]")
print(f"  資料目錄: {config.data_dir}")
print(f"  輸出檔案:")
for key, filename in config.output_files.items():
    print(f"    {key}: {filename}")

# 測試 API Keys
print("\n[API Keys 檢查]")
try:
    openai_key = config.get_openai_key()
    print(f"  OpenAI Key: 存在 ({len(openai_key)} 字元)")
except:
    print(f"  OpenAI Key: 缺失")

try:
    tavily_key = config.get_tavily_key()
    print(f"  Tavily Key: 存在 ({len(tavily_key)} 字元)")
except:
    print(f"  Tavily Key: 缺失")

try:
    serpapi_key = config.get_serpapi_key()
    print(f"  SerpAPI Key: 存在 ({len(serpapi_key)} 字元)")
except:
    print(f"  SerpAPI Key: 缺失")

print("\n" + "=" * 60)
print("配置整合測試完成！")
print("=" * 60)
