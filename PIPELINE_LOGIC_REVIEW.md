# LLM-SEO Pipeline 完整流程邏輯梳理

## 📋 總覽

**目標**：為單一主題（例如「微量吸管」）生成一篇 3,200-3,500 字的 SEO/AISEO 優化文章

**核心架構**：
```
Stage ① Query Pool (查詢研究池)
    ↓
Stage ② SERP Analysis (競爭環境分析)
    ↓
Stage ③ DSPy Analysis (內容策略分析)
    ↓
Stage ④ Article Generation (文章生成)
    ↓
Stage ⑤ Refinement (去 AI 化 + 優化)
```

---

## Stage ① Query Pool Generation (查詢池生成)

### 🎯 目的
生成 **多角度查詢池**，用於全面研究主題，而非生成多篇文章

### 📂 腳本
- [analyze/queries.py](analyze/queries.py)

### 🔄 流程

1. **載入配置** (config/settings.yaml)
   ```yaml
   topic: "微量吸管"
   query_generation:
     pool_size: 20
     base_seeds:
       - "微量吸管"
       - "電動微量吸管"
       - "吸管尖"
       - "微量吸管 校正"
       - "移液管尖端相容性"
   ```

2. **生成查詢**
   - **手動種子**（BASE_SEEDS）：5 個人工定義的核心查詢（避免語義漂移）
   - **LLM 擴展**：使用 GPT-4o-mini 生成 15 個額外查詢
   - **生成策略**：涵蓋資訊/商業/比較/維護/校正/錯誤排查等多角度
   - **語言限制**：只生成繁體中文（台灣用語）

3. **語言檢測 & 向量化**
   - 過濾非中文查詢（如果 LLM 意外生成英文）
   - 使用 OpenAI text-embedding-3-small 為每個查詢生成向量

4. **輸出**
   ```
   data/query_pool.csv          # 原始查詢池（20 條）
   data/query_vectors.json      # 查詢向量
   ```

### ✅ 當前狀態
- 查詢池：23 條查詢（合併後）
- 範例：
  1. 微量吸管
  2. 電動微量吸管
  3. 微量吸管 校正
  4. 微量吸管的使用方法與技巧
  5. ...

### 🔍 邏輯驗證問題
1. ✅ **目的正確**：查詢池用於研究，不是為每個查詢生成文章
2. ⚠️ **語義合併**：有 merge_queries.py 腳本，但 query_pool_merged.csv 只有 23 條（原始 20 條 + 3 條合併？）
3. ✅ **台灣繁體中文**：語言檢測正確

---

## Stage ② Semantic Scoring (語義評分)

### 🎯 目的
評估每個查詢的 **SEO 潛力**，篩選出高價值查詢

### 📂 腳本
- [analyze/semantic_score.py](analyze/semantic_score.py)

### 🔄 流程

1. **三維評分體系**
   - **Coverage (覆蓋度)** - 使用 Tavily API 檢測搜尋結果數量
   - **Relevance (相關性)** - Embedding cosine similarity + LLM 混合評分
   - **Density (密度)** - 向量聚類分析，檢測查詢群集密度

2. **權重配置** (settings.yaml)
   ```yaml
   scores:
     embedding_weight: 0.6    # Embedding 權重
     llm_weight: 0.4          # LLM 權重
     coverage_w: 0.4          # Coverage 權重
     relevance_w: 0.4         # Relevance 權重
     density_w: 0.2           # Density 權重
     min_score_threshold: 4.5 # 最低分數
     top_queries_limit: 15    # 保留前 15 個查詢
   ```

3. **計算公式**
   ```
   最終分數 = (Coverage × 0.4) + (Relevance × 0.4) + (Density × 0.2)
   Relevance = (Embedding分數 × 0.6) + (LLM分數 × 0.4)
   ```

4. **輸出**
   ```
   data/semantic_scores.csv     # 所有查詢的評分結果
   ```

### ✅ 當前狀態
- 已完成 23 個查詢評分
- 輸出：semantic_scores.csv

### 🔍 邏輯驗證問題
1. ✅ **評分體系合理**：三維評分涵蓋搜尋潛力、相關性、內容密度
2. ⚠️ **篩選邏輯**：top_queries_limit 設定為 15，但後續 SERP 分析了 24 個查詢？
3. ❓ **篩選未執行**：semantic_scores.csv 應該會產生篩選後的查詢池，但似乎沒有被使用？

---

## Stage ② SERP Analysis (SERP 分析)

### 🎯 目的
分析 Google SERP，提取競爭者內容、PAA 問題、AI Overview 觸發狀態

