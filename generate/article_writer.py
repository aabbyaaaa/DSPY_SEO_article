# -*- coding: utf-8 -*-
"""
LLM-SEO Pipeline Stage ④: Article Writer (v1.0)
使用 DSPy 生成完整的 SEO 優化文章
"""

import dspy
from typing import List, Dict
from pydantic import BaseModel, Field


# ================================================
# ArticleBlock - 單個區塊生成
# ================================================

class BlockContent(BaseModel):
    """單個區塊的內容"""
    block_name: str = Field(description="區塊名稱")
    content: str = Field(description="區塊內容（Markdown 格式）")
    word_count: int = Field(description="實際字數")


class ArticleBlockSignature(dspy.Signature):
    """生成單個文章區塊的內容"""

    # 輸入
    query: str = dspy.InputField(desc="主查詢關鍵字")
    block_name: str = dspy.InputField(desc="區塊名稱：quick_summary/definition/uses/faq")
    block_requirements: str = dspy.InputField(desc="區塊要求（字數、必須包含的元素）")
    competitor_insights: str = dspy.InputField(desc="競爭者內容分析（關鍵點總結）")
    paa_questions: str = dspy.InputField(desc="People Also Ask 問題列表")
    aiseo_mode: bool = dspy.InputField(desc="是否啟用 AISEO 優化模式")

    # 輸出
    content: str = dspy.OutputField(desc="區塊內容，使用 Markdown 格式，包含適當的標題、列表、段落")


class ArticleBlockWriter(dspy.Module):
    """文章區塊生成器"""

    def __init__(self):
        super().__init__()
        self.write = dspy.ChainOfThought(ArticleBlockSignature)

    def forward(
        self,
        query: str,
        block_name: str,
        block_config: Dict,
        competitor_summaries: List[Dict],
        paa_questions: List[Dict],
        aiseo_triggered: bool
    ) -> BlockContent:
        """
        生成單個區塊的內容

        Args:
            query: 查詢關鍵字
            block_name: 區塊名稱
            block_config: 區塊配置（字數要求等）
            competitor_summaries: 競爭者總結
            paa_questions: PAA 問題
            aiseo_triggered: 是否觸發 AI Overview

        Returns:
            BlockContent: 生成的區塊內容
        """
        import json

        # 準備競爭者洞察
        insights = []
        for summary in competitor_summaries[:5]:  # 只取前 5 個
            insights.append(f"【{summary['domain']}】")
            insights.extend([f"  - {point}" for point in summary['key_points']])

        competitor_text = "\n".join(insights)

        # 準備 PAA 問題
        paa_text = "\n".join([f"- {q.get('question', '')}" for q in paa_questions])

        # 準備區塊要求
        requirements = f"""
字數要求：{block_config.get('word_count_min', 100)}-{block_config.get('word_count_max', 150)} 字
必須包含：{', '.join(block_config.get('must_include', []))}
        """

        try:
            pred = self.write(
                query=query,
                block_name=block_name,
                block_requirements=requirements,
                competitor_insights=competitor_text,
                paa_questions=paa_text,
                aiseo_mode=aiseo_triggered
            )

            content = pred.content
            word_count = len(content.replace(" ", "").replace("\n", ""))

            return BlockContent(
                block_name=block_name,
                content=content,
                word_count=word_count
            )

        except Exception as e:
            print(f"⚠️ 區塊生成失敗 @ {block_name}: {e}")
            return BlockContent(
                block_name=block_name,
                content=f"# {block_name}\n\n[內容生成失敗]",
                word_count=0
            )


# ================================================
# ArticleWriter - 完整文章生成
# ================================================

class Article(BaseModel):
    """完整文章"""
    title: str = Field(description="文章標題")
    query: str = Field(description="主查詢")
    blocks: List[BlockContent] = Field(description="所有區塊內容")
    total_word_count: int = Field(description="總字數")
    metadata: Dict = Field(description="元數據")


class ArticleWriter:
    """完整文章生成器"""

    def __init__(self, block_config: Dict):
        self.block_config = block_config
        self.block_writer = ArticleBlockWriter()

    def generate(
        self,
        query: str,
        outline_data: Dict,
        aiseo_triggered: bool = False
    ) -> Article:
        """
        生成完整文章

        Args:
            query: 主查詢
            outline_data: 來自 article_outlines.json 的數據
            aiseo_triggered: 是否觸發 AISEO

        Returns:
            Article: 完整文章對象
        """
        print(f"\n📝 生成文章：{query}")

        competitor_summaries = outline_data.get("competitor_summaries", [])
        paa_questions = outline_data.get("paa_questions", [])

        blocks = []
        block_order = ["quick_summary", "definition", "uses", "faq"]

        for block_name in block_order:
            block_cfg = self.block_config.get(block_name, {})

            print(f"   生成區塊：{block_name} ({block_cfg.get('word_count_min', 0)}-{block_cfg.get('word_count_max', 0)} 字)")

            block_content = self.block_writer.forward(
                query=query,
                block_name=block_name,
                block_config=block_cfg,
                competitor_summaries=competitor_summaries,
                paa_questions=paa_questions,
                aiseo_triggered=aiseo_triggered
            )

            blocks.append(block_content)
            print(f"      ✅ 完成：{block_content.word_count} 字")

        total_words = sum(b.word_count for b in blocks)

        return Article(
            title=f"{query}完整指南",
            query=query,
            blocks=blocks,
            total_word_count=total_words,
            metadata={
                "aiseo_optimized": aiseo_triggered,
                "paa_count": len(paa_questions),
                "competitor_count": len(competitor_summaries)
            }
        )

    def to_markdown(self, article: Article) -> str:
        """將文章轉換為 Markdown 格式"""
        lines = [
            f"# {article.title}",
            "",
            f"> **關鍵字**: {article.query}",
            f"> **總字數**: {article.total_word_count} 字",
            f"> **AISEO 優化**: {'是' if article.metadata['aiseo_optimized'] else '否'}",
            "",
            "---",
            ""
        ]

        for block in article.blocks:
            lines.append(block.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)
