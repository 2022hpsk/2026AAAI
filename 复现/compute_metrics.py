#!/usr/bin/env python3
"""从已跑好的结果文件**重算全套指标**（不调 API）。

读 results/<benchmark>/<unit>/<baseline>__<cat>.jsonl（每题含 agent_answer/gold/verdict 或 judge_answer），
重算并补齐指标，输出带【具体时间戳】的详细 summary。

指标对齐 论文草稿-Experiments + 汇报V2 §6.2：
  主指标：judge 准确率 / EM / token-F1 / per-category / **attribution acc(归属准确率，本次补齐)**
  专属指标(cross-speaker leakage / audience adaptation)：需说话人级真值标注，
    公开 benchmark 的 baseline QA 答案无法直接计算 → 留给我们方法的记忆结构评估，此处不强算。

用法：
  PYTHONPATH=. ./venv/bin/python compute_metrics.py --benchmark groupmem --baseline bm25
  PYTHONPATH=. ./venv/bin/python compute_metrics.py --benchmark all --baseline bm25
"""
from __future__ import annotations
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "GroupMemBench"))
from bench_loaders import iter_units  # noqa: E402
from baselines.rag_common.eval_lib import parse_judgment  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower().rstrip("."))


def token_f1(pred: str, gold: str) -> float:
    p, g = set(norm(pred).split()), set(norm(gold).split())
    if not p or not g:
        return 0.0
    c = p & g
    if not c:
        return 0.0
    prec, rec = len(c) / len(p), len(c) / len(g)
    return 2 * prec * rec / (prec + rec)


def is_em(pred: str, gold: str) -> bool:
    return norm(pred) == norm(gold)


def attribution(pred: str, gold: str, speakers: set) -> Optional[float]:
    """归属准确率(启发式)：gold 里点了哪些说话人，pred 是否也点对了。
    gold 不涉及说话人 → 返回 None(不计入)。"""
    gl, pl = (gold or "").lower(), (pred or "").lower()
    gt = [s for s in speakers if s and s.lower() in gl]
    if not gt:
        return None
    pr = [s for s in speakers if s and s.lower() in pl]
    return len(set(gt) & set(pr)) / len(gt)


def speakers_of(benchmark: str) -> Dict[str, set]:
    """各单元的说话人集合（用于 attribution）。从 bench_loaders 的消息 author 收集。"""
    out: Dict[str, set] = {}
    for unit, msgs, _ in iter_units(benchmark, HERE, "all"):
        out[unit] = {str(m.get("author", "")).strip() for m in msgs if m.get("author")}
    return out


def verdict_of(r: dict) -> str:
    if r.get("verdict") in ("correct", "incorrect", "unclear"):
        return r["verdict"]
    v = parse_judgment(r.get("judge_answer", ""))
    return "correct" if v is True else "incorrect" if v is False else "unclear"


def micro(recs: List[dict]) -> Dict:
    n = len(recs)
    if not n:
        return {}
    c = sum(1 for r in recs if r["_verdict"] == "correct")
    inc = sum(1 for r in recs if r["_verdict"] == "incorrect")
    unc = sum(1 for r in recs if r["_verdict"] == "unclear")
    attrs = [r["_attr"] for r in recs if r["_attr"] is not None]
    return {
        "accuracy": round(c / n, 4), "correct": c, "incorrect": inc, "unclear": unc, "total": n,
        "unclear_rate": round(unc / n, 4),
        "em": round(sum(1 for r in recs if r["_em"]) / n, 4),
        "f1": round(sum(r["_f1"] for r in recs) / n, 4),
        "attribution_acc": (round(sum(attrs) / len(attrs), 4) if attrs else None),
        "attribution_n": len(attrs),   # 多少题涉及说话人归属
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default="groupmem", choices=["groupmem", "socialmem", "evermem", "all"])
    ap.add_argument("--baseline", default="bm25")
    ap.add_argument("--results-dir", default=str(HERE / "results"))
    args = ap.parse_args()

    benches = ["groupmem", "socialmem", "evermem"] if args.benchmark == "all" else [args.benchmark]
    for bench in benches:
        base = Path(args.results_dir) / bench
        if not base.exists():
            print(f"[跳过] 无结果目录 {base}")
            continue
        print(f"\n========== 重算 {bench} / {args.baseline} ==========")
        spk = speakers_of(bench)
        recs: List[dict] = []
        for unitdir in sorted(base.iterdir()):
            if not unitdir.is_dir():
                continue
            for f in sorted(unitdir.glob(f"{args.baseline}__*.jsonl")):
                cat = f.stem.split("__", 1)[1]
                for line in open(f, encoding="utf-8"):
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    r["unit"] = unitdir.name
                    r["category"] = r.get("category", cat)
                    pred, gold = r.get("agent_answer", ""), r.get("gold", "")
                    r["_verdict"] = verdict_of(r)
                    r["_em"] = is_em(pred, gold)
                    r["_f1"] = token_f1(pred, gold)
                    r["_attr"] = attribution(pred, gold, spk.get(unitdir.name, set()))
                    recs.append(r)
        if not recs:
            print(f"[跳过] {bench} 无结果文件"); continue

        by_cat: Dict[str, List[dict]] = {}
        by_unit: Dict[str, List[dict]] = {}
        for r in recs:
            by_cat.setdefault(r["category"], []).append(r)
            by_unit.setdefault(r["unit"], []).append(r)

        report = {
            "benchmark": bench, "baseline": args.baseline,
            "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall": micro(recs),
            "per_category": {c: micro(rs) for c, rs in sorted(by_cat.items())},
            "per_unit": {u: micro(rs) for u, rs in by_unit.items()},
        }
        ov = report["overall"]
        print(f"按类别（judge准确率 / EM / F1 / 归属acc / 不明率）：")
        for c, m in report["per_category"].items():
            aa = f"{m['attribution_acc']*100:.1f}%(n={m['attribution_n']})" if m["attribution_acc"] is not None else "—"
            print(f"  {c:16s}: acc {m['accuracy']*100:5.1f}%  EM {m['em']*100:5.1f}%  "
                  f"F1 {m['f1']*100:5.1f}%  归属 {aa:>14s}  不明 {m['unclear_rate']*100:4.1f}%  (n={m['total']})")
        aa = f"{ov['attribution_acc']*100:.1f}%(n={ov['attribution_n']})" if ov["attribution_acc"] is not None else "—"
        print(f"  {'总体':16s}: acc {ov['accuracy']*100:5.1f}%  EM {ov['em']*100:5.1f}%  "
              f"F1 {ov['f1']*100:5.1f}%  归属 {aa:>14s}  不明 {ov['unclear_rate']*100:4.1f}%  (n={ov['total']})")

        out = Path(args.results_dir) / f"metrics_{bench}_{args.baseline}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [时间] {report['computed_at']}  → 写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
