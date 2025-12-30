# -*- coding: utf-8 -*-
"""
LLM-SEO Pipeline Stage ④: Article Generation (v3.0 - 6-Block Structure)
------------------------------------------------------------------------
根據 Stage 3 DSPy 分析結果生成符合 6-block 結構的 SEO 文章

輸入：
- data/article_outlines_bilingual.json (文章大綱 + content_gaps)
- data/extracted_content_60_pages.json (參考內容)
- data/serp_analysis_bilingual.json (SERP 分析)

輸出：
- data/final_article.md (最終綜合文章)
- data/final_article_metadata.json (文章元數據)
"""

import os
import sys
import io
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI

# Windows UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from config.config_loader import config, load_config

print("\n" + "=" * 60)
print("📝 6-Block 文章生成模組 - Stage ④ (v3.0)")
print("=" * 60)
print(f"主題：{config.topic} / {config.topic_en}")
print(f"文章結構：{config.article_structure}")

# 載入完整配置
settings = load_config()
block_config = settings["article"]["blocks"]

# 初始化 OpenAI
client = OpenAI(api_key=config.get_openai_key())

# ================================================
# 資料驅動的 FAQ 問題選擇函數
# ================================================

def calculate_paa_frequency(outlines_data: Dict) -> List[Dict]:
    """
    計算 PAA 問題頻率並加權（方案 C+ 動態閾值）

    Returns:
        List[Dict]: [{"question": str, "frequency": int, "base_score": float, "source": "paa"}]
    """
    print("\n📊 計算 PAA 問題頻率...")

    paa_frequency = {}

    for outline_item in outlines_data["outlines"]:
        for paa in outline_item.get("paa_questions", []):
            q_text = paa.get("question", "") if isinstance(paa, dict) else paa

            if q_text:
                if q_text not in paa_frequency:
                    # 自動檢測語言（方案 B）
                    # 檢測是否包含英文字母（排除標點符號）
                    import re
                    is_english = bool(re.search(r'[a-zA-Z]{3,}', q_text))

                    paa_frequency[q_text] = {
                        "question": q_text,
                        "frequency": 0,
                        "source": "paa",
                        "lang": "en" if is_english else "zh-TW"  # 自動檢測語言
                    }
                paa_frequency[q_text]["frequency"] += 1

    paa_candidates = list(paa_frequency.values())

    # 方案 C+: 資料驅動的動態閾值
    if paa_candidates:
        freq_distribution = [p["frequency"] for p in paa_candidates]
        max_freq = max(freq_distribution)
        median_freq = sorted(freq_distribution)[len(freq_distribution) // 2]

        # 動態計算閾值
        high_threshold = max(3, median_freq + 1)  # 至少 3，或中位數 + 1
        medium_threshold = max(2, median_freq)    # 至少 2，或中位數

        high_count = 0
        medium_count = 0
        low_count = 0

        for paa in paa_candidates:
            freq = paa["frequency"]

            # 分層加權（15/12/8）
            if freq >= high_threshold:
                paa["base_score"] = 15.0  # 高頻 PAA
                high_count += 1
            elif freq >= medium_threshold:
                paa["base_score"] = 12.0  # 中頻 PAA
                medium_count += 1
            else:
                paa["base_score"] = 8.0   # 低頻 PAA（仍保留機會）
                low_count += 1

        print(f"   ✅ 收集到 {len(paa_candidates)} 個不重複 PAA 問題")
        print(f"   📈 頻率範圍：{min(freq_distribution)}-{max_freq} 次 (中位數: {median_freq})")
        print(f"   🎯 動態閾值：高頻 ≥{high_threshold}, 中頻 ≥{medium_threshold}")
        print(f"   📊 分層統計：高頻 {high_count} 個 | 中頻 {medium_count} 個 | 低頻 {low_count} 個")
        print(f"   🏆 前 3 高頻：")

        # 按頻率排序顯示
        paa_candidates.sort(key=lambda x: x["frequency"], reverse=True)
        for i, paa in enumerate(paa_candidates[:3], 1):
            print(f"      {i}. (頻率 {paa['frequency']}, base_score {paa['base_score']:.1f}) {paa['question'][:50]}...")

    return paa_candidates


def extract_questions_from_content(pages: List[Dict]) -> List[Dict]:
    """
    使用規則式從 extracted content 提取問題

    Returns:
        List[Dict]: [{"question": str, "type": str, "quality_score": float, "source": "extracted", "lang": str}]
    """
    print("\n🔍 規則式提取問題...")

    # 中文 pattern
    patterns_zh = [
        (r"(為什麼[^？\n]{5,50}？)", "why"),
        (r"(如何[^？\n]{5,50}？)", "how"),
        (r"(什麼是[^？\n]{5,50}？)", "what"),
        (r"([^？\n]{5,50}嗎？)", "yes_no"),
        (r"Q[:：]\s*([^？\n]+？)", "faq"),
        (r"問[:：]\s*([^？\n]+？)", "faq"),
    ]

    # 英文 pattern
    patterns_en = [
        (r"(Why [^?\n]{10,80}\?)", "why"),
        (r"(How [^?\n]{10,80}\?)", "how"),
        (r"(What is [^?\n]{10,80}\?)", "what"),
        (r"(Can [^?\n]{10,80}\?)", "yes_no"),
        (r"Q[:]\s*([^?\n]+\?)", "faq"),
    ]

    extracted_questions = []

    for page in pages:
        lang = page.get('lang', 'unknown')
        content = page.get('content', '')
        quality = page.get('quality_score', 5.0)

        # 選擇對應的 pattern
        patterns = patterns_zh if lang == 'zh-TW' else patterns_en

        for pattern, q_type in patterns:
            flags = re.IGNORECASE if lang == 'en' else 0
            matches = re.findall(pattern, content, flags)

            for match in matches:
                question_text = match.strip()
                if 10 < len(question_text) < 100:
                    extracted_questions.append({
                        "question": question_text,
                        "type": q_type,
                        "quality_score": quality,  # 保留原始 quality_score 作為參考
                        "source": "extracted",
                        "source_url": page['url'][:60] + "...",
                        "lang": lang,
                        "base_score": 8.0  # 方案 C+：統一基礎分數，與低頻 PAA 相同
                    })

    # 按 quality_score 排序（僅用於顯示）
    extracted_questions.sort(key=lambda x: x['quality_score'], reverse=True)

    zh_count = sum(1 for q in extracted_questions if q['lang'] == 'zh-TW')
    en_count = sum(1 for q in extracted_questions if q['lang'] == 'en')
    avg_quality_zh = sum(q['quality_score'] for q in extracted_questions if q['lang'] == 'zh-TW') / zh_count if zh_count > 0 else 0
    avg_quality_en = sum(q['quality_score'] for q in extracted_questions if q['lang'] == 'en') / en_count if en_count > 0 else 0

    print(f"   ✅ 提取到 {len(extracted_questions)} 個問題（統一 base_score=8.0）")
    print(f"   📊 語言分佈：中文 {zh_count} 個 (avg quality: {avg_quality_zh:.2f}), 英文 {en_count} 個 (avg quality: {avg_quality_en:.2f})")
    print(f"   💡 方案 C+：不再使用 quality_score 排序，改用實用性評分")
    print(f"   🏆 前 3 個提取問題（僅供參考）：")
    for i, q in enumerate(extracted_questions[:3], 1):
        print(f"      {i}. ({q['lang']}, source quality {q['quality_score']:.2f}) {q['question'][:50]}...")

    return extracted_questions


def deduplicate_by_embedding(candidates: List[Dict], threshold: float = 0.85) -> List[Dict]:
    """
    使用 OpenAI Embedding 去重（跨語言）

    Args:
        candidates: 候選問題列表
        threshold: 相似度閾值 (>= threshold 視為重複)

    Returns:
        去重後的問題列表
    """
    print(f"\n🔄 Embedding 去重（閾值 {threshold}）...")

    if not candidates:
        return []

    # 取得所有問題的 embeddings
    questions = [c["question"] for c in candidates]

    try:
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=questions
        )
        embeddings = [item.embedding for item in response.data]
    except Exception as e:
        print(f"   ⚠️ Embedding API 失敗：{e}")
        print(f"   ℹ️ 跳過去重步驟")
        return candidates

    # 計算 cosine similarity 並去重
    import numpy as np

    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    unique_candidates = []
    unique_embeddings = []
    duplicates_removed = 0

    for i, candidate in enumerate(candidates):
        is_duplicate = False

        for j, unique_emb in enumerate(unique_embeddings):
            similarity = cosine_similarity(embeddings[i], unique_emb)

            if similarity >= threshold:
                # 發現重複，保留 weighted_score 更高的
                if candidate.get("weighted_score", 0) > unique_candidates[j].get("weighted_score", 0):
                    unique_candidates[j] = candidate
                    unique_embeddings[j] = embeddings[i]

                is_duplicate = True
                duplicates_removed += 1
                break

        if not is_duplicate:
            unique_candidates.append(candidate)
            unique_embeddings.append(embeddings[i])

    print(f"   ✅ 去重前：{len(candidates)} 個")
    print(f"   ✅ 去重後：{len(unique_candidates)} 個")
    print(f"   🗑️ 移除重複：{duplicates_removed} 個")

    return unique_candidates


