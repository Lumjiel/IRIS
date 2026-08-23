"""内置模拟快照数据 —— 网络彻底不可用时的最终兜底。

设计目标：
- 离线演示场景下报告依然"像样"：数值内部一致、字段齐全，而非占位符
- 数据为静态快照，仅供离线演示，不构成任何投资参考
- 所有 data_source 标签包含「模拟」二字，保证下游 degraded 标记检测不被绕过
"""

from typing import Any, Dict, List

_SNAPSHOT_SOURCE = "内置模拟数据（离线快照兜底）"

# 按股票代码索引的快照数据（数值为编写时的量级近似，仅供演示）
_SNAPSHOTS: Dict[str, Dict[str, Any]] = {
    "600196": {  # 复星医药
        "info": {
            "公司名称": "复星医药",
            "公司全称": "上海复星医药（集团）股份有限公司",
            "所属行业": "医药制造",
            "上市日期": "1998-08-07",
            "上市板块": "上海证券交易所主板",
            "总股本": "26.7亿股",
            "流通股本": "26.5亿股",
            "注册地址": "上海市浦东新区",
            "主营业务": "药品制造与研发、医疗器械与医学诊断、医疗健康服务",
            "董事长": "陈玉卿",
            "员工人数": "约38000人",
        },
        "financial": {
            "report_period": "2025中报",
            "total_revenue": "204.5亿元",
            "revenue_yoy_growth": "-3.2%",
            "net_profit": "15.1亿元",
            "net_profit_yoy_growth": "+12.6%",
            "gross_margin": "48.9%",
            "net_margin": "7.4%",
            "roe": "3.1%",
            "eps": "0.57元",
        },
        "quote": {
            "最新价": "26.85", "涨跌幅": "+1.32%", "涨跌额": "0.35",
            "成交量": "184200手", "成交额": "4.92亿", "振幅": "2.15%",
            "最高": "27.10", "最低": "26.52", "今开": "26.60", "昨收": "26.50",
            "换手率": "0.69%", "市盈率-动态": "18.4", "市净率": "1.52",
            "总市值": "717亿", "流通市值": "712亿", "延时": "15分钟",
        },
        "news": [
            {"title": "复星医药发布2025年半年度业绩预告", "content": "公司预计上半年归母净利润同比增长10%-15%，创新药收入占比持续提升...", "publish_time": "2025-07-15", "source": "模拟数据"},
            {"title": "复星医药：汉斯状（斯鲁利单抗）新增适应症获批", "content": "国家药监局批准汉斯状用于小细胞肺癌一线治疗，进一步拓宽产品管线...", "publish_time": "2025-06-28", "source": "模拟数据"},
            {"title": "机构调研纪要：创新药出海进展受关注", "content": "多家券商调研公司海外授权合作进展，市场关注CAR-T产品商业化节奏...", "publish_time": "2025-06-12", "source": "模拟数据"},
        ],
    },
    "600519": {  # 贵州茅台
        "info": {
            "公司名称": "贵州茅台", "公司全称": "贵州茅台酒股份有限公司",
            "所属行业": "白酒", "上市日期": "2001-08-27", "上市板块": "上海证券交易所主板",
            "总股本": "12.56亿股", "流通股本": "12.56亿股", "注册地址": "贵州省仁怀市茅台镇",
            "主营业务": "茅台酒及系列酒的生产与销售", "董事长": "张德芹", "员工人数": "约34000人",
        },
        "financial": {
            "report_period": "2025一季报", "total_revenue": "514.4亿元", "revenue_yoy_growth": "+10.7%",
            "net_profit": "268.5亿元", "net_profit_yoy_growth": "+11.6%", "gross_margin": "91.8%",
            "net_margin": "52.2%", "roe": "8.9%", "eps": "21.38元",
        },
        "quote": {
            "最新价": "1520.00", "涨跌幅": "-0.46%", "涨跌额": "-7.00",
            "成交量": "23600手", "成交额": "35.8亿", "振幅": "1.02%",
            "最高": "1535.98", "最低": "1518.11", "今开": "1530.00", "昨收": "1527.00",
            "换手率": "0.19%", "市盈率-动态": "21.6", "市净率": "8.20",
            "总市值": "1.91万亿", "流通市值": "1.91万亿", "延时": "15分钟",
        },
        "news": [
            {"title": "贵州茅台发布2024年度利润分配方案", "content": "拟每股派发现金红利若干元，分红率保持高位...", "publish_time": "2025-06-20", "source": "模拟数据"},
            {"title": "茅台批价企稳回升 渠道库存健康", "content": "飞天茅台原箱批价近期企稳，渠道反馈动销平稳...", "publish_time": "2025-06-05", "source": "模拟数据"},
            {"title": "公司召开股东大会 审议年度报告", "content": "管理层回应市场关切，强调长期主义与价值回报...", "publish_time": "2025-05-16", "source": "模拟数据"},
        ],
    },
}

