# DSPy 3.0.4 使用指南

## 📌 概述

DSPy 3.0.4 是 Stanford NLP 開發的 LLM 程式框架，用於系統化地構建 LLM 應用。

- **官方網站**: https://dspy.ai
- **GitHub**: https://github.com/stanfordnlp/dspy
- **最新版本**: 3.0.4 (2025)

---

## 🔧 安裝

```bash
pip install dspy-ai
```

檢查版本：
```bash
pip list | findstr dspy
# 輸出：dspy-ai 3.0.4
```

---

## 🚀 快速開始

### **1. 基本配置（DSPy 3.0.4 最新 API）**

```python
import dspy
import os
from dotenv import load_dotenv

# 載入 API Key
load_dotenv("config/secrets.env")

# 初始化 LM（使用統一的 dspy.LM 介面）
lm = dspy.LM('openai/gpt-4o', api_key=os.getenv("OPENAI_API_KEY"))

# 配置 DSPy
dspy.configure(lm=lm)
```

**格式說明：**
- `dspy.LM("provider/model_name", api_key=...)`
- Provider: `openai`, `anthropic`, `cohere`, `together`, 等
- Model: 具體模型名稱（如 `gpt-4o`, `gpt-4o-mini`）

---

### **2. 支援的 LLM Providers**

```python
# OpenAI
lm = dspy.LM('openai/gpt-4o')

# Anthropic
lm = dspy.LM('anthropic/claude-3-5-sonnet-20241022')

# Cohere
lm = dspy.LM('cohere/command-r-plus')

# Together AI
lm = dspy.LM('together/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo')

# Google Gemini
lm = dspy.LM('google/gemini-1.5-pro')
```

---

### **3. 直接調用 LM（測試用）**

```python
# 簡單調用
result = lm("What is the boiling point of water?")
print(result)  # ['The boiling point of water is 100°C at sea level.']

# 帶參數調用
result = lm(
    "Explain autoclave sterilization in 50 words.",
    temperature=0.7,
    max_tokens=100
)
print(result)
```

---

## 📝 定義 DSPy Signature

DSPy Signature 定義了輸入和輸出的結構。

### **範例：FAQ 生成器**

```python
import dspy

class FAQGenerator(dspy.Signature):
    """生成產品常見問題的回答"""

    # 輸入欄位
    product_name: str = dspy.InputField(desc="產品名稱")
    question: str = dspy.InputField(desc="FAQ 問題")
    context: str = dspy.InputField(desc="產品相關背景資訊")

    # 輸出欄位
    answer: str = dspy.OutputField(
        desc="""
        生成專業的 FAQ 回答，要求：
        1. 字數：200-300 字
        2. 使用繁體中文（如果問題是中文）
        3. 提及相關標準或規範
        4. 提供實用建議
        """
    )
```

---

## 🧠 使用 DSPy 模組

DSPy 提供多種預建模組來執行推理。

### **1. ChainOfThought（鏈式思考）**

最常用的模組，適合需要推理的任務。

```python
# 創建 ChainOfThought 模組
faq_gen = dspy.ChainOfThought(FAQGenerator)

# 執行生成
result = faq_gen(
    product_name="高壓滅菌鍋",
    question="高壓滅菌的溫度和時間需求是什麼？",
    context="高壓滅菌鍋是一種利用高溫高壓蒸汽進行滅菌的設備..."
)

print(result.answer)
```

### **2. Predict（直接預測）**

不需要中間推理步驟，直接生成輸出。

```python
faq_gen = dspy.Predict(FAQGenerator)

result = faq_gen(
    product_name="高壓滅菌鍋",
    question="如何選擇合適的高壓滅菌鍋？",
    context="..."
)
```

### **3. ReAct（推理 + 行動）**

適合需要多步驟推理和工具調用的任務。

```python
class ResearchTask(dspy.Signature):
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()

researcher = dspy.ReAct(ResearchTask)
result = researcher(question="What are the key factors of autoclave?")
```

---

## 🔄 DSPy 2.x → 3.0 遷移指南

### **API 變化對照表**

| **功能** | **DSPy 2.x（舊版）** | **DSPy 3.0（新版）** |
|---------|-------------------|-------------------|
| **初始化 OpenAI** | `dspy.OpenAI(model="gpt-4")` | `dspy.LM("openai/gpt-4o")` |
| **初始化 Anthropic** | `dspy.Claude(model="claude-3")` | `dspy.LM("anthropic/claude-3-5-sonnet")` |
| **配置 DSPy** | `dspy.settings.configure(lm=lm)` | `dspy.configure(lm=lm)` |
| **模型名稱格式** | `"gpt-4"` | `"openai/gpt-4o"` |
| **默認參數** | 有硬編碼值 | `temperature=None`, `max_tokens=None` |

### **遷移範例**

**舊版（DSPy 2.x）：**
```python
import dspy

lm = dspy.OpenAI(model="gpt-4", max_tokens=500, temperature=0.7)
dspy.settings.configure(lm=lm)
```

**新版（DSPy 3.0）：**
```python
import dspy

lm = dspy.LM('openai/gpt-4o')  # 參數可選
dspy.configure(lm=lm)
```

---

## 📊 完整範例：批量生成 FAQ