def filter_covered_topics(candidates: List[Dict], previous_blocks_text: str, threshold: float = 0.7) -> List[Dict]:
    """
    過濾已在前 5 個區塊覆蓋的主題

    Args:
        candidates: 候選問題列表
        previous_blocks_text: 前 5 個區塊的文字內容
        threshold: 相似度閾值 (>= threshold 視為重複主題)

    Returns:
        過濾後的問題列表
    """
    print(f"\n🚫 過濾重複主題（閾值 {threshold}）...")

    if not candidates or not previous_blocks_text:
        return candidates

    # 將前 5 個區塊拆成句子
    sentences = re.split(r'[。！？\n]', previous_blocks_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    # 取得所有問題 + 前面區塊句子的 embeddings
    questions = [c["question"] for c in candidates]
    all_texts = questions + sentences

    try:
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=all_texts
        )
        embeddings = [item.embedding for item in response.data]

        question_embeddings = embeddings[:len(questions)]
        sentence_embeddings = embeddings[len(questions):]
    except Exception as e:
        print(f"   ⚠️ Embedding API 失敗：{e}")
        print(f"   ℹ️ 跳過過濾步驟")
        return candidates

    # 檢查每個問題是否與前面區塊重複
    import numpy as np

    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    filtered_candidates = []
    filtered_out = 0

    for i, candidate in enumerate(candidates):
        max_similarity = 0

        for sent_emb in sentence_embeddings:
            similarity = cosine_similarity(question_embeddings[i], sent_emb)
            max_similarity = max(max_similarity, similarity)

        if max_similarity < threshold:
            filtered_candidates.append(candidate)
        else:
            filtered_out += 1
            print(f"   🗑️ 過濾：{candidate['question'][:50]}... (相似度 {max_similarity:.2f})")

    print(f"   ✅ 過濾前：{len(candidates)} 個")
    print(f"   ✅ 過濾後：{len(filtered_candidates)} 個")
    print(f"   🗑️ 移除重複主題：{filtered_out} 個")

    return filtered_candidates