### 📂 腳本
- [analyze/serp_fetcher.py](analyze/serp_fetcher.py)

### 🔄 流程

1. **載入查詢池**
   - 讀取 `query_pool_merged.csv`（23 條查詢）
   - **問題**：為什麼不使用 semantic_scores.csv 篩選後的查詢？

2. **SERP 抓取** (使用 SerpAPI)
   - **Organic Results**：前 10 個自然搜尋結果（title, snippet, domain）
   - **AI Overview**：檢測是否觸發 Google AI Overview（AISEO 信號）
   - **People Also Ask (PAA)**：相關問題列表
   - **Related Searches**：相關搜尋

3. **分析指標**
   ```python
   {
     "query": "微量吸管",
     "ai_overview": {
       "present": true,          # 是否觸發 AI Overview
       "content": "..."          # AI Overview 內容
     },
     "organic_results": [        # 前 10 個競爭者
       {
         "position": 1,
         "title": "...",
         "snippet": "...",
         "domain": "..."
       }
     ],
     "people_also_ask": [        # PAA 問題
       {"question": "...", "answer": "..."}
     ],
     "related_searches": ["..."] # 相關搜尋
   }
   ```

4. **輸出**
   ```
   data/serp_analysis.json      # 包含所有 24 個查詢的 SERP 數據
   ```

### ✅ 當前狀態
- SERP 分析完成：24 個查詢
- AISEO 觸發率：83.33% (20/24 觸發 AI Overview)
- 平均競爭者數：8-10 個/查詢

### 🔍 邏輯驗證問題
1. ❓ **查詢來源不一致**：
   - semantic_score.py 設定 `top_queries_limit: 15`
   - 但 serp_fetcher.py 分析了 24 個查詢
   - **可能原因**：serp_fetcher 直接讀取 query_pool_merged.csv，跳過了評分篩選？

2. ✅ **SERP 數據完整**：提取了所有需要的數據（競爭者、PAA、AI Overview）

3. ⚠️ **潛在問題**：如果 24 個查詢都用於分析，semantic_scoring 的篩選邏輯沒有被使用

---

## Stage ③ DSPy Analysis (DSPy 分析)

### 🎯 目的
使用 DSPy 分析競爭者內容、找出內容缺口、生成文章大綱

### 📂 腳本
- [analyze/dspy_modules.py](analyze/dspy_modules.py) - 三個 DSPy 模組
- [analyze/run_dspy_analysis.py](analyze/run_dspy_analysis.py) - 主執行腳本

### 🔄 流程

#### **3.1 ContentSummarizer（競爭者內容總結）**
- **輸入**：查詢 + 競爭者的 title & snippet（來自 serp_analysis.json）
- **DSPy Signature**：
  ```python
  class ContentSummarizerSignature(dspy.Signature):
      query: str = dspy.InputField()
      title: str = dspy.InputField()
      snippet: str = dspy.InputField()
      position: int = dspy.InputField()

      key_points: List[str] = dspy.OutputField(desc="3-5 個關鍵點")
      content_depth: str = dspy.OutputField(desc="shallow/medium/deep")
      unique_value: str = dspy.OutputField(desc="獨特價值點")
  ```
- **輸出**：每個競爭者的總結（key_points, content_depth, unique_value）

#### **3.2 GapAnalyzer（內容缺口分析）**
- **輸入**：
  - 競爭者總結（來自 ContentSummarizer）
  - PAA 問題
  - AISEO 觸發狀態
  - 平均內容深度
- **DSPy Signature**：
  ```python
  class GapAnalyzerSignature(dspy.Signature):
      query: str = dspy.InputField()
      competitor_summaries: str = dspy.InputField()
      paa_questions: str = dspy.InputField()
      aiseo_triggered: bool = dspy.InputField()
      avg_content_depth: str = dspy.InputField()

      gaps: List[Dict] = dspy.OutputField(desc="3-5 個內容缺口")
      priority_ranking: List[str] = dspy.OutputField()
  ```
- **輸出**：3-5 個排序後的內容缺口機會
  - gap_type: AISEO/PAA/Depth/Coverage
  - opportunity_score: 0-1
  - recommended_action

#### **3.3 OutlineGenerator（文章大綱生成）**
- **輸入**：
  - 內容缺口（來自 GapAnalyzer）
  - PAA 問題
  - AISEO 觸發狀態
  - 4-block 配置（來自 settings.yaml）
