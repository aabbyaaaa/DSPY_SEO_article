# -*- coding: utf-8 -*-
"""
頁面品質篩選模組
----------------
用於從 SERP 結果中篩選出高品質、有價值的頁面
排除電商、論壇、社群媒體等低價值內容
"""

import re
from urllib.parse import urlparse

# =======================================================
# 黑名單配置
# =======================================================

EXCLUDED_DOMAINS = {
    # 電商平台（台灣）
    'shopee.tw', 'shopee.com',
    'pchome.com.tw',
    'momoshop.com.tw',
    'ruten.com.tw',
    'books.com.tw',

    # 電商平台（國際）
    'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazon.co.jp',
    'ebay.com', 'ebay.co.uk',
    'walmart.com',
    'target.com',
    'taobao.com', 'tmall.com', 'jd.com', 'alibaba.com', '1688.com',
    'rakuten.co.jp',
    'lazada.com',

    # 論壇/問答
    'ptt.cc',
    'dcard.tw',
    'mobile01.com',
    'quora.com',
    'reddit.com',
    'zhihu.com',
    'baidu.com',
    'douban.com',
    'answers.yahoo.com',

    # 社群媒體
    'facebook.com',
    'instagram.com',
    'twitter.com', 'x.com',
    'linkedin.com',
    'tiktok.com',
    'pinterest.com',
}

EXCLUDED_URL_PATTERNS = [
    # 電商相關
    r'/product[s]?/',
    r'/shop/',
    r'/buy/',
    r'/cart/',
    r'/checkout/',
    r'/order/',
    r'/category/',
    r'/search\?',
    r'/list/',

    # 論壇相關
    r'/forum/',
    r'/thread/',
    r'/post/',
    r'/discussion/',

    # 問答相關
    r'/question/',
    r'/answers?/',
    r'/qa/',
]

EXCLUDED_TITLE_KEYWORDS = [
    # 電商關鍵字（中文）
    '優惠', '折扣', '特價', '限時', '促銷', '下殺', '搶購', '團購',
    '價格', '比價', '購買', '商品',

    # 電商關鍵字（英文）
    'sale', 'discount', 'deal', 'price', 'buy', 'shop', 'store',
    'amazon', 'ebay',
]

# =======================================================
# 白名單配置
# =======================================================

PRIORITY_DOMAINS = {
    # 學術機構（最高優先）
    '.edu': 10,
    '.ac.uk': 10,
    '.ac.jp': 9,
    '.edu.tw': 10,

    # 學術資料庫
    'sciencedirect.com': 10,
    'ncbi.nlm.nih.gov': 10,
    'pubmed.ncbi.nlm.nih.gov': 10,
    'springer.com': 9,
    'nature.com': 10,
    'science.org': 10,
    'wiley.com': 9,
    'plos.org': 9,
    'arxiv.org': 8,
    'biorxiv.org': 8,

    # 政府/標準組織
    '.gov': 10,
    'who.int': 10,
    'iso.org': 9,
    'cdc.gov': 10,
    'fda.gov': 10,
    'nih.gov': 10,
    'nist.gov': 9,

    # 維基百科
    'wikipedia.org': 10,

    # 專業製造商（知識頁面）
    'tuttnauer.com': 7,
    'getinge.com': 7,
    'steris.com': 7,
    'priorclave.co.uk': 7,
    'yiedar.com': 7,
    'te-lab-equipment.com.tw': 7,

    # 專業媒體/教育平台
    'scientificamerican.com': 8,
    'newscientist.com': 8,
    'labmanager.com': 8,
    'biocompare.com': 7,
    'medscape.com': 8,

    # 影片平台（教學內容）
    'youtube.com': 6,

    # Medium（低優先）
    'medium.com': 5,
}

