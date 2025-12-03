# DSPY_SEO產品分類頁

## ① 主題定義

### 我提供種子(關鍵字)

- 中英文都要給
  
    - settings.yaml
      
## ② 調研階段（Research Layer）

- 1、LLM生成50~80個查詢詞
  
    - 不要限定中英文，因為英文的查詢詞才能讓tavily抓英文資料
      
        - 英文的內容分數高很多 
          
            - queries.py 
              
                - 輸出：data/query_pool.csv
                  
                - 輸出：data/query_vectors.json (向量資料)
                  
- 1-ａ、語義去重合併：合併語義相似的查詢，避免重複計算　（非必要步驟）
  
    - merge_queries.py
      
        - 輸出：data/query_pool_merged.csv
          
        - 輸出：data/query_vectors_merged.json
          
- ２、再利用評分機制挑出20個詞到③階段
  
    - AI Coverage 0.5
      
        - 工具：Tavily API
          
    - Relevance 0.3
      
      >  文章是否「符合主題群集」   
      >   
        - 工具：embedding + GPT
          
    - Query Density 0.1
      
      >  語意集中度   
      >   
        - 工具：embedding clustering
          
    - SERP Coverage 0.1
      
        - 工具：SERP API
          
- 2、抓主題文本 / 蒐集頁面內容  
        > 蒐集前20個查詢詞的相關資料5個
  
    - 工具：Tavily extract！！！不要用search
      
        - 問題：他現在找的資料不一定是好的，同業寫的資料不一定ＯＫ，還是要加入國外的結果？
          
            - 要！要！要！加英文
              
        - 搞清楚Tavily他抓的資料是什麼，才能定義他抓的資料好不好
          
- note. 這階段為什麼不用 Tavily生成查詢詞
  
    - API太貴
      
    - 評分階段看tavily的AI覆蓋範圍應該足夠
      
## ③分析階段（Analysis Layer）

### Embedding（OpenAI text-embedding-3-large）→ 將每個段落轉向量。

### KMeans / cosine_similarity → 分群找主題關聯。

### GPT-4o-mini / Claude → 產出「主題摘要 + 缺口 + 大綱」

## ④ 草稿生成（Draft Layer）

### 產品分類頁的文章不需要生成草稿

- quick_summary
  
- definition
  
- uses
  
- faq
  
    - 熱門FAQ
      
    - 缺口FAQ
      
### 定義區塊內容、文字

- 各區塊提供模板
  
    - article_writer.py
      
## ⑤ 優化階段（Refine Layer）

### 去AI

- 先一步在settings.yaml做去AI化詞語
  
- 要用哪個工具去AI
  
    - 土法煉鋼：中翻英之後再翻中
      
- 要用哪個工具做AI分數檢測
  
### 要如何評分這個文章符合AI SEO的標準

- [建立評分系統](https://chatgpt.com/share/69206baf-91c8-800e-a58d-3783d8925f36)
  
    - 腳本？
      
