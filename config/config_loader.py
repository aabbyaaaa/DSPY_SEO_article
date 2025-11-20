"""
Configuration Loader for LLM-SEO Pipeline
-----------------------------------------
統一載入 settings.yaml 和 secrets.env
避免每個模組都要重複寫載入邏輯
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# 專案根目錄
ROOT_DIR = Path(__file__).parent.parent.absolute()
CONFIG_DIR = ROOT_DIR / "config"

# 載入環境變數
load_dotenv(CONFIG_DIR / "secrets.env")


def load_config(config_name: str = "settings.yaml") -> Dict[str, Any]:
    """
    載入 YAML 配置檔案

    Args:
        config_name: 配置檔案名稱 (預設: settings.yaml)

    Returns:
        配置字典
    """
    config_path = CONFIG_DIR / config_name

    if not config_path.exists():
        raise FileNotFoundError(f"❌ 找不到配置檔案: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def get_api_key(key_name: str, required: bool = False) -> str:
    """
    從環境變數取得 API Key

    Args:
        key_name: API Key 名稱 (例如 OPENAI_API_KEY)
        required: 是否為必要 (True 時找不到會報錯)

    Returns:
        API Key 字串
    """
    api_key = os.getenv(key_name)

    if required and not api_key:
        raise ValueError(f"❌ 缺少必要的 API Key: {key_name}，請檢查 config/secrets.env")

    return api_key


def get_model_name(model_type: str = "main") -> str:
    """
    取得 LLM 模型名稱

    Args:
        model_type: 模型類型 (small | main | fallback)

    Returns:
        模型名稱 (例如 gpt-4o)
    """
    config = load_config()
    return config.get("llm_models", {}).get(model_type, "gpt-4o-mini")


# 快速存取常用配置
class Config:
    """配置快速存取類別"""

    def __init__(self):
        self._config = load_config()

    # === 基本設定 ===
    @property
    def lang(self) -> str:
        return self._config.get("lang", "zh-TW")

    @property
    def region(self) -> str:
        return self._config.get("region", "tw")

    @property
    def topic(self) -> str:
        return self._config.get("topic", "")

    # === Stage ① & ② ===
    @property
    def query_pool_size(self) -> int:
        return self._config.get("query_generation", {}).get("pool_size", 20)

    @property
    def merge_threshold(self) -> float:
        return self._config.get("query_generation", {}).get("merge_threshold", 0.90)

    @property
    def base_seeds(self) -> list:
        return self._config.get("query_generation", {}).get("base_seeds", [])

    # === SERP 分析 ===
    @property
    def serp_enabled(self) -> bool:
        return self._config.get("serp", {}).get("enabled", True)

    @property
    def serp_top_n(self) -> int:
        return self._config.get("serp", {}).get("top_n", 10)

    @property
    def serp_search_engines(self) -> list:
        return self._config.get("serp", {}).get("search_engines", ["google"])

    @property
    def serp_extract_paa(self) -> bool:
        return self._config.get("serp", {}).get("features", {}).get("extract_paa", True)

    @property
    def serp_extract_related(self) -> bool:
        return self._config.get("serp", {}).get("features", {}).get("extract_related", True)

    @property
    def serp_extract_featured_snippet(self) -> bool:
        return self._config.get("serp", {}).get("features", {}).get("extract_featured_snippet", True)

    @property
    def serp_extract_schema(self) -> bool:
        return self._config.get("serp", {}).get("features", {}).get("extract_schema", True)

    # === 語義評分 ===
    @property
    def embedding_weight(self) -> float:
        return self._config.get("scores", {}).get("embedding_weight", 0.6)

    @property
    def llm_weight(self) -> float:
        return self._config.get("scores", {}).get("llm_weight", 0.4)

    @property
    def coverage_w(self) -> float:
        return self._config.get("scores", {}).get("coverage_w", 0.4)

    @property
    def relevance_w(self) -> float:
        return self._config.get("scores", {}).get("relevance_w", 0.4)

    @property
    def density_w(self) -> float:
        return self._config.get("scores", {}).get("density_w", 0.2)

    # === DSPy ===
    @property
    def dspy_enabled(self) -> bool:
        return self._config.get("dspy", {}).get("enabled", True)

    @property
    def dspy_model_small(self) -> str:
        return self._config.get("dspy", {}).get("models", {}).get("small", "gpt-4o-mini")

    @property
    def dspy_model_main(self) -> str:
        return self._config.get("dspy", {}).get("models", {}).get("main", "gpt-4o")

    # === 文章結構 ===
    @property
    def article_structure(self) -> str:
        return self._config.get("article", {}).get("structure", "4-block")

    @property
    def article_blocks(self) -> dict:
        return self._config.get("article", {}).get("blocks", {})

    @property
    def total_word_count_min(self) -> int:
        return self._config.get("article", {}).get("total_word_count_min", 1500)

    @property
    def total_word_count_max(self) -> int:
        return self._config.get("article", {}).get("total_word_count_max", 2150)

    # === 去 AI 化 ===
    @property
    def de_ai_enabled(self) -> bool:
        return self._config.get("refinement", {}).get("de_ai", {}).get("enabled", True)

    @property
    def de_ai_patterns(self) -> list:
        return self._config.get("refinement", {}).get("de_ai", {}).get("remove_patterns", [])

    @property
    def target_ai_score(self) -> float:
        return self._config.get("refinement", {}).get("de_ai", {}).get("target_ai_score", 0.35)

    # === 輸出設定 ===
    @property
    def data_dir(self) -> Path:
        return ROOT_DIR / self._config.get("output", {}).get("data_dir", "data")

    @property
    def output_files(self) -> dict:
        return self._config.get("output", {}).get("files", {})

    # === API Keys ===
    def get_openai_key(self) -> str:
        return get_api_key("OPENAI_API_KEY", required=True)

    def get_tavily_key(self) -> str:
        return get_api_key("TAVILY_API_KEY", required=False)

    def get_serpapi_key(self) -> str:
        return get_api_key("SERPAPI_KEY", required=False)

    def get_rephrasy_key(self) -> str:
        return get_api_key("REPHRASY_API_KEY", required=False)


# 全域配置實例
config = Config()


# ================================================
# 使用範例
# ================================================
if __name__ == "__main__":
    import sys
    import io

    # 設定 Windows 控制台為 UTF-8
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("配置載入測試\n")
    print(f"語言: {config.lang}")
    print(f"地區: {config.region}")
    print(f"主題: {config.topic}")
    print(f"查詢池大小: {config.query_pool_size}")
    print(f"SERP Top N: {config.serp_top_n}")
    print(f"Embedding 權重: {config.embedding_weight}")
    print(f"LLM 權重: {config.llm_weight}")
    print(f"DSPy 小模型: {config.dspy_model_small}")
    print(f"DSPy 主模型: {config.dspy_model_main}")
    print(f"文章結構: {config.article_structure}")
    print(f"總字數範圍: {config.total_word_count_min}-{config.total_word_count_max}")
    print(f"去 AI 化目標分數: {config.target_ai_score}")
    print(f"\n資料目錄: {config.data_dir}")
    print(f"OpenAI Key 存在: {bool(config.get_openai_key())}")
    print(f"Tavily Key 存在: {bool(config.get_tavily_key())}")
    print(f"SerpAPI Key 存在: {bool(config.get_serpapi_key())}")
    print("\n配置載入成功！")
