# -*- coding: utf-8 -*-
"""
使用 DSPy 模組生成 10 個 FAQ 問題
"""

import os
import sys
import io
import json
from pathlib import Path
from dotenv import load_dotenv
import dspy

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

# 載入環境變數
load_dotenv(ROOT_DIR / "config" / "secrets.env")

# 從 dspy_modules 導入 FAQ 生成器
from dspy_modules.article_generator import FAQGenerator

print("\n" + "=" * 60)
print("📝 使用 DSPy 模組生成 10 個 FAQ")
print("=" * 60)

# ================================================
# 步驟 1：初始化 DSPy 與 LLM
# ================================================
print("\n🔧 步驟 1：初始化 DSPy 與 LLM...")

# 配置 DSPy 使用 OpenAI（DSPy 3.0.4 最新 API）
# 使用 dspy.LM（統一的 LM 介面）
# 格式：dspy.LM("provider/model_name", api_key=...)
lm = dspy.LM('openai/gpt-4o', api_key=os.getenv("OPENAI_API_KEY"))
dspy.configure(lm=lm)

print("✅ DSPy 3.0.4 已配置完成（使用 gpt-4o 模型）")

# 測試 LM 是否正常工作（可選）
# test_result = lm("測試：高壓滅菌鍋的標準溫度是？", temperature=0.7)
# print(f"🧪 LM 測試結果：{test_result}")

# ================================================
# 步驟 2：準備輸入資料
# ================================================
print("\n📋 步驟 2：準備輸入資料...")

# 產品基本資訊
product_name = "高壓滅菌鍋"

# 10 個選定的 FAQ 問題
selected_questions = [
    "高壓滅菌的溫度和時間需求是什麼？",
    "高壓蒸氣滅菌保存期限？",
    "How to choose an autoclave?",
    "What are the factors of autoclave?",
    "Which is better Class N or B autoclave?",
    "What are the steps to use an autoclave?",
    "How often should the autoclave be cleaned and maintained?",
    "How to troubleshoot an autoclave?",
    "What are the safety precautions when handling an autoclave?",
    "What cannot be sterilized in an autoclave?"
]

# 前面區塊的內容（用於防止重複）
previous_content = """
高壓滅菌鍋是一種利用高溫高壓蒸汽進行滅菌的設備，廣泛應用於醫療、實驗室、食品工業等領域。
標準滅菌條件為 121°C、15-20 分鐘，或 134°C、3-5 分鐘。
主要用於手術器械、實驗室器材、培養基、廢棄物等的滅菌處理。
"""

print(f"產品名稱：{product_name}")
print(f"FAQ 問題數量：{len(selected_questions)} 個")
print(f"前面區塊內容長度：{len(previous_content)} 字")

# ================================================
# 步驟 3：使用 DSPy Signature 生成單一 FAQ
# ================================================
print("\n🤖 步驟 3：使用 DSPy ChainOfThought 生成 FAQ...")

# 創建 DSPy ChainOfThought 模組
faq_generator = dspy.ChainOfThought(FAQGenerator)

print("\n⚠️  注意：DSPy FAQGenerator 預設一次生成 10 個 Q&A")
print("如果要單獨生成每個問題，需要修改 Signature\n")

# 方法 A：使用原始 FAQGenerator（一次生成全部 10 個）
print("=" * 60)
print("方法 A：使用原始 FAQGenerator（一次生成全部 10 個 Q&A）")
print("=" * 60)

try:
    result = faq_generator(
        product_name=product_name,
        serp_paa=selected_questions,
        previous_content=previous_content
    )

    print("\n✅ 生成完成！")
    print("\n生成的 FAQ 內容：")
    print("-" * 60)
    print(result.faq)
    print("-" * 60)

    # 儲存結果
    output_file = ROOT_DIR / "data" / "faq_dspy_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result.faq)

    print(f"\n✅ 結果已儲存至：{output_file}")

except Exception as e:
    print(f"\n❌ 生成失敗：{e}")
    import traceback
    traceback.print_exc()

# ================================================
# 方法 B：單獨生成每個問題（需要自定義 Signature）
# ================================================
print("\n\n" + "=" * 60)
print("方法 B：單獨生成每個問題（自定義 Signature）")
print("=" * 60)