def translate_question_to_zh_tw(question: str) -> str:
    """
    使用 GPT-4o-mini 翻譯英文問題為繁體中文

    Args:
        question: 英文問題

    Returns:
        繁體中文問題
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "你是專業翻譯，請將英文問題翻譯為繁體中文（台灣用語）。只輸出翻譯結果，不要加任何說明。"
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            temperature=0.3,
            max_tokens=100
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"   ⚠️ 翻譯失敗：{e}")
        return question  # 失敗時返回原文


def score_question_practicality(question: str, topic: str) -> float:
    """
    用 GPT-4o-mini 快速評分問題實用性（方案 A：嚴格評分）

    評分標準：
    - 10分：包含完整產品名稱 + 一般使用者常問 + 問題完整
    - 8分：包含產品相關術語 + 專業但實用 + 問題完整
    - 5分：專業且技術，但問題完整
    - 2分：問題不完整或過於泛化
    - 1分：完全無關

    Args:
        question: 問題文字
        topic: 產品主題（如「高壓滅菌鍋」）

    Returns:
        float: 1-10 的實用性分數
    """
    prompt = f"""請評估以下問題對於「{topic}」產品的實用性（1-10分）。

問題：{question}

評分標準（嚴格版）：
- 10分：包含完整產品名稱（如「高壓滅菌鍋」「autoclave」） + 一般使用者常問的實用問題（如「如何選購」「如何清潔」「如何操作」） + 問題語意完整
- 8分：包含產品相關術語 + 專業但實用的問題（如「如何校正」「故障排除」「定期檢查」） + 問題語意完整
- 5分：專業且技術的問題（如「F0值」「SAL值」「PT100感測器」），但問題語意完整
- 2分：問題不完整（如「高壓滅菌釜 壓力？」缺少動詞）或過於泛化（如「60度能殺菌嗎？」沒提產品名稱）
- 1分：完全無關的問題（如問其他產品）

檢查要點：
1. 問題是否完整？（有主詞、動詞、語意清楚）
2. 是否包含產品名稱或相關術語？
3. 是否為一般使用者關心的問題？
4. 是否與產品直接相關？

只輸出數字（1-10），不要任何說明。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=5
        )

        score_text = response.choices[0].message.content.strip()
        score = float(score_text)
        return max(1.0, min(10.0, score))
    except Exception as e:
        print(f"   ⚠️ 實用性評分失敗（{question[:30]}...）：{e}")
        return 5.0  # 失敗時返回中等分數


def filter_off_topic_questions(candidates: List[Dict], topic: str, synonyms: List[str]) -> List[Dict]:
    """
    過濾不包含產品名稱或同義詞的問題

    Args:
        candidates: 候選問題列表
        topic: 主要產品名稱（如「高壓滅菌鍋」）
        synonyms: 同義詞列表（如 ["高壓滅菌釜", "高壓消毒鍋"]）

    Returns:
        過濾後的問題列表
    """
    print(f"\n🎯 過濾不相關問題（必須包含產品名稱或同義詞）...")

    all_keywords = [topic] + synonyms
    filtered_candidates = []
    filtered_out = 0

    for candidate in candidates:
        question = candidate['question'].lower()

        # 檢查是否包含任何產品關鍵字
        has_keyword = any(kw.lower() in question for kw in all_keywords)

        if has_keyword:
            filtered_candidates.append(candidate)
        else:
            filtered_out += 1
            print(f"   ❌ 過濾：{candidate['question'][:60]}... (不包含產品名稱)")

    print(f"   ✅ 過濾前：{len(candidates)} 個")
    print(f"   ✅ 過濾後：{len(filtered_candidates)} 個")
    print(f"   🗑️ 移除不相關問題：{filtered_out} 個")

    return filtered_candidates


def normalize_product_name(question: str, topic: str, synonyms: List[str]) -> str:
    """
    將問題中的同義詞統一替換為主要產品名稱

    Args:
        question: 問題文字
        topic: 主要產品名稱（如「高壓滅菌鍋」）
        synonyms: 同義詞列表（如 ["高壓滅菌釜", "高壓消毒鍋"]）

    Returns:
        標準化後的問題
    """
    normalized = question
    replaced = False

    for synonym in synonyms:
        if synonym in normalized:
            normalized = normalized.replace(synonym, topic)
            replaced = True
            print(f"   🔄 替換同義詞：{synonym} → {topic}")

    return normalized