```python
import dspy
import os
from dotenv import load_dotenv

# 1. 初始化
load_dotenv("config/secrets.env")
lm = dspy.LM('openai/gpt-4o', api_key=os.getenv("OPENAI_API_KEY"))
dspy.configure(lm=lm)

# 2. 定義 Signature
class SingleFAQGenerator(dspy.Signature):
    """生成單一 FAQ 回答"""
    product_name: str = dspy.InputField(desc="產品名稱")
    question: str = dspy.InputField(desc="問題")
    answer: str = dspy.OutputField(desc="專業回答（200-300字）")

# 3. 創建生成器
faq_gen = dspy.ChainOfThought(SingleFAQGenerator)

# 4. 批量生成
questions = [
    "高壓滅菌的溫度和時間需求是什麼？",
    "高壓蒸氣滅菌保存期限？",
    "How to choose an autoclave?",
]

results = []
for q in questions:
    result = faq_gen(product_name="高壓滅菌鍋", question=q)
    results.append({
        "question": q,
        "answer": result.answer
    })

# 5. 儲存結果
import json
with open("faq_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

---

## 🆕 DSPy 3.0.4 新特性

### **1. Anthropic Citation API 支援**

```python
lm = dspy.LM('anthropic/claude-3-5-sonnet-20241022')
dspy.configure(lm=lm)

# 使用 citation 功能
result = lm("Cite sources for autoclave standards.")
# 自動包含引用資訊
```

### **2. 工具執行增強**

```python
# 新的 ToolCall.execute 方法
from dspy import ToolCall

tool = ToolCall(name="search", args={"query": "autoclave"})
result = tool.execute()  # 簡化的工具調用
```

### **3. User-Agent Header**

DSPy 3.0.4 自動添加 User-Agent header，方便 API 追蹤和調試。

### **4. 更靈活的參數控制**

```python
# temperature 和 max_tokens 現在默認為 None
lm = dspy.LM('openai/gpt-4o')  # 使用模型默認值

# 或者明確指定
lm = dspy.LM('openai/gpt-4o', temperature=0.7, max_tokens=500)
```

---

## 🐛 常見問題排查

### **問題 1：AttributeError: module 'dspy' has no attribute 'OpenAI'**

**原因：** 使用了舊版 API（DSPy 2.x）

**解決方法：**
```python
# ❌ 舊版（不再支援）
lm = dspy.OpenAI(model="gpt-4")

# ✅ 新版（DSPy 3.0+）
lm = dspy.LM('openai/gpt-4o')
```

### **問題 2：API Key 未設定**

**解決方法：**
```python
import os
from dotenv import load_dotenv

load_dotenv("config/secrets.env")
lm = dspy.LM('openai/gpt-4o', api_key=os.getenv("OPENAI_API_KEY"))
```

或設定環境變數：
```bash
export OPENAI_API_KEY="sk-..."
```

### **問題 3：Token 限制超出**

**解決方法：**
```python
# 方法 1：限制 max_tokens
lm = dspy.LM('openai/gpt-4o', max_tokens=1000)

# 方法 2：使用更大的模型
lm = dspy.LM('openai/gpt-4-turbo')

# 方法 3：分批生成（見完整範例）
```

---

## 📚 進階主題

### **1. 自定義 Prompt**

```python
class CustomFAQGenerator(dspy.Signature):
    """自定義 prompt 的 FAQ 生成器"""

    question: str = dspy.InputField()
    answer: str = dspy.OutputField(
        desc="""
        請用以下格式回答：
        1. 直接回答（50字）
        2. 詳細說明（150字）
        3. 相關標準（50字）
        """
    )
```

### **2. 多語言支援**

```python
class BilingualFAQ(dspy.Signature):
    """雙語 FAQ 生成"""

    question_zh: str = dspy.InputField(desc="中文問題")
    question_en: str = dspy.InputField(desc="English question")

    answer_zh: str = dspy.OutputField(desc="中文回答")
    answer_en: str = dspy.OutputField(desc="English answer")
```

### **3. 使用 Cache**

DSPy 3.0.4 自動支援 caching，相同的輸入會使用快取結果：

```python
# 第一次調用（會實際調用 API）
result1 = faq_gen(product_name="高壓滅菌鍋", question="溫度需求？")

# 第二次調用（使用快取，不消耗 API quota）
result2 = faq_gen(product_name="高壓滅菌鍋", question="溫度需求？")
```

---

## 🔗 參考資源

- **官方文檔**: https://dspy.ai
- **GitHub**: https://github.com/stanfordnlp/dspy
- **Release Notes**: https://github.com/stanfordnlp/dspy/releases/tag/3.0.4
- **Discord 社群**: https://discord.gg/VzS6RHHK6F

---

## 📝 總結

DSPy 3.0.4 的主要改進：

✅ **統一的 LM 介面** - `dspy.LM("provider/model")`
✅ **更簡潔的配置** - `dspy.configure(lm=lm)`
✅ **靈活的參數控制** - 默認值改為 `None`
✅ **Anthropic Citation 支援** - 更好的來源歸因
✅ **工具執行增強** - `ToolCall.execute` 方法
✅ **自動 Caching** - 減少 API 調用成本

建議所有新項目使用 DSPy 3.0+ 的新 API，舊項目可以參考遷移指南逐步升級。
