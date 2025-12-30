# -*- coding: utf-8 -*-
"""
生成 10 個 FAQ 問題的答案
"""

import os
import sys
import io
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.absolute()
load_dotenv(ROOT_DIR / "config" / "secrets.env")

# 初始化 OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 10 個問題列表
questions = [
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

print("\n" + "=" * 60)
print("📝 生成 10 個 FAQ 答案")
print("=" * 60)

faq_results = []

for i, question in enumerate(questions, 1):
    print(f"\n正在生成 FAQ {i}/10: {question}")

    # 判斷語言
    is_english = any(ord(char) < 128 and char.isalpha() for char in question)
    answer_lang = "英文" if is_english else "繁體中文"

    # 生成提示
    prompt = f"""你是一位專業的高壓滅菌鍋（Autoclave）領域專家。請為以下問題提供專業、實用、具體的回答。

問題：{question}

回答要求：
1. 語言：使用{answer_lang}回答
2. 字數：200-300 字
3. 內容：實用、專業、具體，提供可操作的建議
4. 如果適用，提及具體標準或規範（如 ISO、EN、FDA 等）
5. 避免過度技術細節，但要專業準確
6. 使用台灣繁體中文專業術語（如果是中文問題）
7. 避免使用「本文」、「以下」等指涉性詞彙
8. 避免 AI 寫作痕跡（如「深入探索」、「全面性的」）

請直接提供答案，不需要重複問題。
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是一位專業的高壓滅菌鍋領域專家，提供實用且專業的建議。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )

        answer = response.choices[0].message.content.strip()

        faq_results.append({
            "question": question,
            "answer": answer,
            "language": "en" if is_english else "zh-TW"
        })

        print(f"✅ 生成完成（{len(answer)} 字）")

    except Exception as e:
        print(f"❌ 生成失敗: {e}")
        faq_results.append({
            "question": question,
            "answer": f"[生成失敗: {str(e)}]",
            "language": "en" if is_english else "zh-TW"
        })

# 儲存結果
output_file = ROOT_DIR / "data" / "faq_10_questions.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(faq_results, f, ensure_ascii=False, indent=2)

print(f"\n\n✅ 生成完成！結果已儲存至：{output_file}")

# 同時生成 Markdown 格式
md_output_file = ROOT_DIR / "data" / "faq_10_questions.md"
with open(md_output_file, "w", encoding="utf-8") as f:
    f.write("# 高壓滅菌鍋 FAQ（10 個問題）\n\n")

    for i, faq in enumerate(faq_results, 1):
        f.write(f"## Q{i}: {faq['question']}\n\n")
        f.write(f"**A:** {faq['answer']}\n\n")
        f.write("---\n\n")

print(f"✅ Markdown 格式已儲存至：{md_output_file}")

# 在控制台輸出結果
print("\n" + "=" * 60)
print("📋 FAQ 內容預覽")
print("=" * 60)

for i, faq in enumerate(faq_results, 1):
    print(f"\n\n### Q{i}: {faq['question']}\n")
    print(f"A: {faq['answer']}\n")
    print("-" * 60)
