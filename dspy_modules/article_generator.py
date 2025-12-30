"""
DSPy 模組：Stage ④ 文章生成（6 區塊結構）

此模組定義了產品類別頁的 6 個內容區塊的 DSPy Signature：
1. Quick Summary（快速摘要）
2. Definition（產品定義）
3. Uses（應用場景）
4. Buying Guide（選購指南）
5. Maintenance（保養維護）
6. FAQ（常見問題）

每個 Signature 包含：
- 輸入/輸出結構定義
- 詳細的 Prompt 指令（在 desc 中）
- 防重複策略
- 格式與字數控制
"""

import dspy
from typing import List, Optional


# ================================================
# 1️⃣ Quick Summary Generator
# ================================================
class QuickSummaryGenerator(dspy.Signature):
    """生成產品的快速摘要（40-50字，2-3句話）

    此區塊用於 AI Overview 快速抓取，提供產品核心資訊。
    """

    # 輸入
    product_name: str = dspy.InputField(
        desc="產品名稱（繁體中文）"
    )
    product_category: str = dspy.InputField(
        desc="產品類別（如：實驗室耗材、儀器設備）"
    )
    basic_info: str = dspy.InputField(
        desc="產品基本資訊（材質、規格、用途等）"
    )

    # 輸出
    summary: str = dspy.OutputField(
        desc="""
        生成 40-50 字的快速摘要，必須包含：
        1. 產品定義（是什麼）
        2. 核心優勢（為什麼重要）
        3. 主要應用領域（用在哪裡）

        格式要求：
        - 2-3 句話
        - 純文字段落（不使用標題、粗體、條列）
        - 繁體中文
        - 字數：40-50 字

        範例：
        「圓筒濾紙是一種圓柱形過濾材料，主要由纖維素或玻璃纖維製成，用於過濾液體或氣體中的懸浮顆粒與微生物。具有高過濾效率、標準化尺寸、相容性廣等優點，廣泛應用於微生物檢測、水質分析與食品安全檢驗，是實驗室常用的基礎耗材。」

        注意事項：
        - 避免使用「本文」、「以下」等指涉性詞彙
        - 避免 AI 寫作痕跡（如「深入探索」、「全面性的」）
        - 使用台灣繁體中文用詞
        """
    )


# ================================================
# 2️⃣ Definition Generator
# ================================================
class DefinitionGenerator(dspy.Signature):
    """生成產品的完整定義（100-150字）

    建立專業權威性，提供產品的詳細介紹。
    """

    # 輸入
    product_name: str = dspy.InputField(desc="產品名稱")
    quick_summary: str = dspy.InputField(
        desc="Quick Summary 內容（用於避免重複）"
    )
    detailed_specs: str = dspy.InputField(
        desc="產品詳細規格（材質、尺寸、孔徑、標準等）"
    )

    # 輸出
    definition: str = dspy.OutputField(
        desc="""
        生成 100-150 字的產品定義，必須包含：
        1. 產品介紹（外觀、結構、基本特性）
        2. 材質/規格（詳細規格資訊）
        3. 應用標準（如 ISO、NIEA、CNS 等）

        格式要求：
        - 純文字段落
        - 字數：100-150 字
        - 繁體中文

        範例：
        「圓筒濾紙是一種標準化的過濾材料，外觀為圓柱狀，主要由高純度纖維素或玻璃纖維製成，具有均勻的孔徑分布與高機械強度。常見規格包括直徑 47mm、55mm 與 90mm，孔徑範圍從 0.22μm 至 8μm 不等，依據過濾需求選擇不同孔徑等級。圓筒濾紙廣泛應用於微生物培養計數、水質檢測與食品安全檢驗，符合 ISO 9001 品質管理標準與環保署 NIEA 環境檢驗方法，是實驗室進行液體過濾與微生物分析的重要工具，具備高過濾效率、低背景干擾與可重複性高等特性。」

        防重複策略：
        - 不要重複 Quick Summary 的內容
        - Quick Summary 著重「是什麼」和「為什麼」
        - Definition 著重「詳細規格」和「技術標準」
        - 避免使用 Quick Summary 中已出現的完整句子

        注意事項：
        - 避免過度技術細節（如化學式、複雜原理）
        - 使用台灣繁體中文專業術語
        - 提及具體標準時使用正確名稱（如「環保署 NIEA W303」）
        """
    )


