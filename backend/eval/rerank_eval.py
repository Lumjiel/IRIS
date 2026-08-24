"""
Rerank 效果评测（docs/DESIGN_rerank_and_memory.md 风险项："怎么证明 rerank 有效"）

方法（诚实边界）：
- 相关性判定用 metadata.stock_code 匹配（二值相关），非人工全文标注——
  优点是可复现零标注成本，缺点是同公司无关段落也会算相关，指标偏保守上限
- 从 chroma_db 现有研报中取 chunk 数最多的前 N 只股票，每只生成 4 个查询模板 → 20 queries
- 对比 纯向量序 vs gte-rerank 序 的 P@3 / MRR@10

用法：
    cd backend
    python -m eval.rerank_eval                 # 完整评测（需要 DASHSCOPE_API_KEY）
    python -m eval.rerank_eval --baseline-only # 只跑向量基线（无 Key 也能跑）
"""
import argparse
import asyncio
import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.logger import get_logger  # noqa: E402

log = get_logger("eval.rerank")

QUERY_TEMPLATES = [
    "{name}({code})的最新评级和目标价是多少",
    "{code} 财务表现和盈利能力分析",
    "机构对 {name} 的投资建议",
    "{name} 所处行业的前景和竞争格局",
]

# --db 覆盖（评测临时语料库用）；None = 用应用知识库
DB_OVERRIDE = None


def _get_db() -> str:
    if DB_OVERRIDE:
        return DB_OVERRIDE
    from app.rag.report_ingest import DB_PATH

    return DB_PATH


TOP_K = 5
FETCH_K = 20
MRR_DEPTH = 10


def _guess_name(text: str) -> str:
    """从文档文本启发式猜公司名（复用 report_ingest 的正则思路）。"""
    import re

    m = re.search(r'([\u4e00-\u9fa5]{2,8}(?:股份|集团|科技|药业|银行|保险|证券))', text)
    return m.group(1) if m else ""


def load_corpus() -> Tuple[List[Dict], List[Dict]]:
    """读取 Chroma 全部文档，返回 (docs, targets)。

    targets 标注策略两级回退：
      1. 研报入库链路（有 stock_code 元数据）→ 按股票代码分组
      2. 普通上传链路（只有 source/page）→ 按来源文件分组，同源=相关
    """
    from app.rag.engine import embeddings
    from langchain_community.vectorstores import Chroma

    db = _get_db()
    try:
        empty = not os.path.exists(db) or not os.listdir(db)
    except OSError as e:
        raise SystemExit(f"[Eval] 知识库目录不可访问（{db}）: {e}")
    if empty:
        raise SystemExit(f"[Eval] 知识库为空（{db}），请先上传研报或使用 --seed-demo")

    try:
        vectorstore = Chroma(persist_directory=db, embedding_function=embeddings)
    except Exception as e:
        raise SystemExit(f"[Eval] Chroma 打开失败（{db}）: {e}")
    raw = vectorstore.get(include=["metadatas", "documents"])
    docs = [
        {"text": text, "meta": meta or {}}
        for text, meta in zip(raw["documents"], raw["metadatas"])
    ]

    def _targets_by(key: str, min_chunks: int = 3) -> List[Dict]:
        volume: Dict[str, Dict] = {}
        for d in docs:
            v = d["meta"].get(key)
            if v:
                volume.setdefault(v, {"field": key, "value": v, "chunks": 0})
                volume[v]["chunks"] += 1
                if volume[v].get("name") in (None, "") and d["text"]:
                    volume[v]["name"] = _guess_name(d["text"][:2000])
        ranked = sorted(volume.values(), key=lambda t: -t["chunks"])
        return [t for t in ranked if t["chunks"] >= min_chunks][:5]

    targets = _targets_by("stock_code") or _targets_by("source")
    if not targets:
        raise SystemExit("[Eval] 语料过少或无可用分组字段（stock_code/source），无法评测")
    return docs, targets


