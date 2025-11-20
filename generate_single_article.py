# -*- coding: utf-8 -*-
"""
生成單篇文章測試腳本
"""

import os, json, sys, io
from pathlib import Path

# Windows UTF-8 support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config
from analyze.dspy_modules import init_dspy
from generate.article_writer import ArticleWriter

print("\n" + "=" * 60)
print("📝 單篇文章生成測試")
print("=" * 60)

# 初始化 DSPy
openai_key = config.get_openai_key()
init_dspy(config.dspy_model_main, openai_key)
print(f"✅ DSPy 初始化完成 (model: {config.dspy_model_main})")

# 載入大綱數據
outline_path = config.data_dir / "article_outlines.json"
with open(outline_path, "r", encoding="utf-8") as f:
    outlines_data = json.load(f)

# 選擇第一個查詢「微量吸管」
target_outline = outlines_data["outlines"][0]
query = target_outline["query"]
aiseo_triggered = target_outline["aiseo_triggered"]

print(f"\n📌 目標查詢：{query}")
print(f"   AISEO 觸發：{aiseo_triggered}")
print(f"   競爭者數量：{len(target_outline['competitor_summaries'])}")
print(f"   PAA 問題數：{len(target_outline.get('paa_questions', []))}")

# 初始化 ArticleWriter
writer = ArticleWriter(block_config=config.article_blocks)

# 生成文章
print("\n" + "=" * 60)
print("🚀 開始生成文章...")
print("=" * 60)

article = writer.generate(
    query=query,
    outline_data=target_outline,
    aiseo_triggered=aiseo_triggered
)

print("\n" + "=" * 60)
print("✅ 文章生成完成！")
print("=" * 60)
print(f"標題：{article.title}")
print(f"總字數：{article.total_word_count} 字")
print(f"區塊數量：{len(article.blocks)}")

# 顯示各區塊字數
for block in article.blocks:
    print(f"  - {block.block_name}: {block.word_count} 字")

# 轉換為 Markdown 並儲存
markdown_content = writer.to_markdown(article)

output_dir = config.data_dir / "articles"
output_dir.mkdir(exist_ok=True)

output_path = output_dir / f"{query}.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(markdown_content)

print(f"\n📁 文章已儲存：{output_path}")

# 同時儲存 JSON 格式
json_path = output_dir / f"{query}.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(article.model_dump(), f, ensure_ascii=False, indent=2)

print(f"📁 JSON 已儲存：{json_path}")

print("\n" + "=" * 60)
print("🎉 完成！")
print("=" * 60)
