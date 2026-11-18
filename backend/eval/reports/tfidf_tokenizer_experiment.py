# -*- coding: utf-8 -*-
"""早停相似度分词对照实验（可复现归档）

背景：reviewer 的 cosine 早停（app/graph/nodes/reviewer.py:58-63）用裸 TfidfVectorizer()，
默认 token_pattern (?u)\\b\\w\\w+\\b 按空白/标点切块，中文长句整段成 token。
本实验用同一段研报文本在 4 个修订场景 × 3 种分词方案下实测 cosine，
量化「默认实现全盲于小数位修订」并对照 char_wb / jieba 的阈值重标压力。

复现：
    cd backend && .venv/bin/python eval/reports/tfidf_tokenizer_experiment.py
依赖：scikit==1.7.2、jieba==0.42.1（2026-11-19 实测通过）
注意：jieba 必须以 TfidfVectorizer(tokenizer=jieba.lcut, token_pattern=None) 直传——
把 jieba 切词结果拼回空格分隔字符串再过默认向量化器是无效接法，小数位盲区依旧存在
（"15.2%" 会被二次切分，"2%" 只含一个词字符被丢弃）。详见同名 .md 报告 §4。
"""
import warnings

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore")  # tokenizer= 会触发 ConvergenceWarning/BuildWarning，与结论无关

try:
    import jieba
except ImportError:
    jieba = None

BASE = ("本报告分析贵州茅台2024年三季报营收1207.76亿元，同比增长15.2%，"
        "合同负债维持高位，渠道打款意愿积极。投资建议：维持买入评级，目标价1850元，"
        "建议关注高端白酒龙头。风险提示：宏观消费复苏斜率不及预期，批价波动加大。")

# 四个修订场景：BASE → 修订版（S4 换行业换业务事实，保留样板结构）
SCENARIOS = [
    ("S1 只改小数位 15.2%→15.3%",
     BASE.replace("同比增长15.2%", "同比增长15.3%")),
    ("S2 改整数 1207.76→1215.42亿",
     BASE.replace("1207.76亿元", "1215.42亿元")),
    ("S3 同义改写两句（典型修订编辑）",
     BASE.replace("合同负债维持高位，渠道打款意愿积极", "合同负债处于高位，渠道回款意愿良好")
         .replace("维持买入评级，目标价1850元", "保持买入评级，目标价1850元")),
    ("S4 换一家公司（平安银行，应判低相似）",
     ("本报告分析平安银行2024年三季报营收1207.76亿元，同比增长15.2%，"
      "净息差企稳回升，零售贷款投放放量。投资建议：维持买入评级，目标价1850元，"
      "建议关注高股息银行。风险提示：宏观消费复苏斜率不及预期，资产质量波动加大。")),
]


def _cosine(vectorizer, text_a, text_b):
    """镜像 reviewer.py:58-63 的算法：两文本联合 fit_transform 后取行间 cosine。"""
    matrix = vectorizer.fit_transform([text_a, text_b])
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])


def main():
    variants = [
        ("默认(现状)", TfidfVectorizer()),
        ("char_wb(2,4)", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))),
    ]
    if jieba is not None:
        variants.append(("jieba", TfidfVectorizer(tokenizer=jieba.lcut, token_pattern=None)))

    header = " ".join(f"{name:>10}" for name, _ in variants)
    print(f"{'场景':<24} {header}")
    for name, revised in SCENARIOS:
        row = " ".join(f"{_cosine(vec, BASE, revised):>10.4f}" for _, vec in variants)
        print(f"{name:<24} {row}")

    # 默认实现的词表样例（HTML M1.4 引用的「词表长这样」出处）
    vec = TfidfVectorizer()
    vec.fit([BASE])
    print("\n默认词表(排序后前 10):", vec.get_feature_names_out()[:10].tolist())


if __name__ == "__main__":
    main()