- **DSPy Signature**：
  ```python
  class OutlineGeneratorSignature(dspy.Signature):
      query: str = dspy.InputField()
      content_gaps: str = dspy.InputField()
      paa_questions: str = dspy.InputField()
      aiseo_triggered: bool = dspy.InputField()
      block_requirements: str = dspy.InputField()

      outline: Dict = dspy.OutputField(desc="4-block 文章大綱")
  ```
- **輸出**：結構化的 4-block 文章大綱
  ```json
  {
    "topic": "微量吸管",
    "blocks": [
      {
        "block_name": "quick_summary",
        "block_title": "微量吸管快速總覽",
        "word_count_target": "40-50",
        "subsections": [...]
      },
      ...
    ]
  }
  ```

### ✅ 當前狀態
- 已完成 24 個查詢的 DSPy 分析
- 輸出：article_outlines.json（包含 24 個查詢的大綱）
- 總內容缺口：120 個
- 平均缺口數/查詢：5 個

### 🔍 邏輯驗證問題
1. ❓ **24 個大綱的用途**：
   - 生成了 24 個不同查詢的大綱
   - 但最終只需要生成 **1 篇文章**
   - **問題**：這 24 個大綱是否應該「合併」成一個統一大綱？

2. ⚠️ **GapAnalyzer 返回 0 缺口**：
   - 所有 24 個查詢的 content_gaps 都是空陣列 `[]`
   - 可能原因：DSPy prompts 需要優化，或競爭者已很完整

3. ✅ **大綱結構正確**：4-block 結構符合設計

---

## Stage ④ Article Generation (文章生成)

### 🎯 目的
基於 article_outlines.json 生成完整文章

### 📂 腳本
- [generate/article_writer.py](generate/article_writer.py) - ArticleWriter 模組
- [generate_target_article.py](generate_target_article.py) - 單篇文章生成腳本

### 🔄 流程

1. **載入大綱數據**
   - 從 article_outlines.json 選擇目標查詢
   - 例如：「微量吸管的使用方法與技巧」

2. **區塊生成** (使用 DSPy ArticleBlockWriter)
   - 依序生成 4 個區塊：
     1. **quick_summary** (40-50 字)
     2. **definition** (100-150 字)
     3. **uses** (100-150 字，條列式)
     4. **faq** (10 Q&A，每個回答 ≤300 字)

3. **DSPy Signature**
   ```python
   class ArticleBlockSignature(dspy.Signature):
       query: str = dspy.InputField()
       block_name: str = dspy.InputField()
       block_requirements: str = dspy.InputField()
       competitor_insights: str = dspy.InputField()
       paa_questions: str = dspy.InputField()
       aiseo_mode: bool = dspy.InputField()

       content: str = dspy.OutputField(desc="Markdown 格式內容")
   ```

4. **輸出**
   ```
   data/articles/{query}.md     # Markdown 文章
   data/articles/{query}.json   # JSON 結構化數據
   ```

### ✅ 當前狀態
- 已生成文章：「微量吸管的使用方法與技巧」
- 實際字數：1,174 字（目標 3,200-3,500 字）

### 🔍 邏輯驗證問題

#### **❌ 字數嚴重不足**
| 區塊 | 目標字數 | 實際字數 | 狀態 |
|------|---------|---------|------|
| quick_summary | 40-50 | 52 | ⚠️ 略超 |
| definition | 100-150 | 188 | ⚠️ 超過 |
| uses | 100-150 | 310 | ❌ 大幅超過 |
| **faq** | **3000** | **624** | ❌ 嚴重不足 |
| **總字數** | **3,200-3,500** | **1,174** | ❌ 遠低於目標 |

#### **問題分析**

1. **FAQ 區塊字數不足（最嚴重）**
   - 目標：10 個問答 × 300 字 = 3,000 字
   - 實際：624 字（只有約 5 個問答）
   - **原因**：DSPy ArticleBlockSignature 沒有明確指定「必須生成 10 個問答」

2. **Definition/Uses 超過字數**
   - Definition: 188 字（目標 100-150）
   - Uses: 310 字（目標 100-150）
   - **原因**：DSPy 沒有嚴格遵守字數上限

3. **block_requirements 傳遞不完整**
   - 當前 block_requirements 格式：
     ```python
     requirements = f"""
     字數要求：{block_config.get('word_count_min', 100)}-{block_config.get('word_count_max', 150)} 字
     必須包含：{', '.join(block_config.get('must_include', []))}
     """
     ```
   - **缺少**：FAQ 的 `questions_min` 和 `questions_max` 配置未傳遞

---

## 🚨 關鍵問題總結

