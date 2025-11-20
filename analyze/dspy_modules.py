# -*- coding: utf-8 -*-
"""
LLM-SEO Pipeline Stage ③: DSPy Analysis Modules (v1.0)
-------------------------------------------------------
三個核心 DSPy 模組：
1. ContentSummarizer - 總結競爭者內容
2. GapAnalyzer - 找出內容缺口
3. OutlineGenerator - 生成文章大綱
"""

import dspy
from typing import List, Dict
from pydantic import BaseModel, Field


# ================================================
# 1️⃣ ContentSummarizer - 競爭者內容總結
# ================================================

class CompetitorSummary(BaseModel):
    """單個競爭者內容的總結"""
    position: int = Field(description="SERP 排名位置")
    domain: str = Field(description="競爭者域名")
    key_points: List[str] = Field(description="3-5 個關鍵點", min_items=3, max_items=5)
    content_depth: str = Field(description="內容深度評估：shallow/medium/deep")
    unique_value: str = Field(description="獨特價值點（如有）")


class ContentSummarizerSignature(dspy.Signature):
    """從競爭者的 title + snippet 提取關鍵資訊"""

    # 輸入
    query: str = dspy.InputField(desc="用戶搜尋查詢")
    title: str = dspy.InputField(desc="競爭者頁面標題")
    snippet: str = dspy.InputField(desc="競爭者頁面描述")
    position: int = dspy.InputField(desc="SERP 排名位置 (1-10)")

    # 輸出
    key_points: List[str] = dspy.OutputField(desc="提取 3-5 個關鍵點，每點 10-20 字")
    content_depth: str = dspy.OutputField(desc="內容深度：shallow (淺層) / medium (中等) / deep (深度)")
    unique_value: str = dspy.OutputField(desc="獨特價值點，若無則填 '無特殊亮點'")


class ContentSummarizer(dspy.Module):
    """競爭者內容總結模組"""

    def __init__(self):
        super().__init__()
        self.summarize = dspy.ChainOfThought(ContentSummarizerSignature)

    def forward(self, query: str, organic_results: List[Dict]) -> List[CompetitorSummary]:
        """
        處理一個查詢的所有競爭者結果

        Args:
            query: 搜尋查詢
            organic_results: SERP organic_results 列表

        Returns:
            List[CompetitorSummary]: 所有競爭者的總結
        """
        summaries = []

        for result in organic_results:
            try:
                pred = self.summarize(
                    query=query,
                    title=result.get("title", ""),
                    snippet=result.get("snippet", ""),
                    position=result.get("position", 0)
                )

                # 解析 key_points（處理字符串或列表）
                key_points = pred.key_points
                if isinstance(key_points, str):
                    # 如果是字符串，按換行符分割並清理
                    key_points = [
                        line.strip().lstrip('0123456789.-) ')
                        for line in key_points.split('\n')
                        if line.strip()
                    ]
                elif not isinstance(key_points, list):
                    key_points = [str(key_points)]

                # 確保至少有 3 個關鍵點
                if len(key_points) < 3:
                    print(f"⚠️ 關鍵點不足 ({len(key_points)})，跳過")
                    continue

                summaries.append(CompetitorSummary(
                    position=result.get("position", 0),
                    domain=result.get("domain", ""),
                    key_points=key_points[:5],  # 最多 5 個
                    content_depth=pred.content_depth,
                    unique_value=pred.unique_value
                ))
            except Exception as e:
                print(f"⚠️ 總結失敗 @ {result.get('title', 'N/A')}: {e}")
                continue

        return summaries


# ================================================
# 2️⃣ GapAnalyzer - 內容缺口分析
# ================================================

class ContentGap(BaseModel):
    """單個內容缺口機會"""
    gap_type: str = Field(description="缺口類型：AISEO/PAA/Depth/Coverage")
    description: str = Field(description="缺口描述 (50-100字)")
    opportunity_score: float = Field(description="機會分數 0-1", ge=0, le=1)
    recommended_action: str = Field(description="建議行動")
    related_paa: List[str] = Field(description="相關 PAA 問題", default_factory=list)


class GapAnalyzerSignature(dspy.Signature):
    """分析競爭者缺口，找出內容機會"""

    # 輸入
    query: str = dspy.InputField(desc="搜尋查詢")
    competitor_summaries: str = dspy.InputField(desc="所有競爭者的總結（JSON 格式）")
    paa_questions: str = dspy.InputField(desc="People Also Ask 問題列表")
    aiseo_triggered: bool = dspy.InputField(desc="是否觸發 AI Overview")
    avg_content_depth: str = dspy.InputField(desc="競爭者平均內容深度")

    # 輸出
    gaps: List[Dict] = dspy.OutputField(desc="3-5 個內容缺口機會，每個包含：gap_type, description, opportunity_score, recommended_action")
    priority_ranking: List[str] = dspy.OutputField(desc="缺口優先順序排序（按 opportunity_score 降序）")