def select_top_10_faq_questions(
    paa_candidates: List[Dict],
    extracted_candidates: List[Dict],
    previous_blocks_text: str
) -> List[str]:
    """
    混合策略選擇最終 10 個 FAQ 問題（方案 C+ 增強版 + 主題過濾 + 同義詞統一）

    策略：
    1. 合併所有候選問題
    2. 🆕 過濾不包含產品名稱的問題
    3. LLM 實用性評分（1-10 分）
    4. 計算綜合分數：final_score = base_score + practicality_score * 0.8
    5. Embedding 去重（threshold=0.85）
    6. 過濾與前 5 個區塊重複的主題（threshold=0.7）
    7. 按 final_score 排序
    8. 選擇前 10 個
    9. 如果是英文問題，翻譯為中文
    10. 🆕 統一同義詞為主要產品名稱

    Returns:
        List[str]: 10 個中文問題（已標準化產品名稱）
    """
    print("\n" + "=" * 60)
    print("🎯 開始資料驅動的 FAQ 問題選擇")
    print("=" * 60)

    # 🆕 定義產品名稱與同義詞（從 settings.yaml 的 base_seeds_zh 讀取）
    topic = config.topic  # "高壓滅菌鍋"（主要名稱）
    all_seeds = settings["query_generation"]["base_seeds_zh"]
    synonyms = [s for s in all_seeds if s != topic]  # 同義詞（排除主要名稱）

    print(f"\n🏷️ 產品名稱設定：")
    print(f"   主要名稱：{topic}")
    print(f"   同義詞：{', '.join(synonyms)}")

    # 1. 合併所有候選問題
    all_candidates = paa_candidates + extracted_candidates
    print(f"\n📦 候選問題池：{len(all_candidates)} 個")
    print(f"   - PAA：{len(paa_candidates)} 個")
    print(f"   - Extracted：{len(extracted_candidates)} 個")

    # 🆕 2. 過濾不包含產品名稱的問題
    on_topic_candidates = filter_off_topic_questions(all_candidates, topic, synonyms)

    # 3. LLM 實用性評分（方案 C+ 核心）
    print(f"\n🤖 開始 LLM 實用性評分（使用 gpt-4o-mini）...")
    for i, candidate in enumerate(on_topic_candidates, 1):
        practicality_score = score_question_practicality(candidate['question'], config.topic)
        candidate['practicality_score'] = practicality_score

        # 計算綜合分數：final_score = base_score + practicality_score * 0.8
        base_score = candidate.get('base_score', 0)
        candidate['final_score'] = base_score + practicality_score * 0.8

        if i <= 5 or i % 20 == 0:  # 顯示前 5 個 + 每 20 個顯示進度
            print(f"   [{i}/{len(on_topic_candidates)}] 實用性 {practicality_score:.1f} | 基礎 {base_score:.1f} | 綜合 {candidate['final_score']:.2f} | {candidate['question'][:40]}...")

    print(f"✅ 完成 {len(on_topic_candidates)} 個問題的實用性評分")

    # 4. Embedding 去重
    unique_candidates = deduplicate_by_embedding(on_topic_candidates, threshold=0.85)

    # 5. 過濾重複主題（與前 5 個區塊）
    filtered_candidates = filter_covered_topics(unique_candidates, previous_blocks_text, threshold=0.7)

    # 6. 按 final_score 排序（方案 C+ 綜合評分）
    filtered_candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    # 7. 選擇前 10 個
    top_10_candidates = filtered_candidates[:10]

    print(f"\n🏆 最終選擇前 10 個問題（方案 C+ 綜合評分）：")
    paa_count = sum(1 for c in top_10_candidates if c['source'] == 'paa')
    extracted_count = sum(1 for c in top_10_candidates if c['source'] == 'extracted')
    print(f"   📊 來源分佈：PAA {paa_count} 個 | Extracted {extracted_count} 個")

    for i, candidate in enumerate(top_10_candidates, 1):
        print(f"   {i}. [{candidate['source']}] 綜合分數 {candidate.get('final_score', 0):.2f} (基礎 {candidate.get('base_score', 0):.1f} + 實用性 {candidate.get('practicality_score', 0):.1f}×0.8)")
        print(f"      {candidate['question'][:80]}...")

    # 8. 翻譯英文問題
    final_questions = []
    for candidate in top_10_candidates:
        if candidate['lang'] == 'en':
            print(f"\n🌐 翻譯英文問題：{candidate['question'][:50]}...")
            zh_question = translate_question_to_zh_tw(candidate['question'])
            print(f"   ➡️ {zh_question}")
            final_questions.append(zh_question)
        else:
            final_questions.append(candidate['question'])

    # 🆕 9. 統一同義詞
    print(f"\n🔄 統一產品名稱同義詞...")
    normalized_questions = []
    for question in final_questions:
        normalized = normalize_product_name(question, topic, synonyms)
        normalized_questions.append(normalized)

    print("\n✅ FAQ 問題選擇完成！")
    print("=" * 60)

    return normalized_questions

# ================================================
# 載入所有資料
# ================================================

print("\n📂 載入資料...")

# 1. 文章大綱 (包含 content_gaps)
outlines_path = config.data_dir / "article_outlines_bilingual.json"
with open(outlines_path, "r", encoding="utf-8") as f:
    outlines_data = json.load(f)

# 2. 提取的內容 (cache_extracted_content.json - 114 pages with quality_score)
content_path = config.data_dir / "cache_extracted_content.json"
with open(content_path, "r", encoding="utf-8") as f:
    content_data_raw = json.load(f)

# 將 content_data 轉換為統一格式（中英文合併）
all_pages = []
for lang_key, pages_list in content_data_raw.items():
    if isinstance(pages_list, list):
        all_pages.extend(pages_list)

# 按 quality_score 排序
all_pages.sort(key=lambda x: x.get('quality_score', 0), reverse=True)

# 3. SERP 分析
serp_path = config.data_dir / "serp_analysis_bilingual.json"
with open(serp_path, "r", encoding="utf-8") as f:
    serp_data = json.load(f)

print(f"✅ 載入 {len(outlines_data['outlines'])} 個查詢大綱")
print(f"✅ 載入 {len(all_pages)} 個參考頁面（中文 {sum(1 for p in all_pages if p.get('lang')=='zh-TW')} 個 + 英文 {sum(1 for p in all_pages if p.get('lang')=='en')} 個）")
print(f"✅ 載入 {len(serp_data['serp_results'])} 個 SERP 分析")

# ================================================
# 整合資料
# ================================================

print("\n🔗 整合資料...")