### **問題 1：查詢池篩選邏輯斷裂**

**現象**：
- semantic_score.py 設定 `top_queries_limit: 15`（只保留前 15 個高分查詢）
- 但 serp_fetcher.py 分析了 **24 個查詢**（來自 query_pool_merged.csv）

**原因**：
serp_fetcher.py 直接讀取 query_pool_merged.csv，跳過了 semantic_scores.csv 的篩選結果

**影響**：
- Tavily API、SerpAPI 成本增加（多分析了 9 個低分查詢）
- DSPy 分析時間增加

**建議修正**：
```python
# serp_fetcher.py 應該讀取篩選後的查詢
scores_df = pd.read_csv(config.data_dir / "semantic_scores.csv")
top_queries = scores_df.nlargest(config.top_queries_limit, "final_score")["query"].tolist()
```

---

### **問題 2：24 個大綱 vs. 1 篇文章的邏輯不一致**

**現象**：
- Stage ③ 生成了 24 個查詢的獨立大綱
- 但目標是生成 **1 篇文章**

**原因**：
原始設計意圖不明確：
- **方案 A**：24 個查詢用於「全面研究」，最終合併成 1 篇文章
- **方案 B**：24 個查詢生成 24 篇文章

**當前實作**：
- 選擇「微量吸管的使用方法與技巧」這 1 個查詢生成文章
- 其他 23 個大綱未使用

**建議策略**：

#### **策略 A：單一查詢模式（當前做法）**
```
24 個查詢 → 選擇最佳 1 個查詢 → 生成 1 篇文章
```
- ✅ 簡單直接
- ❌ 浪費其他 23 個查詢的研究成果

#### **策略 B：多角度聚合模式（推薦）**
```
24 個查詢 → 聚合所有 PAA 問題 → 合併競爭者洞察 → 生成 1 篇全面文章
```
- ✅ 充分利用所有查詢的研究成果
- ✅ 文章內容更全面、更深入
- ❌ 需要新增「聚合模組」

**實作建議**：
```python
# 新增 analyze/aggregate_insights.py
def aggregate_all_outlines(outlines_data):
    """
    合併所有 24 個查詢的洞察，生成統一的文章策略
    """
    all_paa = []
    all_competitor_insights = []
    all_gaps = []

    for outline in outlines_data["outlines"]:
        all_paa.extend(outline.get("paa_questions", []))
        all_competitor_insights.extend(outline["competitor_summaries"])
        all_gaps.extend(outline["content_gaps"])

    # 去重 PAA 問題（基於語義相似度）
    unique_paa = deduplicate_paa(all_paa)

    # 聚合競爭者洞察（提取共同點 + 獨特點）
    aggregated_insights = aggregate_competitor_insights(all_competitor_insights)

    return {
        "aggregated_paa": unique_paa[:10],  # 選擇最相關的 10 個問題
        "aggregated_insights": aggregated_insights,
        "top_gaps": sorted(all_gaps, key=lambda x: x["opportunity_score"], reverse=True)[:5]
    }
```

---

### **問題 3：FAQ 區塊生成邏輯錯誤**

**現象**：
- 目標：10 個問答，每個回答 ≤300 字（共 3,000 字）
- 實際：5 個問答，共 624 字

**原因**：
ArticleBlockSignature 的 block_requirements 沒有明確傳遞 FAQ 的特殊要求

**當前代碼**（article_writer.py:82-86）：
```python
requirements = f"""
字數要求：{block_config.get('word_count_min', 100)}-{block_config.get('word_count_max', 150)} 字
必須包含：{', '.join(block_config.get('must_include', []))}
"""
```

**問題**：
- FAQ 的 `questions_min`、`questions_max`、`answer_max_words` 沒有被傳遞

**修正方案**：
```python
# article_writer.py 修正
requirements = f"""
字數要求：{block_config.get('word_count_min', 100)}-{block_config.get('word_count_max', 150)} 字
必須包含：{', '.join(block_config.get('must_include', []))}
"""

# 針對 FAQ 區塊增強
if block_name == "faq":
    q_min = block_config.get('questions_min', 10)
    q_max = block_config.get('questions_max', 10)
    ans_max = block_config.get('answer_max_words', 300)
    requirements += f"""

**FAQ 特殊要求**：
- 必須生成 {q_min}-{q_max} 個問答（Q&A）
- 每個回答不超過 {ans_max} 字
- 總字數目標：{block_config.get('word_count_min', 3000)} 字
- 使用 Markdown 格式：## 問題標題\\n\\n回答內容
"""
```

---