# 定義單一 FAQ 問題的 Signature
class SingleFAQGenerator(dspy.Signature):
    """生成單一 FAQ 問題的回答"""

    product_name: str = dspy.InputField(desc="產品名稱")
    question: str = dspy.InputField(desc="FAQ 問題")
    previous_content: str = dspy.InputField(desc="前面區塊內容（用於避免重複）")

    answer: str = dspy.OutputField(
        desc="""
        生成此問題的專業回答，要求：
        1. 字數：200-300 字
        2. 內容：實用、專業、具體
        3. 提及具體標準或規範（如適用）
        4. 使用台灣繁體中文（如果問題是中文）或英文（如果問題是英文）
        5. 避免重複前面區塊的內容
        6. 提供可操作的建議

        回答格式：
        直接提供答案內容，不需要重複問題。
        """
    )

# 創建單一 FAQ 生成器
single_faq_gen = dspy.ChainOfThought(SingleFAQGenerator)

print("\n正在逐一生成 10 個 FAQ 回答...\n")

faq_results = []

for i, question in enumerate(selected_questions, 1):
    print(f"正在生成 FAQ {i}/10: {question}")

    try:
        result = single_faq_gen(
            product_name=product_name,
            question=question,
            previous_content=previous_content
        )

        answer = result.answer.strip()

        faq_results.append({
            "question": question,
            "answer": answer,
            "language": "en" if any(ord(c) < 128 and c.isalpha() for c in question) else "zh-TW"
        })

        print(f"✅ 生成完成（{len(answer)} 字）\n")

    except Exception as e:
        print(f"❌ 生成失敗：{e}\n")
        faq_results.append({
            "question": question,
            "answer": f"[生成失敗: {str(e)}]",
            "language": "unknown"
        })

# 儲存結果（JSON 格式）
output_json = ROOT_DIR / "data" / "faq_dspy_individual.json"
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(faq_results, f, ensure_ascii=False, indent=2)

print(f"\n✅ JSON 結果已儲存至：{output_json}")

# 儲存結果（Markdown 格式）
output_md = ROOT_DIR / "data" / "faq_dspy_individual.md"
with open(output_md, "w", encoding="utf-8") as f:
    f.write("# 高壓滅菌鍋 FAQ（使用 DSPy 生成）\n\n")

    for i, faq in enumerate(faq_results, 1):
        f.write(f"## Q{i}: {faq['question']}\n\n")
        f.write(f"**A:** {faq['answer']}\n\n")
        f.write("---\n\n")

print(f"✅ Markdown 結果已儲存至：{output_md}")

# 在控制台輸出預覽
print("\n" + "=" * 60)
print("📋 FAQ 內容預覽（方法 B）")
print("=" * 60)

for i, faq in enumerate(faq_results[:3], 1):  # 只顯示前 3 個
    print(f"\n### Q{i}: {faq['question']}\n")
    print(f"A: {faq['answer']}\n")
    print("-" * 60)

print("\n（完整內容請查看生成的檔案）")

# ================================================
# 總結與說明
# ================================================
print("\n\n" + "=" * 60)
print("📚 DSPy 使用總結")
print("=" * 60)

print("""
兩種方法比較：

方法 A：使用原始 FAQGenerator（一次生成全部）
✅ 優點：
   - 一次性生成所有 FAQ，速度快
   - LLM 可以統一調整問題順序和風格
   - 符合原始 Signature 設計
❌ 缺點：
   - 可能超出 token 限制
   - 難以控制每個回答的質量
   - 如果中途失敗，所有結果都丟失

方法 B：單獨生成每個問題
✅ 優點：
   - 可以精確控制每個回答的質量
   - 容錯性高（單一問題失敗不影響其他）
   - 可以動態調整生成參數
   - 適合大量問題的場景
❌ 缺點：
   - 需要多次 API 調用（成本較高）
   - 整體風格可能不太一致

建議：
- 如果問題數量 ≤ 10 個，使用方法 A
- 如果問題數量 > 10 個或需要精確控制，使用方法 B
""")

print("\n✅ 程序執行完成！")