PRIORITY_URL_PATTERNS = {
    r'/blog/': 5,
    r'/resources?/': 5,
    r'/knowledge/': 5,
    r'/tutorial/': 5,
    r'/guide/': 5,
    r'/learning/': 5,
    r'/education/': 5,
    r'/applications?/': 4,
    r'\.pdf$': 3,
}

PRIORITY_KEYWORDS = {
    # 中文
    '原理': 3, '方法': 3, '指南': 3, '教學': 3, '介紹': 3,
    '技術': 2, '研究': 3, '分析': 2, '手冊': 3,

    # 英文
    'principle': 3, 'method': 3, 'guide': 3, 'tutorial': 3,
    'how to': 4, 'introduction': 3, 'overview': 2,
    'handbook': 3, 'manual': 3, 'research': 3, 'study': 3,
    'analysis': 2, 'review': 2,
}

# =======================================================
# 特殊處理規則
# =======================================================

SPECIAL_RULES = {
    'researchgate.net': {
        'include_patterns': [r'/publication/'],
        'exclude_patterns': [r'/post/', r'/question/'],
    },
    'youtube.com': {
        'include_patterns': [r'/watch\?v='],
        'exclude_patterns': [],
    },
    'medium.com': {
        'priority': 5,  # 低優先但不排除
    },
}

# 製造商網站（只保留知識頁面）
MANUFACTURER_DOMAINS = [
    'fishersci.com', 'thermofisher.com',
    'sigmaaldrich.com', 'merck.com',
    'vwr.com', 'coleparmer.com',
]

# =======================================================
# 核心篩選函數
# =======================================================

