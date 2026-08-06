from urllib.parse import urlparse


class CredibilityScorer:
    """来源可信度评分器，按域名权威给来源打分。"""

    TRUSTED_DOMAINS = {
        # 学术机构
        '.edu': 1.0, '.ac.uk': 1.0, '.ac.in': 1.0, '.ac.jp': 1.0,
        # 政府
        '.gov': 1.0, '.gov.uk': 1.0, '.europa.eu': 1.0,
        # 权威媒体
        'bbc.com': 0.95, 'reuters.com': 0.95, 'ap.org': 0.95,
        'nytimes.com': 0.9, 'theguardian.com': 0.9, 'wsj.com': 0.9,
        'economist.com': 0.9, 'bloomberg.com': 0.9, 'cnbc.com': 0.85,
        # 科技媒体
        'techcrunch.com': 0.8, 'theverge.com': 0.8, 'wired.com': 0.8,
        'arstechnica.com': 0.8, 'zdnet.com': 0.75,
        # 中文权威媒体
        'people.com.cn': 0.9, 'xinhuanet.com': 0.9, 'cctv.com': 0.9,
        'caixin.com': 0.8, '36kr.com': 0.75, 'huxiu.com': 0.7,
    }

    def score(self, url: str) -> float:
        """给 URL 打可信度分（0.0-1.0）"""
        domain = urlparse(url).netloc.lower()
        # 精确匹配
        if domain in self.TRUSTED_DOMAINS:
            return self.TRUSTED_DOMAINS[domain]
        # 后缀匹配
        for suffix, s in self.TRUSTED_DOMAINS.items():
            if suffix.startswith('.') and domain.endswith(suffix):
                return s
        return 0.5  # 默认中等可信度

    def filter_results(self, results: list, min_score: float = 0.4) -> list:
        """过滤掉低可信度的结果"""
        return [r for r in results if self.score(r.get('url', '')) >= min_score]