# 準備參考內容摘要（使用品質最高的頁面）
reference_summaries = []
for page in all_pages[:20]:  # 取前 20 個高品質頁面
    content_preview = page.get("content", "")[:1000]
    reference_summaries.append({
        "title": page.get("title", ""),
        "url": page.get("url", ""),
        "preview": content_preview,
        "query": page.get("query", ""),
        "quality_score": page.get("quality_score", 0),
        "lang": page.get("lang", "unknown")
    })

# 收集所有 content_gaps (按 target_block 分組)
gaps_by_block = {
    "quick_summary": [],
    "definition": [],
    "uses": [],
    "buying_guide": [],
    "maintenance": [],
    "faq": []
}

for outline_item in outlines_data["outlines"]:
    for gap in outline_item.get("content_gaps", []):
        target_block = gap.get("target_block", "")
        if target_block in gaps_by_block:
            gaps_by_block[target_block].append({
                "query": outline_item["query"],
                "gap_type": gap["gap_type"],
                "description": gap["description"],
                "opportunity_score": gap["opportunity_score"],
                "recommended_action": gap["recommended_action"]
            })

print(f"✅ 準備 {len(reference_summaries)} 個參考內容（按 quality_score 排序）")
print(f"   品質分佈：{min([r['quality_score'] for r in reference_summaries]):.2f} - {max([r['quality_score'] for r in reference_summaries]):.2f}")
print(f"   語言分佈：中文 {sum(1 for r in reference_summaries if r['lang']=='zh-TW')} 個 + 英文 {sum(1 for r in reference_summaries if r['lang']=='en')} 個")
print(f"✅ Content Gaps 分佈：")
for block, gaps in gaps_by_block.items():
    print(f"   - {block}: {len(gaps)} 個缺口")

# ================================================
# 🎯 資料驅動的 FAQ 問題選擇
# ================================================

print("\n" + "=" * 60)
print("🎯 開始資料驅動的 FAQ 問題選擇")
print("=" * 60)

# 1. 計算 PAA 頻率
paa_candidates = calculate_paa_frequency(outlines_data)

# 2. 規則式提取問題
extracted_candidates = extract_questions_from_content(all_pages)

# ================================================
# 生成函數 - 6 Blocks
# ================================================

def generate_quick_summary(topic: str, topic_en: str, references: List[Dict], gaps: List[Dict]) -> str:
    """生成 Quick Summary (40-50字，2-3句)"""

    cfg = block_config["quick_summary"]
    ref_text = "\n".join([f"- {r['title']}: {r['preview'][:200]}..." for r in references[:3]])
    gaps_text = "\n".join([f"- {g['description']}" for g in gaps[:3]])
    avoid_text = "、".join(cfg["avoid"])

    prompt = f"""請為「{topic}」(英文: {topic_en}) 撰寫 Quick Summary。

**字數要求：{cfg['word_count_min']}-{cfg['word_count_max']} 字**
**句數：{cfg['sentences']} 句話**
**必須包含：{", ".join(cfg['must_include'])}**

**嚴格避免：**
{avoid_text}

**內容缺口機會（請針對這些優化）：**
{gaps_text}

**參考資料：**
{ref_text}

請直接輸出內容，不要加標題或說明。"""

    response = client.chat.completions.create(
        model=config.dspy_model_main,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200
    )

    return response.choices[0].message.content.strip()


def generate_definition(topic: str, topic_en: str, references: List[Dict], gaps: List[Dict], quick_summary: str) -> str:
    """生成 Definition (100-150字)"""

    cfg = block_config["definition"]
    ref_text = "\n\n".join([f"【{r['title']}】\n{r['preview'][:500]}..." for r in references[:8]])
    gaps_text = "\n".join([f"- {g['description']}" for g in gaps[:3]])
    avoid_text = "、".join(cfg["avoid"])

    prompt = f"""請為「{topic}」(英文: {topic_en}) 撰寫 Definition 區塊。

**字數要求：{cfg['word_count_min']}-{cfg['word_count_max']} 字**
**必須包含：{", ".join(cfg['must_include'])}**

**嚴格避免：**
{avoid_text}

**已在 Quick Summary 說過的內容（不要重複）：**
{quick_summary}

**內容缺口機會（請針對這些優化）：**
{gaps_text}

**參考資料：**
{ref_text}

請直接輸出內容，不要加標題或說明。"""

    response = client.chat.completions.create(
        model=config.dspy_model_main,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=400
    )

    return response.choices[0].message.content.strip()


def generate_uses(topic: str, topic_en: str, references: List[Dict], gaps: List[Dict], definition: str) -> str:
    """生成 Uses (100-150字，僅應用場景)"""

    cfg = block_config["uses"]
    ref_text = "\n\n".join([f"【{r['title']}】\n{r['preview'][:800]}..." for r in references[:10]])
    gaps_text = "\n".join([f"- {g['description']}" for g in gaps[:3]])
    avoid_text = "、".join(cfg["avoid"])

    prompt = f"""請為「{topic}」(英文: {topic_en}) 撰寫 Uses（應用場景）區塊。

**字數要求：{cfg['word_count_min']}-{cfg['word_count_max']} 字**
**場景數量：{cfg['scenarios_min']}-{cfg['scenarios_max']} 個**
**格式要求：{cfg['structure']}**
**必須包含：{", ".join(cfg['must_include'])}**

**🚨 嚴格避免（非常重要）：**
{avoid_text}

**特別注意：僅描述「應用場景」，不要包含「操作步驟」、「使用方法」、「注意事項」！**

**已在 Definition 說過的內容（不要重複）：**
{definition[:200]}...

**內容缺口機會（請針對這些優化）：**
{gaps_text}

**參考資料：**
{ref_text}

請直接輸出內容，不要加標題或說明。使用段落式描述，以冒號分隔場景名稱和描述。"""

    response = client.chat.completions.create(
        model=config.dspy_model_main,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=400
    )

    return response.choices[0].message.content.strip()