def extract_domain(url):
    """提取域名"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 移除 www.
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return ''

def is_excluded_domain(domain):
    """檢查是否在黑名單域名中"""
    # 精確匹配
    if domain in EXCLUDED_DOMAINS:
        return True

    # 部分匹配
    for excluded in EXCLUDED_DOMAINS:
        if excluded in domain:
            return True

    return False

def is_excluded_url_pattern(url):
    """檢查 URL 是否匹配排除模式"""
    url_lower = url.lower()
    for pattern in EXCLUDED_URL_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False

def is_excluded_title(title):
    """檢查標題是否包含排除關鍵字"""
    title_lower = title.lower()
    for keyword in EXCLUDED_TITLE_KEYWORDS:
        if keyword in title_lower:
            return True
    return False

def calculate_priority_score(url, title, snippet):
    """計算頁面優先級分數"""
    score = 0
    domain = extract_domain(url)
    url_lower = url.lower()
    text = (title + ' ' + snippet).lower()

    # 1. 域名優先級
    for pattern, points in PRIORITY_DOMAINS.items():
        if pattern.startswith('.'):
            # 頂級域名匹配
            if domain.endswith(pattern):
                score += points
                break
        else:
            # 完整域名匹配
            if pattern in domain:
                score += points
                break

    # 2. URL 模式優先級
    for pattern, points in PRIORITY_URL_PATTERNS.items():
        if re.search(pattern, url_lower):
            score += points

    # 3. 內容關鍵字優先級
    for keyword, points in PRIORITY_KEYWORDS.items():
        if keyword in text:
            score += points

    return score

def apply_special_rules(url, domain):
    """應用特殊規則"""

    # ResearchGate: 只保留論文頁面
    if 'researchgate.net' in domain:
        rules = SPECIAL_RULES['researchgate.net']
        for pattern in rules['include_patterns']:
            if re.search(pattern, url):
                return True
        for pattern in rules['exclude_patterns']:
            if re.search(pattern, url):
                return False
        return False  # 其他頁面都不要

    # YouTube: 只保留影片頁面
    if 'youtube.com' in domain or 'youtu.be' in domain:
        if '/watch?v=' in url or 'youtu.be/' in url:
            return True
        return False

    # 製造商網站: 只保留知識頁面
    if any(mfg in domain for mfg in MANUFACTURER_DOMAINS):
        knowledge_patterns = ['/blog/', '/resources/', '/learning/', '/applications/', '/knowledge/']
        product_patterns = ['/product/', '/shop/', '/buy/', '/cart/']

        # 如果是商品頁面，排除
        if any(pattern in url.lower() for pattern in product_patterns):
            return False

        # 如果是知識頁面，保留
        if any(pattern in url.lower() for pattern in knowledge_patterns):
            return True

        # 其他頁面低優先（讓分數決定）
        return None

    return None  # 沒有特殊規則

def is_valuable_page(url, title, snippet):
    """
    判斷頁面是否有價值

    Returns:
        (bool, int): (是否保留, 優先級分數)
    """

    domain = extract_domain(url)

    # 1. 黑名單檢查
    if is_excluded_domain(domain):
        return False, 0

    if is_excluded_url_pattern(url):
        return False, 0

    if is_excluded_title(title):
        return False, 0

    # 2. 特殊規則檢查
    special_result = apply_special_rules(url, domain)
    if special_result is False:
        return False, 0
    elif special_result is True:
        # 特殊規則通過，計算優先級
        score = calculate_priority_score(url, title, snippet)
        return True, score

    # 3. 計算優先級分數
    score = calculate_priority_score(url, title, snippet)

    # 4. 分數閾值（至少要有一些正向信號）
    if score > 0:
        return True, score

    # 5. 即使沒有正向信號，但也沒有負向信號，給個基礎分
    return True, 1

def filter_organic_results(organic_results, max_results=3):
    """
    從有機搜尋結果中篩選高品質頁面

    Args:
        organic_results: SERP 有機結果列表
        max_results: 最多保留幾個結果

    Returns:
        篩選後的結果列表（依優先級排序）
    """

    scored_results = []

    for result in organic_results:
        url = result.get('link', '')
        title = result.get('title', '')
        snippet = result.get('snippet', '')

        is_valid, score = is_valuable_page(url, title, snippet)

        if is_valid:
            result['quality_score'] = score
            scored_results.append(result)

    # 依優先級排序
    scored_results.sort(key=lambda x: x['quality_score'], reverse=True)

    # 返回前 N 個
    return scored_results[:max_results]

# =======================================================
# 測試函數
# =======================================================

if __name__ == "__main__":
    import sys, io

    # Windows UTF-8 support
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # 測試案例
    test_cases = [
        {
            'url': 'https://shopee.tw/product/123',
            'title': '高壓滅菌鍋優惠特價',
            'snippet': '限時折扣',
            'expected': False,
        },
        {
            'url': 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456/',
            'title': 'Autoclave Sterilization Methods',
            'snippet': 'A comprehensive review of autoclave principles',
            'expected': True,
        },
        {
            'url': 'https://www.yiedar.com/blog_knowledge/autoclave-guide',
            'title': '滅菌鍋使用指南',
            'snippet': '詳細介紹高壓滅菌鍋的使用方法',
            'expected': True,
        },
        {
            'url': 'https://www.fishersci.com/shop/products/autoclave-xyz',
            'title': 'Autoclave Product Page',
            'snippet': 'Buy now with discount',
            'expected': False,
        },
        {
            'url': 'https://www.fishersci.com/blog/autoclave-maintenance-guide',
            'title': 'Autoclave Maintenance Guide',
            'snippet': 'How to maintain your autoclave',
            'expected': True,
        },
    ]

    print("=" * 80)
    print("頁面篩選測試")
    print("=" * 80)

    for i, case in enumerate(test_cases, 1):
        is_valid, score = is_valuable_page(
            case['url'],
            case['title'],
            case['snippet']
        )

        status = "✅" if is_valid == case['expected'] else "❌"
        print(f"\n[{i}] {status}")
        print(f"URL: {case['url']}")
        print(f"結果: {'保留' if is_valid else '排除'} (分數: {score})")
        print(f"預期: {'保留' if case['expected'] else '排除'}")