def build_queries(targets: List[Dict]) -> List[Dict]:
    """每个 target × 4 查询模板 ≈ 20 queries；target 即相关性标签。"""
    queries = []
    for t in targets:
        code = t["value"] if t["field"] == "stock_code" else ""
        name = t.get("name") or t["value"]
        for tpl in QUERY_TEMPLATES:
            q = tpl.format(name=name, code=code)
            if not code:
                # 无代码时去掉空括号占位，避免裸 "None"
                q = q.replace("()", "").replace("  ", " ").strip()
            queries.append({"query": q, "target": t})
    return queries


def vector_search(query: str) -> List[Dict]:
    """向量召回 FETCH_K 候选，保持距离升序（Chroma 原生序）。"""
    from app.rag.engine import embeddings
    from langchain_community.vectorstores import Chroma

    try:
        vectorstore = Chroma(persist_directory=_get_db(), embedding_function=embeddings)
        pairs = vectorstore.similarity_search_with_score(query, k=FETCH_K)
        return [{"doc": doc, "dist": float(dist)} for doc, dist in pairs]
    except Exception as e:
        raise SystemExit(f"[Eval] 向量检索失败（query={query!r}）: {e}")


def is_relevant(doc_meta: Dict, target: Dict) -> bool:
    return doc_meta.get(target["field"]) == target["value"]


def p_at_k(ranked: List[Dict], target: Dict, k: int = TOP_K) -> float:
    hits = sum(1 for r in ranked[:k] if is_relevant(r["doc"].metadata, target))
    return hits / k


def mrr(ranked: List[Dict], target: Dict, depth: int = MRR_DEPTH) -> float:
    for i, r in enumerate(ranked[:depth], start=1):
        if is_relevant(r["doc"].metadata, target):
            return 1.0 / i
    return 0.0


# 合成语料：3 家公司 × 各维度段落。仅用于验证评测链路，非真实研报
DEMO_COMPANIES = [
    {"code": "600519", "name": "贵州茅台",
     "facets": ["高端白酒龙头，品牌护城河深厚", "批价坚挺，渠道库存健康", "分红率提升，现金流充沛"]},
    {"code": "600196", "name": "复星医药",
     "facets": ["创新药管线进入收获期", "海外商业化能力突出", "研发投入占比持续提升"]},
    {"code": "300750", "name": "宁德时代",
     "facets": ["动力电池全球市占率第一", "麒麟电池量产领先同行", "储能业务高速增长"]},
]


def _seed_demo_corpus(db_path):
    """写入合成语料到目标库（幂等：先删后建）。"""
    import shutil

    from langchain_community.vectorstores import Chroma
    from langchain_core.documents import Document

    from app.rag.engine import embeddings

    target = db_path or _get_db()
    try:
        if os.path.exists(target):
            shutil.rmtree(target)
        os.makedirs(target, exist_ok=True)
    except OSError as e:
        raise SystemExit(f"[Eval] 语料目录重置失败（{target}）: {e}")

    docs = []
    for comp in DEMO_COMPANIES:
        for j, facet in enumerate(comp["facets"]):
            for k in range(2):
                text = (f"{comp['name']}({comp['code']})研报观点：{facet}。"
                        f"分析师认为该因素对长期投资价值构成{'核心' if k == 0 else '重要'}支撑。"
                        f"风险提示：行业竞争加剧、政策变化及宏观经济波动可能影响上述判断。" * 2)
                docs.append(Document(page_content=text, metadata={
                    "stock_code": comp["code"], "stock_name": comp["name"],
                    "chunk_index": j * 2 + k, "source": f"demo_{comp['code']}"
                }))

    Chroma.from_documents(documents=docs, embedding=embeddings, persist_directory=target)
    print(f"[Seed] 已写入 {len(docs)} 条合成语料 -> {target}")