# ================================================
# 3️⃣ Uses Generator
# ================================================
class UsesGenerator(dspy.Signature):
    """生成產品的應用場景（100-150字，3-5個場景）

    描述實際使用情境與具體操作步驟。
    """

    # 輸入
    product_name: str = dspy.InputField(desc="產品名稱")
    product_category: str = dspy.InputField(desc="產品類別")
    previous_content: str = dspy.InputField(
        desc="Quick Summary + Definition 內容（用於避免重複）"
    )

    # 輸出
    uses: str = dspy.OutputField(
        desc="""
        生成 3-5 個具體應用場景，每個場景 50-80 字。

        格式結構：
        場景名稱：產品名稱 + 具體操作步驟 + 檢測目標 + 應用標準/情境

        每個場景必須包含：
        1. 具體操作步驟（如何使用產品）
        2. 檢測目標（測什麼、檢測什麼）
        3. 應用標準/情境（符合什麼標準、用於什麼場合）

        格式要求：
        - 段落式（冒號分隔）
        - 每個場景一個段落
        - 總字數：100-150 字
        - 場景數量：3-5 個
        - 繁體中文

        範例：
        「微生物培養計數：使用圓筒濾紙過濾水樣或食品懸浮液，收集微生物於濾紙表面後轉移至培養基進行菌落計數，此方法廣泛應用於飲用水大腸桿菌群檢測，符合 NIEA E202 環境檢驗方法。

水質環境監測：圓筒濾紙用於測定水中懸浮固體物（SS）含量，過濾一定體積水樣後烘乾稱重，計算懸浮物濃度，此檢測為河川、廢水排放管制的重要指標。

食品安全檢驗：圓筒濾紙可過濾飲料、乳製品或調味液中的微生物，搭配特定培養基檢測生菌數、大腸桿菌群或酵母菌，確保產品符合食品衛生標準。」

        防重複策略：
        - 不要重複 Quick Summary 或 Definition 的內容
        - Quick Summary 和 Definition 只「定義產品」
        - Uses 區塊描述「如何使用產品」
        - 避免籠統描述（❌「食品檢驗實驗室使用」）
        - 使用具體操作（✅「過濾飲料中的微生物進行生菌數檢測」）

        嚴禁內容：
        - ❌ 選購建議（屬於 Buying Guide）
        - ❌ 保養維護（屬於 Maintenance）
        - ❌ 產品定義（屬於 Definition）
        - ❌ 籠統的「XX實驗室」描述

        注意事項：
        - 每個場景必須描述具體的檢測任務或操作流程
        - 提及具體的檢測項目（如「大腸桿菌群」、「懸浮固體物」）
        - 使用台灣繁體中文專業術語
        """
    )


# ================================================
# 4️⃣ Buying Guide Generator
# ================================================
class BuyingGuideGenerator(dspy.Signature):
    """生成選購指南（快速重點 50-80字 + 詳細內容 250字）

    提供選購建議，幫助使用者選擇合適產品。
    """

    # 輸入
    product_name: str = dspy.InputField(desc="產品名稱")
    product_specs: str = dspy.InputField(
        desc="產品規格選項（尺寸、材質、厚度等）"
    )
    previous_content: str = dspy.InputField(
        desc="Quick Summary + Definition + Uses 內容（用於避免重複）"
    )

    # 輸出
    buying_guide: str = dspy.OutputField(
        desc="""
        生成選購指南，包含兩部分（不換行，使用 ｜ 符號分隔）：

        1. 快速重點（50-80字）：濃縮核心選購要點，適合 AI Overview 抓取
        2. 詳細內容（250字）：完整選購建議

        格式要求：
        ▸ 快速重點：[50-80字簡答]｜ [250字詳細內容]

        必須包含：
        1. 選購要素（考量哪些因素）
        2. 規格選擇（如何選擇規格）
        3. 常見錯誤（避免哪些錯誤）
        4. 認證標準（需要哪些認證）

        範例：
        「▸ 快速重點：選購 PVC 手套需注意厚度、尺寸與用途，一般實驗室用 0.12mm 以上較耐用，尺寸應試戴確認手指活動靈活，若接觸有機溶劑應改用丁腈手套。｜ 選購 PVC 手套時，首要考量厚度與耐用性，一般實驗室用 PVC 手套厚度介於 0.08-0.15mm，若需處理粗糙器材或長時間配戴，建議選擇 0.12mm 以上規格。尺寸選擇應注意手掌圍與中指長度，過大會影響精細操作，過小則易破損，建議現場試戴確認手指活動靈活度。表面處理分為光面與麻面，光面適合一般操作，麻面則提供更好的抓握力，適用於潮濕環境或需頻繁持取器皿的場合。需注意 PVC 手套不耐有機溶劑，若實驗涉及丙酮、甲苯等化學品應改用丁腈手套。包裝規格通常為 100 入/盒，建議確認生產日期與保存期限，過期手套易脆化破損。若為食品檢驗或醫療用途，需選擇符合 FDA 或 CNS 15138 認證的產品。」

        防重複策略：
        - 不要重複前面區塊的內容
        - Uses 區塊描述「如何使用」
        - Buying Guide 描述「如何選購」
        - 避免提及使用方法或保養維護

        格式限制：
        - 不能換行（整個內容在同一行）
        - 使用 ｜ 符號分隔快速重點與詳細內容
        - 不使用粗體、斜體、標題

        注意事項：
        - 快速重點要濃縮最核心的選購建議
        - 詳細內容要提供實用的選購指導
        - 使用台灣繁體中文
        """
    )