def generate_buying_guide(topic: str, topic_en: str, references: List[Dict], gaps: List[Dict], previous_content: str) -> str:
    """生成 Buying Guide (50-80字快速重點 + 250字詳細)"""

    cfg = block_config["buying_guide"]
    ref_text = "\n\n".join([f"【{r['title']}】\n{r['preview']}..." for r in references[:12]])
    gaps_text = "\n".join([f"- {g['description']}" for g in gaps[:5]])
    avoid_text = "、".join(cfg["avoid"])

    prompt = f"""請為「{topic}」(英文: {topic_en}) 撰寫 Buying Guide（選購指南）區塊。

**格式要求：{cfg['format']}**
**快速重點字數：{cfg['quick_summary_words']} 字**
**詳細內容字數：{cfg['detailed_words']} 字**
**必須包含：{", ".join(cfg['must_include'])}**

**🚨 嚴格避免：**
{avoid_text}

**重要格式規則：**
1. 必須以「▸ 快速重點：」開頭
2. 使用「｜」分隔快速重點和詳細內容
3. **不能換行** - 整個內容必須在一行內
4. 不要使用條列式（1.2.3.或-）

**前面已說過的內容（不要重複）：**
{previous_content[:300]}...

**內容缺口機會（請針對這些優化）：**
{gaps_text}

**參考資料：**
{ref_text}

請直接輸出一段不換行的文字，格式為：▸ 快速重點：[50-80字簡答]｜ [250字詳細內容]"""

    response = client.chat.completions.create(
        model=config.dspy_model_main,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=600
    )

    content = response.choices[0].message.content.strip()
    # 確保不換行
    content = content.replace('\n', ' ').replace('\r', '')
    return content


def generate_maintenance(topic: str, topic_en: str, references: List[Dict], gaps: List[Dict], previous_content: str) -> str:
    """生成 Maintenance (50-80字快速重點 + 250字詳細)"""

    cfg = block_config["maintenance"]
    ref_text = "\n\n".join([f"【{r['title']}】\n{r['preview']}..." for r in references[:12]])
    gaps_text = "\n".join([f"- {g['description']}" for g in gaps[:5]])
    avoid_text = "、".join(cfg["avoid"])

    prompt = f"""請為「{topic}」(英文: {topic_en}) 撰寫 Maintenance（保養維護）區塊。

**格式要求：{cfg['format']}**
**快速重點字數：{cfg['quick_summary_words']} 字**
**詳細內容字數：{cfg['detailed_words']} 字**
**必須包含：{", ".join(cfg['must_include'])}**

**🚨 嚴格避免：**
{avoid_text}

**重要格式規則：**
1. 必須以「▸ 快速重點：」開頭
2. 使用「｜」分隔快速重點和詳細內容
3. **不能換行** - 整個內容必須在一行內
4. 不要使用條列式（1.2.3.或-）

**前面已說過的內容（不要重複）：**
{previous_content[:300]}...

**內容缺口機會（請針對這些優化）：**
{gaps_text}

**參考資料：**
{ref_text}

請直接輸出一段不換行的文字，格式為：▸ 快速重點：[50-80字簡答]｜ [250字詳細內容]"""

    response = client.chat.completions.create(
        model=config.dspy_model_main,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=600
    )

    content = response.choices[0].message.content.strip()
    # 確保不換行
    content = content.replace('\n', ' ').replace('\r', '')
    return content


def generate_faq(topic: str, topic_en: str, references: List[Dict], selected_questions: List[str], gaps: List[Dict], all_previous_content: str) -> Dict:
    """生成 FAQ (1200-3000字，10個問題)

    Args:
        selected_questions: 已透過資料驅動方式選擇的 10 個問題（中文）
    """

    cfg = block_config["faq"]
    ref_text = "\n\n".join([f"【{r['title']}】\n{r['preview']}" for r in references])
    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(selected_questions)])
    gaps_text = "\n".join([f"- {g['description']}" for g in gaps[:5]])
    avoid_text = "、".join(cfg["avoid"])

    prompt = f"""請為「{topic}」(英文: {topic_en}) 撰寫 FAQ 區塊。

**重要：以下是已透過資料驅動方式選擇的 {len(selected_questions)} 個問題，請直接針對這些問題撰寫回答。**

**必須回答的問題（共 {len(selected_questions)} 個）：**
{questions_text}

**每個回答：不超過 {cfg['answer_max_words']} 字**
**總字數：{cfg['word_count_min']}-{cfg['word_count_max']} 字**
**問題類型參考：{", ".join(cfg['content_types'])}**

**🚨 嚴格避免（非常重要）：**
{avoid_text}

**特別重要：不要重複前面 Quick Summary、Definition、Uses、Buying Guide、Maintenance 區塊已說過的內容！**

**前面所有區塊已說過的內容（絕對不要重複）：**
{all_previous_content[:500]}...

**內容缺口機會（請針對這些優化回答）：**
{gaps_text}

**參考資料：**
{ref_text}

請以 JSON 格式輸出，格式如下：
{{
  "faqs": [
    {{
      "question": "問題1（必須與上面列出的問題完全一致）",
      "answer": "回答1"
    }},
    {{
      "question": "問題2（必須與上面列出的問題完全一致）",
      "answer": "回答2"
    }},
    ...（共 {len(selected_questions)} 個問答）
  ]
}}

確保：
1. 問題文字與上面列出的完全一致
2. 每個回答都是全新的內容，不重複前面任何區塊
3. 回答詳細且實用，不要泛泛而談"""

    response = client.chat.completions.create(
        model=config.dspy_model_main,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=5000
    )

    response_text = response.choices[0].message.content.strip()

    # 提取 JSON
    try:
        faq_data = json.loads(response_text)
    except:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            faq_data = json.loads(json_match.group())
        else:
            faq_data = {"faqs": []}

    return faq_data