class GapAnalyzer(dspy.Module):
    """內容缺口分析模組"""

    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(GapAnalyzerSignature)

    def forward(
        self,
        query: str,
        competitor_summaries: List[CompetitorSummary],
        paa_questions: List[Dict],
        aiseo_triggered: bool
    ) -> List[ContentGap]:
        """
        分析內容缺口

        Args:
            query: 搜尋查詢
            competitor_summaries: 競爭者總結列表
            paa_questions: PAA 問題列表
            aiseo_triggered: 是否觸發 AI Overview

        Returns:
            List[ContentGap]: 排序後的內容缺口機會
        """
        # 計算平均內容深度
        depth_counts = {"shallow": 0, "medium": 0, "deep": 0}
        for summary in competitor_summaries:
            depth_counts[summary.content_depth] = depth_counts.get(summary.content_depth, 0) + 1

        avg_depth = max(depth_counts, key=depth_counts.get) if depth_counts else "medium"

        # 準備輸入
        import json
        competitor_json = json.dumps([s.model_dump() for s in competitor_summaries], ensure_ascii=False, indent=2)
        paa_text = "\n".join([f"- {q.get('question', '')}" for q in paa_questions])

        try:
            pred = self.analyze(
                query=query,
                competitor_summaries=competitor_json,
                paa_questions=paa_text,
                aiseo_triggered=aiseo_triggered,
                avg_content_depth=avg_depth
            )

            # 解析輸出
            gaps = []
            if isinstance(pred.gaps, list):
                for gap_data in pred.gaps:
                    if isinstance(gap_data, dict):
                        gaps.append(ContentGap(
                            gap_type=gap_data.get("gap_type", "Unknown"),
                            description=gap_data.get("description", ""),
                            opportunity_score=float(gap_data.get("opportunity_score", 0.5)),
                            recommended_action=gap_data.get("recommended_action", ""),
                            related_paa=[q.get("question", "") for q in paa_questions[:3]]
                        ))

            # 按機會分數排序
            gaps.sort(key=lambda x: x.opportunity_score, reverse=True)
            return gaps[:5]  # 最多保留 5 個

        except Exception as e:
            print(f"⚠️ 缺口分析失敗 @ {query}: {e}")
            return []


# ================================================
# 3️⃣ OutlineGenerator - 文章大綱生成
# ================================================

class ArticleBlock(BaseModel):
    """文章區塊結構"""
    block_name: str = Field(description="區塊名稱：quick_summary/definition/uses/faq")
    block_title: str = Field(description="區塊標題（繁體中文）")
    word_count_target: str = Field(description="目標字數範圍，如 '100-150'")
    subsections: List[Dict] = Field(description="子章節列表，每個包含 title 和 key_points")
    paa_coverage: List[str] = Field(description="此區塊涵蓋的 PAA 問題", default_factory=list)


class OutlineGeneratorSignature(dspy.Signature):
    """生成符合 4-block 結構的文章大綱"""

    # 輸入
    query: str = dspy.InputField(desc="搜尋查詢（主題）")
    content_gaps: str = dspy.InputField(desc="內容缺口列表（JSON 格式）")
    paa_questions: str = dspy.InputField(desc="PAA 問題列表")
    aiseo_triggered: bool = dspy.InputField(desc="是否觸發 AI Overview（若為 True，Quick Summary 必須優化為可被引用）")
    block_requirements: str = dspy.InputField(desc="4-block 字數要求（JSON 格式）")

    # 輸出
    outline: Dict = dspy.OutputField(desc="完整文章大綱，包含 4 個 block，每個 block 包含 subsections")


class OutlineGenerator(dspy.Module):
    """文章大綱生成模組"""

    def __init__(self, block_config: Dict):
        super().__init__()
        self.generate = dspy.ChainOfThought(OutlineGeneratorSignature)
        self.block_config = block_config

    def forward(
        self,
        query: str,
        content_gaps: List[ContentGap],
        paa_questions: List[Dict],
        aiseo_triggered: bool
    ) -> Dict:
        """
        生成文章大綱

        Args:
            query: 搜尋查詢
            content_gaps: 內容缺口列表
            paa_questions: PAA 問題列表
            aiseo_triggered: 是否觸發 AI Overview

        Returns:
            Dict: 結構化的文章大綱
        """
        import json

        # 準備輸入
        gaps_json = json.dumps([g.model_dump() for g in content_gaps], ensure_ascii=False, indent=2)
        paa_text = "\n".join([f"- {q.get('question', '')}" for q in paa_questions])
        block_req_json = json.dumps(self.block_config, ensure_ascii=False, indent=2)

        try:
            pred = self.generate(
                query=query,
                content_gaps=gaps_json,
                paa_questions=paa_text,
                aiseo_triggered=aiseo_triggered,
                block_requirements=block_req_json
            )

            # 驗證並返回
            if isinstance(pred.outline, dict):
                return pred.outline
            else:
                print(f"⚠️ 大綱格式錯誤，返回預設結構")
                return self._default_outline(query)

        except Exception as e:
            print(f"⚠️ 大綱生成失敗 @ {query}: {e}")
            return self._default_outline(query)

    def _default_outline(self, query: str) -> Dict:
        """預設大綱結構（當 DSPy 失敗時使用）"""
        return {
            "topic": query,
            "blocks": [
                {
                    "block_name": "quick_summary",
                    "block_title": f"{query}快速總覽",
                    "word_count_target": "100-150",
                    "subsections": []
                },
                {
                    "block_name": "definition",
                    "block_title": f"什麼是{query}？",
                    "word_count_target": "300-400",
                    "subsections": []
                },
                {
                    "block_name": "uses",
                    "block_title": f"{query}的使用方法",
                    "word_count_target": "500-600",
                    "subsections": []
                },
                {
                    "block_name": "faq",
                    "block_title": f"{query}常見問題",
                    "word_count_target": "600-1000",
                    "subsections": []
                }
            ]
        }


# ================================================
# 輔助函數
# ================================================

def init_dspy(model_name: str, api_key: str):
    """初始化 DSPy 語言模型 (DSPy 2.6.5+)"""
    # DSPy 2.6+ 使用 LM 統一接口
    lm = dspy.LM(model=f"openai/{model_name}", api_key=api_key, max_tokens=2000)
    dspy.configure(lm=lm)
    return lm