# ================================================
# 5️⃣ Maintenance Generator
# ================================================
class MaintenanceGenerator(dspy.Signature):
    """生成保養維護指南（快速重點 50-80字 + 詳細內容 250字）

    延長產品壽命並確保操作安全。
    """

    # 輸入
    product_name: str = dspy.InputField(desc="產品名稱")
    product_type: str = dspy.InputField(
        desc="產品類型（拋棄式、可重複使用、儀器設備等）"
    )
    previous_content: str = dspy.InputField(
        desc="前面所有區塊內容（用於避免重複）"
    )

    # 輸出
    maintenance: str = dspy.OutputField(
        desc="""
        生成保養維護指南，包含兩部分（不換行，使用 ｜ 符號分隔）：

        1. 快速重點（50-80字）：濃縮核心保養要點
        2. 詳細內容（250字）：完整保養建議

        格式要求：
        ▸ 快速重點：[50-80字簡答]｜ [250字詳細內容]

        必須包含：
        1. 日常清潔（如何清潔保養）
        2. 儲存條件（溫度、濕度、避光等）
        3. 定期檢查（檢查什麼、多久檢查）
        4. 故障排除（常見問題與處理）

        範例：
        「▸ 快速重點：PVC 手套為拋棄式耗材不建議重複使用，儲存應避免陽光直射與高溫，溫度控制在 15-25°C，開封後建議 6 個月內用完，使用後依廢棄物處理規範分類丟棄。｜ PVC 手套為拋棄式耗材，不建議重複使用，但若短時間內需暫時脫下，應將手套翻轉內面朝外放置於乾淨托盤上，避免外側污染接觸檯面。使用中若手套內部潮濕積汗，可在配戴前先塗抹少許滑石粉或使用棉質內襯手套，減少濕滑感並延長配戴舒適度。儲存時應避免陽光直射與高溫環境，建議放置於陰涼乾燥處，溫度控制在 15-25°C，濕度低於 70%，避免手套老化變硬。未開封的 PVC 手套保存期限約 2-3 年，開封後建議於 6 個月內用完，並隨時檢查是否出現發黃、龜裂或異味。使用後的手套若接觸化學品或生物樣品，應依實驗室廢棄物處理規範分類丟棄，不可與一般垃圾混合。定期盤點庫存，確保各尺寸手套充足，避免實驗中斷。」

        防重複策略：
        - 不要重複前面區塊的內容
        - Uses 區塊描述「如何使用」
        - Buying Guide 描述「如何選購」
        - Maintenance 描述「如何保養維護」
        - 避免提及使用方法或選購建議

        格式限制：
        - 不能換行（整個內容在同一行）
        - 使用 ｜ 符號分隔快速重點與詳細內容
        - 不使用粗體、斜體、標題

        注意事項：
        - 快速重點要濃縮最核心的保養建議
        - 詳細內容要提供實用的保養指導
        - 根據產品類型調整內容（拋棄式 vs 可重複使用）
        - 使用台灣繁體中文
        """
    )