# ================================================
# 生成文章
# ================================================

print("\n" + "=" * 60)
print("🚀 開始生成 6-Block 文章")
print("=" * 60)

generated_blocks = {}

# 1️⃣ Quick Summary
print("\n⏳ 生成 Quick Summary...")
generated_blocks["quick_summary"] = generate_quick_summary(
    config.topic,
    config.topic_en,
    reference_summaries,
    gaps_by_block["quick_summary"]
)
print(f"✅ Quick Summary 完成 ({len(generated_blocks['quick_summary'])} 字)")

# 2️⃣ Definition
print("\n⏳ 生成 Definition...")
generated_blocks["definition"] = generate_definition(
    config.topic,
    config.topic_en,
    reference_summaries,
    gaps_by_block["definition"],
    generated_blocks["quick_summary"]
)
print(f"✅ Definition 完成 ({len(generated_blocks['definition'])} 字)")

# 3️⃣ Uses
print("\n⏳ 生成 Uses...")
generated_blocks["uses"] = generate_uses(
    config.topic,
    config.topic_en,
    reference_summaries,
    gaps_by_block["uses"],
    generated_blocks["definition"]
)
print(f"✅ Uses 完成 ({len(generated_blocks['uses'])} 字)")

# 4️⃣ Buying Guide
print("\n⏳ 生成 Buying Guide...")
previous_content = generated_blocks["quick_summary"] + generated_blocks["definition"] + generated_blocks["uses"]
generated_blocks["buying_guide"] = generate_buying_guide(
    config.topic,
    config.topic_en,
    reference_summaries,
    gaps_by_block["buying_guide"],
    previous_content
)
print(f"✅ Buying Guide 完成 ({len(generated_blocks['buying_guide'])} 字)")

# 5️⃣ Maintenance
print("\n⏳ 生成 Maintenance...")
previous_content += generated_blocks["buying_guide"]
generated_blocks["maintenance"] = generate_maintenance(
    config.topic,
    config.topic_en,
    reference_summaries,
    gaps_by_block["maintenance"],
    previous_content
)
print(f"✅ Maintenance 完成 ({len(generated_blocks['maintenance'])} 字)")

# 🎯 選擇 FAQ 問題（資料驅動）
print("\n⏳ 選擇 FAQ 問題（資料驅動）...")
all_previous_content = "\n\n".join([
    f"【Quick Summary】{generated_blocks['quick_summary']}",
    f"【Definition】{generated_blocks['definition']}",
    f"【Uses】{generated_blocks['uses']}",
    f"【Buying Guide】{generated_blocks['buying_guide']}",
    f"【Maintenance】{generated_blocks['maintenance']}"
])

# 呼叫資料驅動的 FAQ 問題選擇函數
selected_faq_questions = select_top_10_faq_questions(
    paa_candidates,
    extracted_candidates,
    all_previous_content
)

# 6️⃣ FAQ
print("\n⏳ 生成 FAQ...")
faq_data = generate_faq(
    config.topic,
    config.topic_en,
    reference_summaries,
    selected_faq_questions,  # 使用資料驅動選擇的 10 個問題
    gaps_by_block["faq"],
    all_previous_content
)
print(f"✅ FAQ 完成 ({len(faq_data.get('faqs', []))} 個問題)")

# ================================================
# 計算字數統計
# ================================================

total_words = sum([
    len(generated_blocks["quick_summary"]),
    len(generated_blocks["definition"]),
    len(generated_blocks["uses"]),
    len(generated_blocks["buying_guide"]),
    len(generated_blocks["maintenance"])
])

faq_words = sum(len(faq.get("answer", "")) for faq in faq_data.get("faqs", []))
total_words += faq_words

print(f"\n📊 字數統計：")
print(f"   Quick Summary: {len(generated_blocks['quick_summary'])} 字")
print(f"   Definition: {len(generated_blocks['definition'])} 字")
print(f"   Uses: {len(generated_blocks['uses'])} 字")
print(f"   Buying Guide: {len(generated_blocks['buying_guide'])} 字")
print(f"   Maintenance: {len(generated_blocks['maintenance'])} 字")
print(f"   FAQ: {faq_words} 字 ({len(faq_data.get('faqs', []))} 個問題)")
print(f"   總計: {total_words} 字")

# ================================================
# 生成 Markdown 文章
# ================================================

print("\n📝 生成 Markdown 文章...")

markdown_content = f"""# {config.topic}

> 本文整合 {len(outlines_data['outlines'])} 個查詢的 DSPy 分析結果，提供完整的 {config.topic} 指南。

---

## Quick Summary

{generated_blocks["quick_summary"]}

---

## Definition

{generated_blocks["definition"]}

---

## Uses

{generated_blocks["uses"]}

---

## Buying Guide

{generated_blocks["buying_guide"]}

---

## Maintenance

{generated_blocks["maintenance"]}

---

## FAQ - 常見問題

"""

