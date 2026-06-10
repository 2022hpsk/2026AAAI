#!/usr/bin/env python3
"""A-MEM（Agentic Memory, agiresearch/A-mem）baseline —— 三数据集统一跑。

与 Mem0 同构：开源框架 + 本地 MiniLM embedding + 调 LLM 做"笔记/链接构建"，检索回"记忆文本"。
QA-agent + judge 仍走我们统一的 DeepSeek 客户端(经 eval_patches 抬 token+temp0)，与 BM25/Mem0 完全可比。
逐题结果写 results/<benchmark>/<unit>/amem__<cat>.jsonl → compute_metrics.py --baseline amem 可重算。

A-MEM 接 DeepSeek：openai SDK 自动读 OPENAI_BASE_URL；设 OPENAI_API_KEY=<deepseek>、
OPENAI_BASE_URL=https://api.deepseek.com、llm_model=deepseek-v4-flash 即可(已验证 base_url 生效)。

⚠️ A-MEM 入库 add_note 每条都调 LLM 做笔记/链接构建(读改写、串行) → 很贵很慢；用 --max-messages 截断。
用法：
  python run_amem.py --benchmark socialmem --domain grp_xxx --max-messages 60 --qtype Q1 --limit 3
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "8")   # 192核机器：限线程，否则单次 embedding 14s
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "GroupMemBench"))

from baselines.rag_common.eval_lib import (  # noqa: E402
    load_env_file, read_text, split_reasoning_and_final, parse_judgment,
)

call_chat = None  # 由 eval_patches 补丁后的版本在 main 里注入


def build_amem(model_embed: str, llm_model: str):
    """构造 A-MEM；LLM 走 OpenAI 兼容后端（openai SDK 自动读 OPENAI_BASE_URL → DeepSeek）。"""
    from agentic_memory.memory_system import AgenticMemorySystem
    # 强制赋值（.env 里可能有空的 OPENAI_API_KEY=，不能用 setdefault 否则不覆盖）
    dk = os.environ.get("DEEPSEEK_API_KEY", "")
    if dk:
        os.environ["OPENAI_API_KEY"] = dk
    os.environ["OPENAI_BASE_URL"] = os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"

    # ★ 补丁：A-MEM 原用 json_schema 结构化输出，DeepSeek 不支持(400) → 改成 json_object；
    #   并把 max_tokens 从 1000 调大(deepseek-v4-flash 是推理模型，否则被截断)。
    from agentic_memory.llm_controller import OpenAIController

    def _patched_get_completion(self, prompt, response_format=None, temperature=0.7):
        r = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": "You must respond with a JSON object."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, temperature=temperature, max_tokens=8000)
        return r.choices[0].message.content
    OpenAIController.get_completion = _patched_get_completion

    return AgenticMemorySystem(model_name=model_embed, llm_backend="openai", llm_model=llm_model)


def ingest(ms, messages: List[dict], max_messages: int,
           batch_size: int = 64, workers: int = 16) -> int:
    """A-MEM 批量入库（保留增量图特性 + 提高吞吐 + 省 token）。

    每条消息一条 note。每条 add_note 内部 = analyze_content(1次LLM 生成元数据) +
    process_memory 的"记忆演化"(KNN 找邻居 + 1次LLM 决定链接/更新邻居)。串行 ~12s/条。
    批量化：每批 batch_size 条**并发**跑(workers 线程) → 批内并发生成note+embedding+KNN+图更新→commit；
    批间串行(barrier) → 下一批的演化能看到上一批已 commit 的记忆，**保留增量图**(batch1→graph1, batch2→graph2…)。
    代价：批内并发对邻居的演化是"读改写"，可能轻微脏写/丢链接(与 Mem0 并行变体同性质)，换数倍提速。
    """
    import time
    from concurrent.futures import ThreadPoolExecutor
    contents = []
    for m in messages[:max_messages]:
        c = (m.get("content") or "").strip()
        if c:
            contents.append((f"[{m.get('author','?')}] {c}", str(m.get("author", "?")), str(m.get("_channel", ""))))
    t0 = time.time()
    n = 0
    for i in range(0, len(contents), batch_size):
        batch = contents[i:i + batch_size]

        def _one(item):
            try:
                ms.add_note(content=item[0], tags=[item[1]], category=item[2])
            except Exception as e:
                print(f"    [入库warn] add_note 失败: {str(e)[:80]}", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as ex:   # 批内并发；with 退出=批 barrier
            list(ex.map(_one, batch))
        n += len(batch)
        print(f"  [批量入库] {n}/{len(contents)} 条（batch={batch_size}, {workers}并发, {time.time()-t0:.0f}s）", flush=True)
    print(f"  [入库] 共 {n} 条 note，耗时 {time.time()-t0:.0f}s（chroma 实存 {len(ms.memories)} 条）")
    return n


def run_unit(benchmark, unit, questions, ms, client, llm_model, agent_system, judge_system,
             top_k, results_dir, qtype="all", limit=None, qa_workers=16) -> Dict[str, Dict]:
    """该单元问答（按题并行；检索只读、每题无状态→无损）。"""
    from concurrent.futures import ThreadPoolExecutor
    cats: Dict[str, List[dict]] = {}
    for q in questions:
        cat = q.get("category", "unknown")
        if qtype != "all" and cat != qtype:
            continue
        cats.setdefault(cat, []).append(q)
    tasks = [(cat, q) for cat, qs in cats.items() for q in (qs[:limit] if limit else qs)]

    def _one(task):
        cat, q = task
        hits = ms.search_agentic(q["question"], k=top_k)  # List[Dict]，取 content
        passages = "\n\n".join(f"[{i}] {h.get('content','') if isinstance(h, dict) else h}"
                               for i, h in enumerate(hits, 1))
        au = (f"Question:\n{q['question']}\n\nRetrieved passages:\n{passages}\n\n"
              "Answer the question using the retrieved passages.")
        _, af = split_reasoning_and_final(call_chat(client, llm_model, agent_system, au, 1024))
        ju = f"Question:\n{q['question']}\n\nGold Answer:\n{q.get('answer','')}\n\nAgent Answer:\n{af}\n"
        _, jf = split_reasoning_and_final(call_chat(client, llm_model, judge_system, ju, 512))
        v = parse_judgment(jf)
        return cat, {"id": q.get("id", ""), "query": q["question"], "gold": q.get("answer", ""),
                     "agent_answer": af, "judge_answer": jf,
                     "verdict": "correct" if v is True else "incorrect" if v is False else "unclear"}

    by_cat: Dict[str, List[dict]] = {}
    with ThreadPoolExecutor(max_workers=qa_workers) as ex:
        for cat, rec in ex.map(_one, tasks):
            by_cat.setdefault(cat, []).append(rec)

    summary = {}
    for cat, recs in by_cat.items():
        out = results_dir / benchmark / unit / f"amem__{cat}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        c = sum(1 for r in recs if r["verdict"] == "correct")
        summary[f"{unit}/{cat}"] = {"accuracy": c / len(recs) if recs else 0.0,
                                    "correct": c, "total": len(recs)}
    n = len(tasks); cc = sum(s["correct"] for s in summary.values())
    print(f"[amem] {unit}: {n} 题，acc {cc/n*100:.1f}% ({cc}/{n})" if n else f"[amem] {unit}: 0 题")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default="groupmem", choices=["groupmem", "socialmem", "evermem"])
    ap.add_argument("--domain", "--unit", dest="domain", default="Finance", help="单元；或 all")
    ap.add_argument("--qtype", default="all")
    ap.add_argument("--limit", type=int, default=None, help="每类最多取多少题")
    ap.add_argument("--max-messages", type=int, default=2000, help="入库消息上限（A-MEM 每条调 LLM）")
    ap.add_argument("--batch-size", type=int, default=64, help="批量入库每批条数(批内并发)")
    ap.add_argument("--ingest-workers", type=int, default=16, help="批内并发 worker 数")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--embed-model", default="all-MiniLM-L6-v2")
    ap.add_argument("--llm-model", default="deepseek-v4-flash")
    ap.add_argument("--qa-workers", type=int, default=16)
    ap.add_argument("--results-dir", default=str(HERE / "results"))
    args = ap.parse_args()

    try:
        import torch; torch.set_num_threads(8)
    except Exception:
        pass
    load_env_file(str(HERE / ".env"))
    from eval_patches import patch_token_budgets
    patch_token_budgets()  # 与 BM25/Mem0 一致：token 预算+temp0
    import baselines.rag_common.eval_lib as _elib
    globals()["call_chat"] = _elib.call_chat
    from llm_clients import make_client
    from bench_loaders import iter_units
    client = make_client("deepseek")  # QA/judge 统一 DeepSeek
    agent_system = read_text(str(HERE / "GroupMemBench/prompts/hipporag_agent_system.txt"))
    judge_system = read_text(str(HERE / "GroupMemBench/prompts/hipporag_judge_system.txt"))

    all_summary: Dict[str, Dict] = {}
    for unit, messages, questions in iter_units(args.benchmark, HERE, args.domain):
        print(f"\n=== [amem/{args.benchmark}] 单元 {unit}：入库 {min(len(messages),args.max_messages)} 条 ===")
        ms = build_amem(args.embed_model, args.llm_model)  # 每单元独立记忆
        ingest(ms, messages, args.max_messages, batch_size=args.batch_size, workers=args.ingest_workers)
        summ = run_unit(args.benchmark, unit, questions, ms, client, args.llm_model,
                        agent_system, judge_system, args.top_k, Path(args.results_dir),
                        qtype=args.qtype, limit=args.limit, qa_workers=args.qa_workers)
        all_summary.update(summ)

    from datetime import datetime
    all_summary["_computed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = Path(args.results_dir, f"summary_amem_{args.benchmark}.json")
    out.write_text(json.dumps(all_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n汇总写入 {out}（{all_summary['_computed_at']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