# ================================================
# 6️⃣ FAQ Generator
# ================================================
class FAQGenerator(dspy.Signature):
    """生成常見問題（10個Q&A，總字數1200-3000字）

    回答使用者常見疑問，優化 Featured Snippet 與 PAA。
    """

    # 輸入
    product_name: str = dspy.InputField(desc="產品名稱")
    serp_paa: List[str] = dspy.InputField(
        desc="SERP 分析中的 People Also Ask 問題列表"
    )
    previous_content: str = dspy.InputField(
        desc="前面所有區塊內容（用於補充但不重複）"
    )

    # 輸出
    faq: str = dspy.OutputField(
        desc="""
        生成 10 個常見問題與回答，涵蓋以下類型：
        1. 操作方法（如何使用、如何操作）
        2. 故障排除（常見問題、如何解決）
        3. 規格選擇（哪種規格適合、如何選擇）
        4. 安全注意事項（注意什麼、禁忌事項）

        格式要求：
        Q: [問題]
        A: [回答，最多 300 字]

        （重複 10 次）

        範例：
        「Q: 圓筒濾紙可以重複使用嗎？
        A: 圓筒濾紙為拋棄式耗材，不建議重複使用。每次過濾後，濾紙表面會累積微生物或懸浮顆粒，若重複使用可能導致交叉污染或過濾效率下降。此外，濾紙經過高溫高壓滅菌或化學消毒後，纖維結構可能受損，影響孔徑均勻性與過濾精度。建議每次實驗使用新的濾紙，確保檢測結果準確可靠。

        Q: 如何選擇合適的圓筒濾紙孔徑？
        A: 選擇圓筒濾紙孔徑需根據過濾目標決定。若用於微生物培養計數，建議選擇 0.22μm 或 0.45μm 孔徑，可有效截留細菌與酵母菌。若用於水質懸浮固體物（SS）檢測，建議選擇 0.7μm 至 1.2μm 孔徑，符合環保署 NIEA W210 方法規範。若用於粗過濾或預處理，可選擇 5μm 至 8μm 孔徑。選擇時需確認檢測方法規範，避免孔徑過大導致截留率不足，或孔徑過小導致過濾速度過慢。」

        問題來源：
        - 優先使用 SERP PAA 問題（調整為繁體中文）
        - 補充常見的操作、故障、選購、安全問題
        - 確保問題與產品高度相關

        回答要求：
        - 每個回答最多 300 字
        - 回答要實用、具體、專業
        - 使用台灣繁體中文
        - 提及具體標準或規範（如適用）

        防重複策略：
        - FAQ 可以補充前面區塊的內容，但不能完全重複
        - 前面區塊已詳細說明的內容，FAQ 可以用不同角度回答
        - 例如：Definition 說明「孔徑範圍」，FAQ 回答「如何選擇孔徑」

        注意事項：
        - 問題要具體、實用，避免過於籠統
        - 回答要專業、準確，提供可操作的建議
        - 總字數：1200-3000 字（10 個 Q&A）
        """
    )