# 添加 FAQ
for i, faq in enumerate(faq_data.get("faqs", []), 1):
    markdown_content += f"### {i}. {faq['question']}\n\n"
    markdown_content += f"{faq['answer']}\n\n"

# 添加 SEO 元數據
markdown_content += f"""---

## SEO 元數據

**文章統計：**
- 總字數：{total_words}
- 目標範圍：{config.total_word_count_min}-{config.total_word_count_max}
- H2 標題數：6 個（6-block 結構）
- FAQ 問題數：{len(faq_data.get('faqs', []))}

**關鍵字覆蓋：**
- 主題：{config.topic} / {config.topic_en}
- 分析查詢數：{len(outlines_data['outlines'])}
- FAQ 問題選擇：資料驅動（PAA + 規則式提取）

**參考來源：**
"""

for i, ref in enumerate(reference_summaries[:10], 1):
    markdown_content += f"{i}. [{ref['title']}]({ref['url']}) (quality: {ref['quality_score']:.2f}, {ref['lang']})\n"

markdown_content += f"""

---

*📅 生成時間：自動生成*
*🤖 生成方式：基於 DSPy 分析 + GPT-4o + 資料驅動 FAQ 選擇*
*📊 資料來源：{len(all_pages)} 個頁面（{sum(1 for p in all_pages if p.get('lang')=='zh-TW')} 中文 + {sum(1 for p in all_pages if p.get('lang')=='en')} 英文） + {len(serp_data['serp_results'])} 個 SERP 分析*
"""

# ================================================
# 儲存結果
# ================================================

print("\n💾 儲存文章...")

# 儲存 Markdown
md_path = config.data_dir / "final_article.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write(markdown_content)

print(f"✅ Markdown 已儲存：{md_path}")

# 儲存元數據
metadata = {
    "topic_zh": config.topic,
    "topic_en": config.topic_en,
    "structure": "6-block",
    "word_count": {
        "quick_summary": len(generated_blocks["quick_summary"]),
        "definition": len(generated_blocks["definition"]),
        "uses": len(generated_blocks["uses"]),
        "buying_guide": len(generated_blocks["buying_guide"]),
        "maintenance": len(generated_blocks["maintenance"]),
        "faq": faq_words,
        "total": total_words
    },
    "blocks": {
        "h2_count": 6,
        "faq_questions": len(faq_data.get("faqs", []))
    },
    "sources": {
        "queries_analyzed": len(outlines_data['outlines']),
        "pages_extracted": len(all_pages),
        "pages_zh": sum(1 for p in all_pages if p.get('lang') == 'zh-TW'),
        "pages_en": sum(1 for p in all_pages if p.get('lang') == 'en'),
        "serp_results": len(serp_data["serp_results"]),
        "faq_selection": {
            "paa_candidates": len(paa_candidates),
            "extracted_candidates": len(extracted_candidates),
            "total_candidates": len(paa_candidates) + len(extracted_candidates),
            "selected_questions": len(selected_faq_questions)
        },
        "content_gaps": sum(len(gaps) for gaps in gaps_by_block.values())
    },
    "references": [
        {
            "title": ref["title"],
            "url": ref["url"],
            "query": ref["query"]
        }
        for ref in reference_summaries[:10]
    ],
    "seo_requirements": {
        "word_count_range": f"{config.total_word_count_min}-{config.total_word_count_max}",
        "word_count_achieved": total_words,
        "within_range": config.total_word_count_min <= total_words <= config.total_word_count_max
    }
}

metadata_path = config.data_dir / "final_article_metadata.json"
with open(metadata_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f"✅ 元數據已儲存：{metadata_path}")

# ================================================
# 最終報告
# ================================================

print("\n" + "=" * 60)
print("✅ 6-Block 文章生成完成！")
print("=" * 60)
print(f"📁 文章檔案：{md_path}")
print(f"📁 元數據檔案：{metadata_path}")
print(f"\n📊 文章統計：")
print(f"   總字數：{total_words} 字")
print(f"   目標範圍：{config.total_word_count_min}-{config.total_word_count_max} 字")
print(f"   達成率：{'✅ 符合' if config.total_word_count_min <= total_words <= config.total_word_count_max else '⚠️ 超出範圍'}")
print(f"\n📈 6-Block 結構：")
print(f"   1. Quick Summary：{len(generated_blocks['quick_summary'])} 字")
print(f"   2. Definition：{len(generated_blocks['definition'])} 字")
print(f"   3. Uses：{len(generated_blocks['uses'])} 字")
print(f"   4. Buying Guide：{len(generated_blocks['buying_guide'])} 字")
print(f"   5. Maintenance：{len(generated_blocks['maintenance'])} 字")
print(f"   6. FAQ：{faq_words} 字（{len(faq_data.get('faqs', []))} 個問題）")
print(f"\n🎯 資料來源：")
print(f"   分析查詢：{len(outlines_data['outlines'])} 個")
print(f"   參考頁面：{len(all_pages)} 個（中文 {sum(1 for p in all_pages if p.get('lang')=='zh-TW')} + 英文 {sum(1 for p in all_pages if p.get('lang')=='en')}）")
print(f"   Content Gaps：{sum(len(gaps) for gaps in gaps_by_block.values())} 個")
print(f"\n📊 資料驅動的 FAQ 選擇：")
print(f"   PAA 候選問題：{len(paa_candidates)} 個")
print(f"   規則式提取問題：{len(extracted_candidates)} 個")
print(f"   總候選池：{len(paa_candidates) + len(extracted_candidates)} 個")
print(f"   最終選擇：{len(selected_faq_questions)} 個（經 Embedding 去重 + 主題過濾）")
print("\n" + "=" * 60)
