#!/usr/bin/env python3
"""GroupMemBench baseline 运行器（P4 · 梯队①）。

封装上游 UCSB-NLP-Chang/GroupMemBench 的"检索 + 问答"流程，使其可以：
  * 跑 BM25（以及之后的 Mem0）检索，覆盖 4 个领域 × 6 类问题；
  * 把 QA-agent + judge 的 LLM 调用路由到 Anthropic 或本地 OpenAI 兼容服务
    （上游默认 gpt-5 走 OpenAI/Azure，本机没有该 key）；
  * 汇总成论文那种"按类别"的准确率表。

不改动克隆下来的上游仓库（保证以后能干净地 git pull），所有适配都在本目录里。

两种模式
--------
--retrieval-only ：不调用任何 LLM。只建索引、取 top-k，并报一个"标准答案是否作为
                   子串出现在 top-k 段落里"的粗略召回率代理。用来在没有任何 key 的
                   情况下，端到端验证"数据加载 + 检索"这条链路。现在就能跑。
(默认)            ：完整"检索 -> QA-agent -> judge"流程（需要 --llm-provider anthropic
                   且配好 ANTHROPIC_API_KEY，或 --llm-provider local 配本地 vLLM）。

示例
----
# 冒烟测试，不用 LLM，每类取 20 题：
python run_baseline.py --baseline bm25 --domain Finance --qtype multi_hop \
    --retrieval-only --limit 20

# 完整跑分（需要先在 .env 里填好 ANTHROPIC_API_KEY）：
python run_baseline.py --baseline bm25 --domain all --qtype all \
    --llm-provider anthropic --agent-model claude-haiku-4-5-20251001 \
    --judge-model claude-haiku-4-5-20251001
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List

HERE = Path(__file__).resolve().parent
REPO = HERE / "GroupMemBench"
if not REPO.exists():
    sys.exit(f"[致命] 找不到上游仓库 {REPO}。请先克隆："
             f"git clone https://github.com/UCSB-NLP-Chang/GroupMemBench.git（或跑 setup.sh）")
sys.path.insert(0, str(REPO))

# 上游模块（仓库已加入 sys.path）
from baselines.rag_common.eval_lib import (  # noqa: E402
    load_conversation_messages,
    load_env_file,
    load_questions,
    message_index_text,
    read_text,
    format_retrieved_message,
    split_reasoning_and_final,
    parse_judgment,
)
from rank_bm25 import BM25Okapi  # noqa: E402

DOMAINS = ["Finance", "Technology", "Healthcare", "Manufacturing"]
QTYPES = ["multi_hop", "knowledge_update", "term_ambiguity",
          "user_implicit", "temporal", "abstention"]

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> List[str]:
    """小写 + 词级切分；保留数字/日期/用户ID，不做停用词处理（保证确定性、无参数）。"""
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def conv_path(domain: str) -> Path:
    return REPO / "data" / "final" / domain / f"synthetic_domain_channels_rolevariants_{domain}.json"


def questions_path(domain: str, qtype: str) -> Path:
    return REPO / "questions" / domain / f"{qtype}.jsonl"


# --------------------------------------------------------------------------- #
# 检索器（与问答解耦，和上游设计一致）
# --------------------------------------------------------------------------- #
def build_bm25_retriever(messages: List[Dict]) -> Callable[[str, int], List[int]]:
    """一条消息=一篇文档；只用消息正文建索引（元数据在展示给 agent 时才拼上）。"""
    corpus = [tokenize(message_index_text(m)) for m in messages]
    bm25 = BM25Okapi(corpus)

    def retrieve(query: str, k: int) -> List[int]:
        q = tokenize(query)
        if not q:
            return []
        scores = bm25.get_scores(q)
        return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    return retrieve


BASELINES = {"bm25": build_bm25_retriever}


# --------------------------------------------------------------------------- #
# 仅检索模式的代理指标（不调 LLM）：标准答案文本是否出现在 top-k 段落里？
# --------------------------------------------------------------------------- #
def gold_recall_at_k(messages, questions, retrieve, k: int) -> Dict[str, float]:
    hits, total, skipped = 0, 0, 0
    for q in questions:
        gold = (q.get("answer") or "").strip().lower()
        # abstention（拒答）类的标准答案是"无相关信息"之类的套话，不是可检索的字符串
        if not gold or gold.startswith("there is no information"):
            skipped += 1
            continue
        asker = q.get("asking_user_id") or ""
        query = f"{asker} {q['question']}" if asker else q["question"]
        idxs = retrieve(query, k)
        joined = " ".join(message_index_text(messages[i]).lower() for i in idxs if 0 <= i < len(messages))
        if gold in joined:
            hits += 1
        total += 1
    return {"recall_at_k": (hits / total if total else 0.0),
            "hits": hits, "scored": total, "skipped_abstention": skipped}


# --------------------------------------------------------------------------- #
# 补充指标：token-EM / token-F1（judge 准确率之外的免费参考指标）
# --------------------------------------------------------------------------- #
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower().rstrip("."))


def token_f1(pred: str, gold: str) -> float:
    p, g = set(_norm(pred).split()), set(_norm(gold).split())
    if not p or not g:
        return 0.0
    common = p & g
    if not common:
        return 0.0
    prec, rec = len(common) / len(p), len(common) / len(g)
    return 2 * prec * rec / (prec + rec)


def exact_match(pred: str, gold: str) -> bool:
    return _norm(pred) == _norm(gold)


# --------------------------------------------------------------------------- #
# 全局题级并行 QA：把所有(单元,类别)的题汇成一个任务池一起并发。
#   检索只读、agent/judge 每题独立无状态 → 并行无损精度。
#   这样即便某些单元题很少(如 SocialMemBench 43 网络×9 类)也能跑满并发。
# --------------------------------------------------------------------------- #
def run_global_qa(tasks, retrieves, msgs_by_unit, client, agent_model, judge_model,
                  agent_system, judge_system, top_k, workers, call_chat, progress_every=50):
    import time
    from concurrent.futures import ThreadPoolExecutor

    def _one(task):
        unit, q = task["unit"], task["q"]
        retrieve, messages = retrieves[unit], msgs_by_unit[unit]
        rec = {"unit": unit, "category": task["cat"], "id": q.get("id", ""),
               "asking_user_id": q.get("asking_user_id", "")}
        gold = q.get("answer", "")
        asker = q.get("asking_user_id") or ""
        query = f"{asker} {q['question']}" if asker else q["question"]
        t0 = time.time(); idxs = retrieve(query, top_k); rec["t_retrieve"] = time.time() - t0
        docs = [format_retrieved_message(messages[i]) for i in idxs if 0 <= i < len(messages)]
        passages = "\n\n".join(f"[{i}] {d}" for i, d in enumerate(docs, 1))
        asker_line = f"Asking user: {asker}\n\n" if asker else ""
        agent_user = (f"{asker_line}Question:\n{q['question']}\n\nRetrieved passages:\n{passages}\n\n"
                      "Answer the question using the retrieved passages.")
        t0 = time.time(); ao = call_chat(client, agent_model, agent_system, agent_user, 512)
        rec["t_agent"] = time.time() - t0
        _, afinal = split_reasoning_and_final(ao)
        ju = f"Question:\n{q['question']}\n\nGold Answer:\n{gold}\n\nAgent Answer:\n{afinal}\n"
        t0 = time.time(); jo = call_chat(client, judge_model, judge_system, ju, 512)
        rec["t_judge"] = time.time() - t0
        _, jfinal = split_reasoning_and_final(jo)
        v = parse_judgment(jfinal)
        rec["verdict"] = "correct" if v is True else "incorrect" if v is False else "unclear"
        rec["em"] = exact_match(afinal, gold); rec["f1"] = token_f1(afinal, gold)
        rec["agent_answer"] = afinal; rec["gold"] = gold
        return rec

    t_wall = time.time(); records = []; done = 0; n = len(tasks)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(_one, tasks):
            records.append(r); done += 1
            if done % progress_every == 0 or done == n:
                acc = sum(1 for x in records if x["verdict"] == "correct") / done
                print(f"  进度 {done}/{n} | 实时 acc {acc*100:.1f}% | {time.time()-t_wall:.0f}s", flush=True)
    return records, round(time.time() - t_wall, 1)


def group_stats(recs: List[dict]) -> Dict[str, float]:
    n = len(recs)
    c = sum(1 for r in recs if r["verdict"] == "correct")
    inc = sum(1 for r in recs if r["verdict"] == "incorrect")
    unc = sum(1 for r in recs if r["verdict"] == "unclear")
    return {"accuracy": c / n if n else 0.0, "correct": c, "incorrect": inc, "unclear": unc,
            "total": n, "unclear_rate": unc / n if n else 0.0,
            "em": sum(1 for r in recs if r["em"]) / n if n else 0.0,
            "f1": sum(r["f1"] for r in recs) / n if n else 0.0,
            "sum_retrieve_s": round(sum(r["t_retrieve"] for r in recs), 1),
            "sum_agent_s": round(sum(r["t_agent"] for r in recs), 1),
            "sum_judge_s": round(sum(r["t_judge"] for r in recs), 1),
            "wall_s": 0.0}


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="bm25", choices=list(BASELINES))
    ap.add_argument("--benchmark", default="groupmem", choices=["groupmem", "socialmem", "evermem"],
                    help="哪个 benchmark：groupmem(领域为单元) / socialmem(network为单元) / evermem(topic为单元)")
    ap.add_argument("--domain", "--unit", dest="domain", default="all",
                    help="单元过滤：GroupMemBench 领域 / SocialMemBench network_id / EverMemBench topic_id；或 all")
    ap.add_argument("--qtype", default="all", help="按问题类别过滤（category），或 all")
    ap.add_argument("--limit", type=int, default=None, help="每个单元最多取多少题")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--retrieval-only", action="store_true", help="只检索、不调 LLM")
    ap.add_argument("--llm-provider", default="deepseek",
                    choices=["deepseek", "anthropic", "openai", "local"])
    ap.add_argument("--agent-model", default="deepseek-v4-flash")
    ap.add_argument("--judge-model", default="deepseek-v4-flash")
    ap.add_argument("--agent-prompt", default=str(REPO / "prompts/hipporag_agent_system.txt"))
    ap.add_argument("--judge-prompt", default=str(REPO / "prompts/hipporag_judge_system.txt"))
    ap.add_argument("--env-file", default=str(HERE / ".env"), help="凭据文件，默认 复现/.env")
    ap.add_argument("--workers", type=int, default=8,
                    help="QA 并发数（按题并行；检索只读+每题无状态→并行无损精度）")
    ap.add_argument("--results-dir", default=str(HERE / "results"))
    args = ap.parse_args()

    import time
    load_env_file(args.env_file)  # 把 .env 里的 key 读进环境变量（已存在的不覆盖）

    from bench_loaders import iter_units  # 三个 benchmark 的统一 loader

    client = None
    call_chat = None
    if not args.retrieval_only:
        from llm_clients import make_client
        from eval_patches import patch_token_budgets
        patch_token_budgets()  # 抬高 token 预算 + temperature=0，避免 DeepSeek 的 Final 行被截断/不可复现
        import baselines.rag_common.eval_lib as _elib
        call_chat = _elib.call_chat   # 取补丁后的 call_chat
        client = make_client(args.llm_provider)  # 没填 key 会抛出一句清楚的中文/英文提示
        agent_system = read_text(args.agent_prompt)
        judge_system = read_text(args.judge_prompt)

    os.makedirs(args.results_dir, exist_ok=True)
    summary: Dict[str, Dict] = {}

    # ── 阶段1：建好所有单元的索引 + 汇总全局任务（题级）──
    retrieves: Dict[str, Callable] = {}
    msgs_by_unit: Dict[str, List[dict]] = {}
    idx_times: Dict[str, float] = {}
    tasks: List[dict] = []
    percat: Dict[tuple, int] = {}
    for unit, messages, questions in iter_units(args.benchmark, HERE, args.domain):
        t_idx = time.time()
        retrieves[unit] = BASELINES[args.baseline](messages)
        idx_times[unit] = time.time() - t_idx
        msgs_by_unit[unit] = messages
        print(f"[索引] [{args.benchmark}] {unit}：{len(messages)} 条消息，建索引 {idx_times[unit]:.1f}s")
        for q in questions:
            cat = q.get("category", "unknown")
            if args.qtype != "all" and cat != args.qtype:
                continue
            k = (unit, cat)
            percat[k] = percat.get(k, 0) + 1
            if args.limit and percat[k] > args.limit:   # 每(单元,类别)限题
                continue
            tasks.append({"unit": unit, "cat": cat, "q": q})
    print(f"[汇总] 共 {len(tasks)} 题，{len(retrieves)} 个单元，建索引合计 {sum(idx_times.values()):.1f}s")

    # ── 阶段2：评测 ──
    qa_wall = 0.0
    if args.retrieval_only:
        groups: Dict[tuple, List[dict]] = {}
        for t in tasks:
            groups.setdefault((t["unit"], t["cat"]), []).append(t["q"])
        for (unit, cat), qs in groups.items():
            res = gold_recall_at_k(msgs_by_unit[unit], qs, retrieves[unit], args.top_k)
            summary[f"{unit}/{cat}"] = res
    else:
        print(f"[问答] 全局题级并行，{args.workers} 并发，共 {len(tasks)} 题 ...")
        records, qa_wall = run_global_qa(
            tasks, retrieves, msgs_by_unit, client, args.agent_model, args.judge_model,
            agent_system, judge_system, args.top_k, args.workers, call_chat)
        # 按(单元,类别)分组：写逐题 jsonl + 统计
        gr: Dict[tuple, List[dict]] = {}
        for r in records:
            gr.setdefault((r["unit"], r["category"]), []).append(r)
        for (unit, cat), recs in gr.items():
            out = Path(args.results_dir) / args.benchmark / unit / f"{args.baseline}__{cat}.jsonl"
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                for r in recs:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            res = group_stats(recs)
            res["index_build_s"] = round(idx_times.get(unit, 0.0), 1)
            summary[f"{unit}/{cat}"] = res
        print(f"[问答] 全部完成，墙钟 {qa_wall}s（{args.workers} 并发）")

    # 汇总
    print("\n" + "=" * 64)
    report: Dict[str, Dict] = {"per_unit_cat": summary}
    if args.retrieval_only:
        by_cat: Dict[str, List[float]] = {}
        for key, res in summary.items():
            by_cat.setdefault(key.split("/", 1)[1], []).append(res["recall_at_k"])
        print(f"[{args.benchmark}] 按类别平均 recall@{args.top_k}：")
        for cat in sorted(by_cat):
            v = by_cat[cat]; print(f"  {cat:18s}: {sum(v)/len(v)*100:5.1f}%  (n={len(v)})")
        allv = [r["recall_at_k"] for r in summary.values()]
        if allv: print(f"  {'总体':18s}: {sum(allv)/len(allv)*100:5.1f}%")
        report["overall"] = {"recall_at_k_mean": (sum(allv)/len(allv) if allv else 0.0)}
    else:
        # 微平均（按题数加总，比"各 key 准确率再平均"更准）
        def agg(keys):
            c = sum(summary[k]["correct"] for k in keys); inc = sum(summary[k]["incorrect"] for k in keys)
            unc = sum(summary[k]["unclear"] for k in keys); t = sum(summary[k]["total"] for k in keys)
            em = sum(summary[k]["em"] * summary[k]["total"] for k in keys)
            f1 = sum(summary[k]["f1"] * summary[k]["total"] for k in keys)
            return {"correct": c, "incorrect": inc, "unclear": unc, "total": t,
                    "accuracy": c / t if t else 0.0, "unclear_rate": unc / t if t else 0.0,
                    "em": em / t if t else 0.0, "f1": f1 / t if t else 0.0}
        # 按类别
        cats: Dict[str, List[str]] = {}
        for k in summary: cats.setdefault(k.split("/", 1)[1], []).append(k)
        print(f"[{args.benchmark}] 按类别（judge 准确率 / EM / F1 / 不明率）：")
        report["per_category"] = {}
        for cat in sorted(cats):
            a = agg(cats[cat]); report["per_category"][cat] = a
            print(f"  {cat:16s}: acc {a['accuracy']*100:5.1f}%  EM {a['em']*100:5.1f}%  "
                  f"F1 {a['f1']*100:5.1f}%  不明 {a['unclear_rate']*100:4.1f}%  (n={a['total']})")
        # 按单元
        units: Dict[str, List[str]] = {}
        for k in summary: units.setdefault(k.split("/", 1)[0], []).append(k)
        report["per_unit"] = {u: agg(ks) for u, ks in units.items()}
        # 总体 + 计时
        ov = agg(list(summary)); report["overall"] = ov
        report["timing"] = {"qa_wall_s": qa_wall,
                            "index_build_s": round(sum(idx_times.values()), 1),
                            "agent_s_sum": round(sum(r["sum_agent_s"] for r in summary.values()), 1),
                            "judge_s_sum": round(sum(r["sum_judge_s"] for r in summary.values()), 1),
                            "retrieve_s_sum": round(sum(r["sum_retrieve_s"] for r in summary.values()), 1),
                            "workers": args.workers}
        print(f"  {'总体':16s}: acc {ov['accuracy']*100:5.1f}%  EM {ov['em']*100:5.1f}%  "
              f"F1 {ov['f1']*100:5.1f}%  不明 {ov['unclear_rate']*100:4.1f}%  (n={ov['total']})")
        print(f"  计时: QA 墙钟 {qa_wall}s（{args.workers}并发）/ 建索引 {report['timing']['index_build_s']}s "
              f"/ agent {report['timing']['agent_s_sum']}s+judge {report['timing']['judge_s_sum']}s（调用累计）")

    from datetime import datetime
    report["computed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 任务1：summary 带具体时间
    tag = "retrieval_only" if args.retrieval_only else "qa"
    summ_path = Path(args.results_dir) / f"summary_{args.benchmark}_{args.baseline}_{tag}.json"
    summ_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n详细汇总已写入 {summ_path}（计算时间 {report['computed_at']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