### **問題 4：DSPy 輸出不穩定**

**現象**：
- GapAnalyzer 返回 0 個缺口（所有 24 個查詢）
- FAQ 生成數量不足

**原因**：
DSPy 的 ChainOfThought 在沒有明確 few-shot examples 的情況下，輸出不穩定

**建議優化**：

#### **方案 A：增加 Few-Shot Examples**
```python
# dspy_modules.py
class ArticleBlockWriter(dspy.Module):
    def __init__(self):
        super().__init__()
        self.write = dspy.ChainOfThought(ArticleBlockSignature)

        # 增加 Few-Shot Examples
        if block_name == "faq":
            self.write.demos = [
                dspy.Example(
                    query="微量吸管",
                    block_name="faq",
                    block_requirements="生成 10 個問答",
                    content="""
## 微量吸管使用方法？
微量吸管的正確使用對於確保實驗結果的準確性至關重要...（300字）

## 微量吸管多久校正？
微量吸管的校正頻率取決於使用頻率...（300字）

（共 10 個問答）
                    """
                )
            ]
```

#### **方案 B：使用 Constraints 強制輸出格式**
```python
class FAQBlockSignature(dspy.Signature):
    """專門用於 FAQ 區塊生成"""
    query: str = dspy.InputField()
    paa_questions: List[str] = dspy.InputField(desc="必須回答的 PAA 問題列表")
    num_questions: int = dspy.InputField(desc="必須生成的問答數量")
    max_words_per_answer: int = dspy.InputField(desc="每個回答的最大字數")

    questions: List[str] = dspy.OutputField(desc="問題列表，必須包含所有 PAA 問題")
    answers: List[str] = dspy.OutputField(desc="回答列表，每個回答不超過 max_words_per_answer")
```

---

## ✅ 修正優先順序

### **P0（最緊急）**
1. **修正 FAQ 生成邏輯**
   - 確保生成 10 個問答
   - 每個回答 250-300 字
   - 總字數達到 3,000 字

### **P1（重要）**
2. **修正查詢篩選邏輯**
   - serp_fetcher.py 應該讀取 semantic_scores.csv 的篩選結果
   - 只分析 top 15 個查詢

3. **決定多查詢策略**
   - 策略 A：單一查詢模式（簡單，但浪費資源）
   - 策略 B：聚合模式（推薦，需要開發聚合模組）

### **P2（優化）**
4. **增強 DSPy 穩定性**
   - 增加 Few-Shot Examples
   - 優化 GapAnalyzer prompts

---

## 🎯 建議的流程修正版本

```
Stage ① Query Pool (20 條查詢)
    ↓
Stage ① Semantic Scoring (篩選出 15 條高分查詢)  ← 修正：確保篩選被使用
    ↓
Stage ② SERP Analysis (分析 15 條查詢)  ← 修正：讀取篩選結果
    ↓
Stage ③ DSPy Analysis (分析 15 條查詢)
    ↓
【新增】Stage ③.5 Aggregate Insights (聚合 15 條查詢的洞察)  ← 新增模組
    ↓
Stage ④ Article Generation (基於聚合洞察生成 1 篇文章)  ← 修正：FAQ 生成邏輯
    ↓
Stage ⑤ Refinement (去 AI 化 + 優化)
```

---

## 📝 總結

### **核心邏輯驗證**

| 階段 | 目的 | 邏輯狀態 | 關鍵問題 |
|------|------|----------|----------|
| Stage ① | 生成多角度查詢池 | ✅ 正確 | - |
| Semantic Scoring | 篩選高價值查詢 | ⚠️ 部分失效 | 篩選結果未被使用 |
| Stage ② | SERP 競爭分析 | ✅ 正確 | 查詢來源錯誤（讀取未篩選的池） |
| Stage ③ | DSPy 內容策略分析 | ✅ 結構正確 | GapAnalyzer 返回 0 缺口 |
| **Stage ④** | **文章生成** | **❌ 字數嚴重不足** | **FAQ 只生成 624/3000 字** |

### **最關鍵的修正**
1. **FAQ 區塊生成邏輯** - 必須修正，否則無法達到 3,200-3,500 字目標
2. **查詢篩選邏輯** - 建議修正，節省 API 成本
3. **多查詢聚合策略** - 建議新增，充分利用研究成果

---

您想要我先修正哪個問題？我建議優先順序：
1. **修正 FAQ 生成邏輯**（最緊急，直接影響文章字數）
2. **決定多查詢策略**（影響整體架構）
3. **修正查詢篩選邏輯**（優化，節省成本）