# 未知代码的通用模板（数值为合理量级，非真实数据）
_GENERIC = {
    "info": {
        "公司名称": "样本公司", "公司全称": "样本股份有限公司",
        "所属行业": "制造业", "上市日期": "2010-01-01", "上市板块": "深圳证券交易所主板",
        "总股本": "10亿股", "流通股本": "8亿股", "注册地址": "-",
        "主营业务": "-", "董事长": "-", "员工人数": "-",
    },
    "financial": {
        "report_period": "最近报告期", "total_revenue": "50亿元", "revenue_yoy_growth": "+5%",
        "net_profit": "5亿元", "net_profit_yoy_growth": "+8%", "gross_margin": "30%",
        "net_margin": "10%", "roe": "6%", "eps": "0.50元",
    },
    "quote": {
        "最新价": "15.00", "涨跌幅": "+0.67%", "涨跌额": "0.10",
        "成交量": "120000手", "成交额": "1.80亿", "振幅": "1.50%",
        "最高": "15.25", "最低": "14.88", "今开": "14.95", "昨收": "14.90",
        "换手率": "1.50%", "市盈率-动态": "20.0", "市净率": "2.00",
        "总市值": "150亿", "流通市值": "120亿", "延时": "15分钟",
    },
    "news": [
        {"title": "样本公司发布定期业绩公告", "content": "公司经营稳健，主要财务指标保持增长...", "publish_time": "2025-07-01", "source": "模拟数据"},
        {"title": "行业政策动态跟踪", "content": "所在行业近期政策环境稳定，景气度延续...", "publish_time": "2025-06-15", "source": "模拟数据"},
        {"title": "机构投资者调研摘要", "content": "公司就经营情况与发展战略与投资者交流...", "publish_time": "2025-05-30", "source": "模拟数据"},
    ],
}


def get_snapshot(stock_code: str) -> Dict[str, Any]:
    """返回指定代码的完整快照（info/financial/quote/news），无匹配时用通用模板。"""
    return _SNAPSHOTS.get(str(stock_code), _GENERIC)


def get_mock_info(stock_code: str) -> Dict[str, str]:
    snap = get_snapshot(stock_code)
    data = dict(snap["info"])
    # 与旧版 mock 行为兼容：保留股票代码字段，下游提示词可能引用
    data["股票代码"] = str(stock_code)
    data["data_source"] = _SNAPSHOT_SOURCE
    return data

def get_mock_financial(stock_code: str) -> Dict[str, Any]:
    snap = get_snapshot(stock_code)
    data = {"stock_code": str(stock_code)}
    data.update(snap["financial"])
    data["data_source"] = _SNAPSHOT_SOURCE
    return data


def get_mock_quote(stock_code: str) -> Dict[str, Any]:
    snap = get_snapshot(stock_code)
    data = {"stock_code": str(stock_code)}
    data.update(snap["quote"])
    data["data_source"] = _SNAPSHOT_SOURCE
    return data


def get_mock_news(stock_code: str) -> List[Dict[str, str]]:
    return [dict(n) for n in get_snapshot(stock_code)["news"]]