def main():
    parser = argparse.ArgumentParser(description="Rerank 效果评测")
    parser.add_argument("--baseline-only", action="store_true",
                        help="只跑向量基线（不调 rerank API）")
    parser.add_argument("--output", default="eval/reports/rerank_eval.md",
                        help="结果 markdown 输出路径")
    parser.add_argument("--db", default=None,
                        help="覆盖知识库路径（默认用应用 chroma_db）")
    parser.add_argument("--seed-demo", action="store_true",
                        help="先向目标库写入 3 公司合成语料（验证评测链路，非真实研报）")
    args = parser.parse_args()

    global DB_OVERRIDE
    if args.db:
        DB_OVERRIDE = args.db

    if args.seed_demo:
        _seed_demo_corpus(args.db)

    print("[1/4] 加载知识库...")
    _docs, targets = load_corpus()

    queries = build_queries(targets)
    labels = ", ".join(t.get("name") or t["value"] for t in targets)
    print(f"[2/4] {len(queries)} 条查询（标注分组: {labels}）")

    rows = []
    for i, q in enumerate(queries, 1):
        candidates = vector_search(q["query"])
        baseline = candidates[:TOP_K]
        row = {
            "query": q["query"],
            "target": q["target"].get("name") or q["target"]["value"],
            "base_p3": p_at_k(baseline, q["target"]),
            "base_mrr": mrr(baseline, q["target"]),
            "rr_p3": None,
            "rr_mrr": None,
        }

        if not args.baseline_only:
            try:
                from app.rag.reranker import get_reranker

                reranked = asyncio.to_thread(
                    get_reranker().rerank,
                    q["query"],
                    [c["doc"] for c in candidates],
                    TOP_K,
                )
                ranked_docs = asyncio.run(reranked)
                rerank_order = [{"doc": d} for d in ranked_docs]
                row["rr_p3"] = p_at_k(rerank_order, q["target"])
                row["rr_mrr"] = mrr(rerank_order, q["target"])
            except Exception as e:
                log.warning(f"rerank 失败（该条按基线计）: {e}")

        rows.append(row)
        print(f"  [{i:>2}/{len(queries)}] P@3 base={row['base_p3']:.2f}"
              + (f" rr={row['rr_p3']:.2f}" if row["rr_p3"] is not None else ""))

    print("[3/4] 汇总...")
    summary = {
        "queries": len(rows),
        "top_k": TOP_K,
        "base_p3": statistics.mean(r["base_p3"] for r in rows),
        "base_mrr": statistics.mean(r["base_mrr"] for r in rows),
    }
    reranked_rows = [r for r in rows if r["rr_p3"] is not None]
    if reranked_rows:
        summary["rr_p3"] = statistics.mean(r["rr_p3"] for r in reranked_rows)
        summary["rr_mrr"] = statistics.mean(r["rr_mrr"] for r in reranked_rows)
        summary["reranked_queries"] = len(reranked_rows)

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # 写报告
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Rerank 效果评测",
        "",
        f"- 时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 方法：分组字段二值相关判定（优先 stock_code，回退 source 文件；非人工全文标注）；"
        f"候选 {FETCH_K}，P@{TOP_K} / MRR@{MRR_DEPTH}",
        f"- 指标：**P@3** 向量基线 {summary['base_p3']:.3f}"
        + (f" vs rerank **{summary['rr_p3']:.3f}**" if "rr_p3" in summary else ""),
        f"- 指标：**MRR@10** 向量基线 {summary['base_mrr']:.3f}"
        + (f" vs rerank **{summary['rr_mrr']:.3f}**" if "rr_mrr" in summary else ""),
        "",
        "| 查询 | 目标 | P@3 基线 | P@3 rerank | MRR 基线 | MRR rerank |",
        "|------|------|---------|-----------|---------|-----------|",
    ]
    for r in rows:
        fmt = lambda v: f"{v:.2f}" if v is not None else "-"  # noqa: E731
        lines.append(
            f"| {r['query']} | {r['target']} | {fmt(r['base_p3'])} "
            f"| {fmt(r['rr_p3'])} | {fmt(r['base_mrr'])} | {fmt(r['rr_mrr'])} |"
        )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[4/4] 报告已写入 {out}")


if __name__ == "__main__":
    main()
