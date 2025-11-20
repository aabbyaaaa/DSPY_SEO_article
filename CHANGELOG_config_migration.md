# 配置系統遷移紀錄

## 更新日期
2025-01-20

## 更新概要
將所有 `analyze/` 模組統一使用 `config_loader` 進行配置管理，取代原本的手動載入方式。

---

## 更新檔案清單

### 新增檔案

1. **config/config_loader.py**
   - 統一配置載入工具
   - 提供 `Config` 類別快速存取所有設定
   - 自動載入 `config/secrets.env`
   - 支援 Windows UTF-8 編碼

2. **test_config_integration.py**
   - 配置整合測試腳本
   - 驗證所有配置項目是否正確載入
   - 檢查 API Keys 是否存在

3. **CHANGELOG_config_migration.md** (本檔案)
   - 更新紀錄

### 更新檔案

1. **config/settings.yaml**
   - 完整的 5-stage pipeline 配置
   - 新增 SERP 分析配置區塊
   - 新增 DSPy 模組配置區塊
   - 新增 4-block 文章結構量化標準
   - 新增去 AI 化策略配置
   - 移除所有 API keys（已移至 secrets.env）
   - 調整評分權重：embedding_weight 0.6, llm_weight 0.4

2. **analyze/queries.py** (v1.3 → v1.4)
   - 改用 `config_loader` 載入配置
   - BASE_SEEDS 從 settings.yaml 讀取（而非硬編碼）
   - 模型名稱使用 `config.dspy_model_small`
   - 檔案路徑使用 `config.data_dir` 和 `config.output_files`
   - 新增 Windows UTF-8 編碼支援

3. **analyze/merge_queries.py** (v1.0 → v1.1)
   - 改用 `config_loader` 載入配置
   - THRESHOLD 從 settings.yaml 讀取
   - 檔案路徑使用 `config.data_dir` 和 `config.output_files`
   - 新增 Windows UTF-8 編碼支援

4. **analyze/semantic_score.py** (v1.2 → v1.3)
   - 改用 `config_loader` 載入配置
   - 所有權重從 settings.yaml 讀取
   - 模型名稱使用 `config.dspy_model_small`
   - 混合評分權重使用 `config.embedding_weight` 和 `config.llm_weight`
   - 檔案路徑使用 `config.data_dir`
   - 新增 Windows UTF-8 編碼支援
   - 移除手動環境變數檢查（由 config_loader 處理）

---

## 主要改進

### 1. 統一配置管理
**之前**：每個腳本各自載入 YAML 和環境變數
```python
# 舊方式
with open("config/settings.yaml", "r") as f:
    cfg = yaml.safe_load(f)
topic = cfg.get("topic", "微量吸管")
```

**之後**：使用統一的 config_loader
```python
# 新方式
from config.config_loader import config
topic = config.topic
```

### 2. 移除硬編碼值
**之前**：
- `queries.py` 中的 BASE_SEEDS 硬編碼
- `merge_queries.py` 中的 THRESHOLD = 0.90 硬編碼
- `semantic_score.py` 中的權重硬編碼（0.7 * emb + 0.3 * llm）

**之後**：
- 所有數值從 `settings.yaml` 讀取
- 修改配置無需改動程式碼

### 3. 路徑管理改善
**之前**：
```python
pool_path = os.path.join(ROOT_DIR, "data", "query_pool.csv")
```

**之後**：
```python
pool_path = config.data_dir / config.output_files["query_pool"]
```

### 4. API Key 管理
**之前**：
```python
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
```

**之後**：
```python
from config.config_loader import config
api_key = config.get_openai_key()  # 自動檢查是否存在
```

---

## 配置項目對照表

| 配置項目 | 舊位置 | 新位置 | 說明 |
|---------|--------|--------|------|
| 主題 | `settings.yaml: topic` | `config.topic` | 不變 |
| 查詢池大小 | `settings.yaml: query_pool_size` | `config.query_pool_size` | 不變 |
| 合併閾值 | `merge_queries.py: THRESHOLD = 0.90` | `config.merge_threshold` | 從硬編碼改為配置 |
| 手動種子 | `queries.py: BASE_SEEDS = [...]` | `config.base_seeds` | 從硬編碼改為配置 |
| Coverage 權重 | `settings.yaml: scores.coverage_w` | `config.coverage_w` | 不變 |
| Embedding 權重 | `semantic_score.py: 0.7` | `config.embedding_weight` | 從硬編碼改為配置 (0.6) |
| LLM 權重 | `semantic_score.py: 0.3` | `config.llm_weight` | 從硬編碼改為配置 (0.4) |
| 小模型名稱 | `"gpt-4o-mini"` | `config.dspy_model_small` | 從硬編碼改為配置 |
| 資料目錄 | `"data"` | `config.data_dir` | 改為 Path 物件 |

---

## 使用方式

### 在任何模組中使用配置

```python
import sys
from pathlib import Path

# 加入專案根目錄到路徑
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config

# 直接使用
print(config.topic)
print(config.serp_top_n)
api_key = config.get_openai_key()
```

### 修改配置

只需編輯 `config/settings.yaml`，無需修改程式碼：

```yaml
# config/settings.yaml
topic: 新主題
query_generation:
  pool_size: 30
  merge_threshold: 0.85
```

---

## 測試驗證

執行以下命令驗證配置整合：

```bash
# 測試配置載入
python config/config_loader.py

# 測試完整配置整合
python test_config_integration.py
```

預期輸出：所有配置項目正確顯示，API Keys 正常載入。

---

## 向後相容性

**中斷性改變**：
1. `queries.py` 不再從檔案內的 `BASE_SEEDS` 讀取，需在 `settings.yaml` 設定
2. `merge_queries.py` 的 THRESHOLD 不再硬編碼，需在 `settings.yaml` 設定
3. `semantic_score.py` 的混合權重從 0.7/0.3 改為 0.6/0.4

**遷移步驟**：
1. 確保 `config/settings.yaml` 包含所有必要配置
2. 確保 `config/secrets.env` 包含所有 API Keys
3. 執行測試腳本驗證

---

## 下一步

1. 實作 `serp_fetcher.py` 使用相同的配置系統
2. 建立 DSPy 模組（Stage ③）使用配置系統
3. 建立主執行腳本統一調用所有 stage

---

## 技術細節

### Windows UTF-8 編碼支援

所有腳本開頭加入：
```python
import sys, io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

### Path 物件使用

改用 `pathlib.Path` 而非字串拼接：
```python
# 舊方式
path = os.path.join(ROOT_DIR, "data", "file.csv")

# 新方式
path = config.data_dir / "file.csv"
```

---

## 維護者
- 更新日期：2025-01-20
- 版本：v1.0
