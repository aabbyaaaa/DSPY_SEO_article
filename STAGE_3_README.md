# Stage ③ DSPy 分析模組 - 實作說明

## 📋 目前狀態：已完成核心模組開發

### ✅ 已完成的工作

#### 1. 核心 DSPy 模組 ([analyze/dspy_modules.py](analyze/dspy_modules.py))

**ContentSummarizer（競爭者內容總結）**
- 輸入：查詢 + 競爭者的 title & snippet
- 輸出：每個競爭者的 3-5 個關鍵點 + 內容深度評估 + 獨特價值
- 使用 ChainOfThought 提高推理質量

**GapAnalyzer（內容缺口分析）**
- 輸入：查詢 + 競爭者總結 + PAA 問題 + AISEO 狀態
- 輸出：3-5 個排序後的內容缺口機會（含機會分數 0-1）
- 自動判斷缺口類型：AISEO/PAA/Depth/Coverage

**OutlineGenerator（文章大綱生成）**
- 輸入：查詢 + 內容缺口 + PAA 問題 + AISEO 狀態 + 4-block 要求
- 輸出：完整的 4-block 文章大綱（Quick Summary/Definition/Uses/FAQ）
- 自動將 PAA 問題分配到各 block

#### 2. 主執行腳本 ([analyze/run_dspy_analysis.py](analyze/run_dspy_analysis.py))

- 載入 `data/serp_analysis.json` (24 個查詢)
- 依序執行三個 DSPy 模組
- 輸出 `data/article_outlines.json`（包含所有查詢的大綱）
- 實時顯示處理進度和缺口機會

#### 3. 測試腳本

- **test_dspy_modules.py** - 驗證模組導入
- **test_dspy_single.py** - 單一查詢完整測試

---

## 🚀 如何運行

### 前置條件

確保已完成 Stage ① & ②：
```bash
# 1. 生成查詢池
python analyze/queries.py

# 2. 語義評分
python analyze/semantic_score.py

# 3. SERP 分析
python analyze/serp_fetcher.py
```

### 運行 DSPy 分析

```bash
# 方法 1：完整分析（24 個查詢）
python analyze/run_dspy_analysis.py

# 方法 2：單一查詢測試（推薦先測試）
python test_dspy_single.py
```

---

## 📊 輸出文件

### data/article_outlines.json

```json
{
  "topic": "微量吸管",
  "query_count": 24,
  "outlines": [
    {
      "query": "微量吸管",
      "aiseo_triggered": true,
      "competitor_summaries": [...],  // ContentSummarizer 輸出
      "content_gaps": [...],          // GapAnalyzer 輸出
      "outline": {                    // OutlineGenerator 輸出
        "topic": "微量吸管",
        "blocks": [
          {
            "block_name": "quick_summary",
            "block_title": "微量吸管快速總覽",
            "word_count_target": "100-150",
            "subsections": [...]
          },
          ...
        ]
      }
    }
  ],
  "summary": {
    "total_gaps_found": 120,
    "avg_gaps_per_query": 5.0,
    "aiseo_coverage": 0.833
  }
}
```

---

## 🔧 技術細節

### DSPy 配置 ([config/settings.yaml](config/settings.yaml) lines 85-114)

```yaml
dspy:
  enabled: true
  models:
    small: gpt-4o-mini       # ContentSummarizer
    main: gpt-4o             # GapAnalyzer & OutlineGenerator
  optimizer:
    type: BootstrapFewShot
    max_bootstrapped_demos: 8
  modules:
    content_summarizer:
      max_summary_length: 200
      extract_keywords: true
    gap_analyzer:
      min_gap_score: 0.6
      max_gaps: 5
    outline_generator:
      structure: "4-block"
      use_serp_insights: true
```

### DSPy Signature 設計原則

1. **明確的輸入輸出類型**：使用 `dspy.InputField` 和 `dspy.OutputField`
2. **結構化輸出**：使用 Pydantic `BaseModel` 確保輸出格式一致
3. **鏈式推理**：使用 `ChainOfThought` 提高複雜任務的推理質量

### 4-Block 文章結構

從 SERP 數據 → DSPy 分析 → 4-Block 大綱：

```
Quick Summary (100-150字)
  ↓ 目的：被 AI Overview 引用
  ↓ 包含：定義 + 核心用途 + 主要類型

Definition (300-400字)
  ↓ 目的：深度說明
  ↓ 包含：差異說明 + 應用場景 + 視覺化

Uses (500-600字)
  ↓ 目的：實用指南
  ↓ 包含：使用方法 + 維護 + 常見問題排查

FAQ (600-1000字)
  ↓ 目的：回答所有 PAA 問題
  ↓ 包含：5-10 個 Q&A + FAQPage Schema
```

---

## ⚙️ DSPy 版本相容性

本專案使用 **DSPy 2.6.5**，API 與舊版不同：

```python
# ❌ 舊版 API (不適用)
lm = dspy.OpenAI(model="gpt-4o", api_key=key)
dspy.settings.configure(lm=lm)

# ✅ 新版 API (2.6+)
lm = dspy.LM(model="openai/gpt-4o", api_key=key)
dspy.configure(lm=lm)
```

---

## 🐛 常見問題排查

### 1. `AttributeError: module 'dspy' has no attribute 'OpenAI'`

**原因**：DSPy 2.6+ 移除了 `dspy.OpenAI`，改用統一的 `dspy.LM`

**解決**：已在 [dspy_modules.py:302-307](analyze/dspy_modules.py#L302) 修正

### 2. `FileNotFoundError: data/serp_analysis.json`

**原因**：未執行 Stage ② SERP 分析

**解決**：
```bash
python analyze/serp_fetcher.py
```

### 3. API 速率限制

DSPy 會大量調用 OpenAI API，注意：
- 使用 `config.dspy_model_small` (gpt-4o-mini) 節省成本
- `run_dspy_analysis.py` 內建速率限制保護

---

## 📈 預期效果

### 輸入（來自 Stage ②）
- 24 個高潛力查詢
- 每個查詢 8-10 個競爭者結果
- 平均 3.2 個 PAA 問題
- 83.3% AISEO 觸發率

### 輸出（Stage ③）
- 24 個完整文章大綱
- 每個大綱包含：
  - 3-5 個內容缺口機會
  - 4 個結構化區塊
  - PAA 問題分配
  - 字數規劃

### 下一步（Stage ④）
使用生成的 `article_outlines.json` 進行實際文章撰寫

---

## 📝 開發日誌

### 2025-11-20
- ✅ 完成三個 DSPy 模組（ContentSummarizer, GapAnalyzer, OutlineGenerator）
- ✅ 修正 DSPy 2.6+ API 相容性問題
- ✅ 創建主執行腳本 `run_dspy_analysis.py`
- ✅ 創建測試腳本 `test_dspy_single.py`
- 🔄 正在測試：單一查詢完整流程

### 下一步計畫
1. 完成單一查詢測試驗證
2. 運行完整 24 個查詢分析
3. 開始 Stage ④ 文章生成模組