# ================================================
# 主要文章生成器（串接所有模組）
# ================================================
class ArticleGenerator:
    """
    主要文章生成器，串接 6 個區塊的 DSPy 模組

    使用方式：
    ```python
    from dspy_modules.article_generator import ArticleGenerator

    generator = ArticleGenerator()
    article = generator.generate(
        product_name="圓筒濾紙",
        product_category="實驗室耗材",
        basic_info="過濾材料，用於微生物檢測",
        detailed_specs="直徑 47mm、55mm、90mm，孔徑 0.22-8μm",
        serp_paa=["圓筒濾紙可以重複使用嗎？", "如何選擇合適孔徑？"]
    )
    ```
    """

    def __init__(self, model: str = "gpt-4o"):
        """初始化文章生成器

        Args:
            model: 使用的 LLM 模型（預設 gpt-4o）
        """
        self.model = model

        # 初始化各個生成器
        self.quick_summary_gen = dspy.ChainOfThought(QuickSummaryGenerator)
        self.definition_gen = dspy.ChainOfThought(DefinitionGenerator)
        self.uses_gen = dspy.ChainOfThought(UsesGenerator)
        self.buying_guide_gen = dspy.ChainOfThought(BuyingGuideGenerator)
        self.maintenance_gen = dspy.ChainOfThought(MaintenanceGenerator)
        self.faq_gen = dspy.ChainOfThought(FAQGenerator)

    def generate(
        self,
        product_name: str,
        product_category: str,
        basic_info: str,
        detailed_specs: str,
        product_type: str = "一般產品",
        product_specs: str = "",
        serp_paa: List[str] = None
    ) -> dict:
        """生成完整文章（6 個區塊）

        Args:
            product_name: 產品名稱
            product_category: 產品類別
            basic_info: 產品基本資訊
            detailed_specs: 產品詳細規格
            product_type: 產品類型（拋棄式、可重複使用等）
            product_specs: 產品規格選項
            serp_paa: SERP PAA 問題列表

        Returns:
            包含 6 個區塊內容的字典
        """
        if serp_paa is None:
            serp_paa = []

        if not product_specs:
            product_specs = detailed_specs

        # 1️⃣ 生成 Quick Summary
        quick_summary_result = self.quick_summary_gen(
            product_name=product_name,
            product_category=product_category,
            basic_info=basic_info
        )
        quick_summary = quick_summary_result.summary

        # 2️⃣ 生成 Definition
        definition_result = self.definition_gen(
            product_name=product_name,
            quick_summary=quick_summary,
            detailed_specs=detailed_specs
        )
        definition = definition_result.definition

        # 3️⃣ 生成 Uses
        previous_content_uses = f"{quick_summary}\n\n{definition}"
        uses_result = self.uses_gen(
            product_name=product_name,
            product_category=product_category,
            previous_content=previous_content_uses
        )
        uses = uses_result.uses

        # 4️⃣ 生成 Buying Guide
        previous_content_buying = f"{quick_summary}\n\n{definition}\n\n{uses}"
        buying_guide_result = self.buying_guide_gen(
            product_name=product_name,
            product_specs=product_specs,
            previous_content=previous_content_buying
        )
        buying_guide = buying_guide_result.buying_guide

        # 5️⃣ 生成 Maintenance
        previous_content_maintenance = f"{previous_content_buying}\n\n{buying_guide}"
        maintenance_result = self.maintenance_gen(
            product_name=product_name,
            product_type=product_type,
            previous_content=previous_content_maintenance
        )
        maintenance = maintenance_result.maintenance

        # 6️⃣ 生成 FAQ
        previous_content_faq = f"{previous_content_maintenance}\n\n{maintenance}"
        faq_result = self.faq_gen(
            product_name=product_name,
            serp_paa=serp_paa,
            previous_content=previous_content_faq
        )
        faq = faq_result.faq

        # 返回完整文章
        return {
            "product_name": product_name,
            "quick_summary": quick_summary,
            "definition": definition,
            "uses": uses,
            "buying_guide": buying_guide,
            "maintenance": maintenance,
            "faq": faq,
            "metadata": {
                "total_chars": len(quick_summary) + len(definition) + len(uses) +
                              len(buying_guide) + len(maintenance) + len(faq),
                "block_count": 6
            }
        }


# ================================================
# 使用範例
# ================================================
if __name__ == "__main__":
    # 初始化 DSPy
    import os
    from dotenv import load_dotenv

    load_dotenv("config/secrets.env")

    lm = dspy.OpenAI(
        model="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    dspy.settings.configure(lm=lm)

    # 創建文章生成器
    generator = ArticleGenerator()

    # 生成文章
    article = generator.generate(
        product_name="圓筒濾紙",
        product_category="實驗室耗材",
        basic_info="圓柱形過濾材料，主要由纖維素或玻璃纖維製成，用於過濾液體或氣體中的懸浮顆粒與微生物",
        detailed_specs="直徑 47mm、55mm、90mm，孔徑範圍 0.22μm 至 8μm，符合 ISO 9001",
        product_type="拋棄式耗材",
        product_specs="直徑、孔徑、材質",
        serp_paa=["圓筒濾紙可以重複使用嗎？", "如何選擇合適的孔徑？"]
    )

    # 輸出結果
    print("=" * 60)
    print("生成的文章內容")
    print("=" * 60)
    print(f"\n【Quick Summary】\n{article['quick_summary']}\n")
    print(f"\n【Definition】\n{article['definition']}\n")
    print(f"\n【Uses】\n{article['uses']}\n")
    print(f"\n【Buying Guide】\n{article['buying_guide']}\n")
    print(f"\n【Maintenance】\n{article['maintenance']}\n")
    print(f"\n【FAQ】\n{article['faq']}\n")
    print(f"\n【Metadata】\n總字數：{article['metadata']['total_chars']} 字")
