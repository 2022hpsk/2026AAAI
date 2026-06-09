#!/usr/bin/env python3
"""GroupMemBench 上的 Mem0 记忆系统 baseline（P4 · 梯队①）。

状态：未验证 / 被卡住。上游 UCSB-NLP-Chang/GroupMemBench 的公开版本只放了
BM25 + text-embedding-3-large 两个 baseline（mem0 被提及但没放出来），所以这个脚本
是我们自己"重建"的 Mem0 baseline。目前还跑不了 / 没法验证，因为它同时需要：
  (1) 一个能调的 LLM——Mem0 的"事实抽取"入库环节、以及 QA-agent + judge 都要用
      （本机没有 OpenAI key；Anthropic 端点需要 ANTHROPIC_API_KEY，见 README）；
  (2) 一个 embedding 后端——建议用本地 CPU 的 sentence-transformers（不需要 key），
      先 `pip install sentence-transformers chromadb`（在 requirements.txt 里取消注释）。

与 BM25 的关键区别（别直接套用 rag_common.run_qa）：
  BM25 检索回来的是"原始消息的下标"；Mem0 检索回来的是"被概括过的记忆文本"。
  所以这里的段落是 mem0 的记忆文本，但拼成和上游**完全一致**的 agent/judge 提示形态
  （保证可比），用下面我们自己的循环来跑。

规模提醒：一个领域约 3 万条消息。逐条做 Mem0 事实抽取 ≈ 每领域 3 万次 LLM 调用
（又贵又慢）。用 --max-messages 先截断到能跑的规模，用 --ingest-batch 把消息成组入库。

（解封后）运行示例：
  python run_mem0.py --domain Finance --qtype all --llm-provider anthropic \
      --agent-model claude-haiku-4-5-20251001 --max-messages 4000
"""
from __future__ import annotations

import argparse
import json
import os
import re
# ★ 关键：本机 192 核，torch 默认用满全部线程 → 容器内超额订阅 → 单次 embedding 要 14s。
#   必须在 import torch / sentence-transformers（mem0 会间接 import）之前限制线程数。
#   实测：限到 8 线程后 embedding 从 14s 降到 0.01s（快上千倍）。
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "8")

import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
REPO = HERE / "GroupMemBench"
sys.path.insert(0, str(REPO))

from baselines.rag_common.eval_lib import (  # noqa: E402
    call_chat, load_conversation_messages, load_env_file, load_questions, read_text,
    split_reasoning_and_final, parse_judgment,
)

DOMAINS = ["Finance", "Technology", "Healthcare", "Manufacturing"]
QTYPES = ["multi_hop", "knowledge_update", "term_ambiguity",
          "user_implicit", "temporal", "abstention"]


def build_mem0(llm_provider: str, agent_model: str, embed_model: str,
               collection: str = "groupmembench", persist_path: str = None,
               max_tokens: int = 100000) -> Any:
    """构造一个 Mem0 Memory：LLM 可配置 + 使用本地 embedding。

    collection/persist_path：chroma 集合名与落盘目录。同名集合落盘后**可跨进程复用**，
    从而"入库一次、之后复跑直接用"，省掉重复的 LLM 抽取（省 token、省时间）。
    max_tokens：抽取调用的输出上限。见下方说明。
    """
    from mem0 import Memory  # noqa
    config: Dict[str, Any] = {
        "embedder": {"provider": "huggingface",
                     "config": {"model": embed_model}},  # CPU 即可，无需 API key
        "vector_store": {"provider": "chroma",
                         "config": {"collection_name": collection,
                                    "path": persist_path or str(HERE / ".mem0_chroma")}},
    }
    # ★ max_tokens 必须很大：deepseek-v4-flash 是推理模型(先花token推理再出JSON)，
    #   且 batch=50 一次要抽 ~50 条事实，实测 out_tokens≈1.06万。8000 会把 JSON 从中间砍断
    #   →该批解析失败存0条(这正是"1000条只存20条"的真因)。给 10w 才稳(实测 finish=stop)。
    MAXTOK = max_tokens
    if llm_provider == "anthropic":
        config["llm"] = {"provider": "anthropic",
                         "config": {"model": agent_model, "temperature": 0.0,
                                    "max_tokens": MAXTOK,
                                    "api_key": os.environ.get("ANTHROPIC_API_KEY")}}
    elif llm_provider == "deepseek":
        # DeepSeek 走 mem0 的 openai 兼容 provider（base_url 指向 deepseek）
        config["llm"] = {"provider": "openai",
                         "config": {"model": agent_model, "temperature": 0.0,
                                    "max_tokens": MAXTOK,
                                    "api_key": os.environ.get("DEEPSEEK_API_KEY"),
                                    "openai_base_url": os.environ.get("DEEPSEEK_BASE_URL",
                                                                      "https://api.deepseek.com")}}
    else:  # openai / 本地 OpenAI 兼容服务
        config["llm"] = {"provider": "openai",
                         "config": {"model": agent_model, "temperature": 0.0,
                                    "max_tokens": MAXTOK,
                                    "openai_base_url": os.environ.get("OPENAI_BASE_URL")}}
    return Memory.from_config(config)


def ingest(mem: Any, messages: List[Dict], group_id: str, batch: int) -> Dict[str, float]:
    """按频道顺序，把消息成组（带作者标签）地加入 mem0。每批 add(infer=True) 都会调 LLM 抽取事实。
    返回计时统计（总耗时、批数、每批平均）。"""
    import time
    buf: List[Dict[str, str]] = []
    n_batches = 0
    per_batch: List[float] = []

    def _flush():
        nonlocal n_batches
        t0 = time.time()
        mem.add(buf, user_id=group_id)
        dt = time.time() - t0
        n_batches += 1
        per_batch.append(dt)
        print(f"  [入库] 第 {n_batches} 批（{len(buf)} 条消息）耗时 {dt:.1f}s", flush=True)

    for m in messages:
        content = (m.get("content") or "").strip()
        if not content:
            continue
        buf.append({"role": "user", "content": f"[{m.get('author','?')}] {content}"})
        if len(buf) >= batch:
            _flush(); buf = []
    if buf:
        _flush()
    total = sum(per_batch)
    return {"ingest_total_s": total, "n_batches": n_batches,
            "avg_batch_s": (total / n_batches if n_batches else 0.0)}


def _msg_lines(messages: List[Dict]) -> List[str]:
    return [f"[{m.get('author','?')}] {(m.get('content') or '').strip()}"
            for m in messages if (m.get('content') or '').strip()]


def ingest_parallel(mem: Any, ext_client: Any, model: str, messages: List[Dict],
                    group_id: str, batch: int, workers: int, max_tokens: int) -> Dict[str, float]:
    """单域内"并行独立抽取"——损失跨批合并(去重/覆盖)换提速。

    与串行版的区别：每批独立抽取(existing_memories=[])、互不依赖 → 用线程池并发跑这些
    DeepSeek 抽取调用(慢的部分)。抽完把所有事实用 infer=False 直接入库(只本地 embed+写，
    不再调 LLM、不再做 additive 合并)。
    代价：无跨批去重/知识更新覆盖(knowledge_update 受损 + 冗余增多)；factual recall 基本不亏。
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from mem0.configs.prompts import ADDITIVE_EXTRACTION_PROMPT, generate_additive_extraction_prompt
    try:
        from mem0.memory.utils import parse_messages
    except Exception:
        parse_messages = lambda ms: "\n".join(f"{m['role']}: {m['content']}" for m in ms)

    lines = _msg_lines(messages)
    batches = [lines[i:i + batch] for i in range(0, len(lines), batch)]

    def _extract(bi_lines):
        bi, blines = bi_lines
        parsed = parse_messages([{"role": "user", "content": x} for x in blines])
        up = generate_additive_extraction_prompt(existing_memories=[], new_messages=parsed,
                                                  last_k_messages=[], custom_instructions=None)
        try:
            r = ext_client.chat.completions.create(
                model=model, temperature=0, max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": ADDITIVE_EXTRACTION_PROMPT},
                          {"role": "user", "content": up}])
            content = r.choices[0].message.content or ""
            mems = json.loads(content).get("memory", [])
            facts = [m.get("text", "") if isinstance(m, dict) else str(m) for m in mems]
            return bi, [f for f in facts if f], r.choices[0].finish_reason
        except Exception as e:
            return bi, [], f"ERR:{str(e)[:60]}"

    t0 = time.time()
    all_facts: List[str] = []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_extract, (bi, b)) for bi, b in enumerate(batches)]
        for fut in as_completed(futs):
            bi, facts, fin = fut.result()
            all_facts.extend(facts)
            done += 1
            print(f"  [并行抽取] {done}/{len(batches)} 批完成（本批 {len(facts)} 条, finish={fin}）", flush=True)
    extract_s = time.time() - t0

    # 直接入库（infer=False：只本地 embed+写，不调 LLM、不合并）
    t1 = time.time()
    if all_facts:
        mem.add([{"role": "user", "content": f} for f in all_facts],
                user_id=group_id, infer=False)
    store_s = time.time() - t1
    print(f"  [入库] 并行抽取 {extract_s:.0f}s（{workers} worker）+ 直接存 {store_s:.0f}s；共 {len(all_facts)} 条事实")
    return {"ingest_total_s": extract_s + store_s, "n_batches": len(batches),
            "n_facts": len(all_facts), "extract_s": round(extract_s, 1), "store_s": round(store_s, 1)}


def run_unit(benchmark: str, unit: str, questions: List[dict], mem: Any, client: Any,
             agent_model: str, judge_model: str, agent_system: str, judge_system: str,
             top_k: int, results_dir: Path, qtype: str = "all", limit: int = None,
             qa_workers: int = 16) -> Dict[str, Dict]:
    """对某个单元(域/网络/话题)的问题跑 Mem0 问答（**按题并行**，检索只读+每题无状态→无损）。
    检索用 user_id=unit（与入库一致）。结果写 results/<benchmark>/<unit>/mem0__<cat>.jsonl。"""
    from concurrent.futures import ThreadPoolExecutor
    # 按类别分组（可按 qtype 过滤、每类 limit）
    cats: Dict[str, List[dict]] = {}
    for q in questions:
        cat = q.get("category", "unknown")
        if qtype != "all" and cat != qtype:
            continue
        cats.setdefault(cat, []).append(q)
    tasks = []
    for cat, qs in cats.items():
        for q in (qs[:limit] if limit else qs):
            tasks.append((cat, q))

    def _one(task):
        cat, q = task
        asker = q.get("asking_user_id") or ""
        query = f"{asker} {q['question']}" if asker else q["question"]
        hits = mem.search(query, top_k=top_k, filters={"user_id": unit}).get("results", [])
        passages = "\n\n".join(f"[{i}] {h.get('memory','')}" for i, h in enumerate(hits, 1))
        agent_user = (f"Asking user: {asker}\n\nQuestion:\n{q['question']}\n\n"
                      f"Retrieved passages:\n{passages}\n\nAnswer the question using the retrieved passages.")
        _, afinal = split_reasoning_and_final(call_chat(client, agent_model, agent_system, agent_user, 1024))
        ju = f"Question:\n{q['question']}\n\nGold Answer:\n{q.get('answer','')}\n\nAgent Answer:\n{afinal}\n"
        _, jfinal = split_reasoning_and_final(call_chat(client, judge_model, judge_system, ju, 512))
        v = parse_judgment(jfinal)
        return cat, {"id": q.get("id", ""), "query": q["question"], "gold": q.get("answer", ""),
                     "agent_answer": afinal, "judge_answer": jfinal,
                     "verdict": "correct" if v is True else "incorrect" if v is False else "unclear"}

    by_cat: Dict[str, List[dict]] = {}
    with ThreadPoolExecutor(max_workers=qa_workers) as ex:
        for cat, rec in ex.map(_one, tasks):
            by_cat.setdefault(cat, []).append(rec)

    summary: Dict[str, Dict] = {}
    for cat, recs in by_cat.items():
        out = results_dir / benchmark / unit / f"mem0__{cat}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        c = sum(1 for r in recs if r["verdict"] == "correct")
        summary[f"{unit}/{cat}"] = {"accuracy": c / len(recs) if recs else 0.0,
                                    "correct": c, "total": len(recs)}
    n = len(tasks); cc = sum(s["correct"] for s in summary.values())
    print(f"[mem0] {unit}: {n} 题，acc {cc/n*100:.1f}% ({cc}/{n})")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default="groupmem", choices=["groupmem", "socialmem", "evermem"],
                    help="哪个 benchmark（经 bench_loaders 统一加载）")
    ap.add_argument("--domain", "--unit", dest="domain", default="Finance",
                    help="单元：GroupMem 领域 / SocialMem network_id / EverMem topic_id；或 all")
    ap.add_argument("--qtype", default="all")
    ap.add_argument("--llm-provider", default="deepseek",
                    choices=["deepseek", "anthropic", "openai", "local"])
    ap.add_argument("--agent-model", default="deepseek-v4-flash")
    ap.add_argument("--judge-model", default="deepseek-v4-flash")
    ap.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--max-messages", type=int, default=4000)
    ap.add_argument("--ingest-batch", type=int, default=50,
                    help="每批消息数（实测 batch=50 配 --llm-max-tokens 10w 不截断）")
    ap.add_argument("--llm-max-tokens", type=int, default=100000,
                    help="mem0 抽取调用的输出上限。batch=50 约需 1.06万 out_tokens，给 10w 留足余量防截断")
    ap.add_argument("--limit", type=int, default=None, help="每类最多取多少题（小测用）")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--force-ingest", action="store_true",
                    help="即便集合已存在也强制重新入库（默认：已入库则跳过，省 token）")
    ap.add_argument("--parallel-extract", type=int, default=1, metavar="N",
                    help="单域内并行抽取的 worker 数。>1 = 每批独立抽取(无跨批合并)并发跑，"
                         "数倍提速，代价是丢去重/知识更新覆盖(knowledge_update受损+冗余)。1 = 原版串行 additive。")
    ap.add_argument("--persist-dir", default=None,
                    help="chroma 持久化目录。默认 .mem0_chroma/<benchmark>（按数据集分目录、命名规范）。"
                         "集合名=<benchmark>__<单元>__m<入库条数>。")
    ap.add_argument("--qa-workers", type=int, default=16, help="问答阶段按题并行数(无状态,无损)")
    ap.add_argument("--results-dir", default=str(HERE / "results"))
    args = ap.parse_args()

    import time
    # 关掉 mem0/chromadb 的遥测（次要）
    os.environ.setdefault("MEM0_TELEMETRY", "False")
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    try:
        import torch; torch.set_num_threads(8)  # 兜底再限一次线程（192核机器的关键优化）
    except Exception:
        pass
    load_env_file(str(HERE / ".env"))  # 读取 复现/.env 里的凭据
    from eval_patches import patch_token_budgets
    patch_token_budgets()  # 与 BM25 一致：token 预算抬高 + temperature=0（可复现）
    import baselines.rag_common.eval_lib as _elib
    globals()["call_chat"] = _elib.call_chat  # run() 用补丁后(temp=0)的 call_chat
    from llm_clients import make_client
    from bench_loaders import iter_units  # 三个 benchmark 的统一 loader
    client = make_client(args.llm_provider)  # 没填 key 会抛出清楚的提示
    agent_system = read_text(str(REPO / "prompts/hipporag_agent_system.txt"))
    judge_system = read_text(str(REPO / "prompts/hipporag_judge_system.txt"))

    # 持久化目录规范化：默认 .mem0_chroma/<benchmark>，按数据集分目录、不混；集合名再带单元+条数。
    persist_dir = args.persist_dir or str(HERE / ".mem0_chroma" / args.benchmark)
    print(f"[存储] chroma 目录 = {persist_dir}；集合命名 = {args.benchmark}__<单元>__m<入库条数>")

    all_summary: Dict[str, Dict] = {}
    # 逐单元：建集合 → (复用或入库) → 该单元问答。每个单元自己的记忆库，互不串台。
    for unit, messages, questions in iter_units(args.benchmark, HERE, args.domain):
        messages = messages[: args.max_messages]
        # 集合命名：<benchmark>__<unit>__m<入库消息数>，清晰区分"哪个数据集/哪个单元/入库多少条"。
        # chroma 名只允许 [a-zA-Z0-9._-]，把单元名里的非法字符替成 -。
        safe_unit = re.sub(r"[^a-zA-Z0-9._-]", "-", str(unit))
        collection = f"{args.benchmark}__{safe_unit}__m{len(messages)}"
        t0 = time.time()
        mem = build_mem0(args.llm_provider, args.agent_model, args.embed_model,
                         collection=collection, persist_path=persist_dir,
                         max_tokens=args.llm_max_tokens)
        print(f"\n=== [{args.benchmark}] 单元 {unit}：{len(messages)} 条消息 | "
              f"build_mem0 {time.time()-t0:.1f}s ===")

        # 复用检查（user_id=unit）：已入库则跳过
        try:
            existing = len(mem.get_all(filters={"user_id": unit}).get("results", []))
        except Exception as e:
            print(f"[警告] get_all 检查失败({e})，按未入库处理"); existing = 0
        if existing > 0 and not args.force_ingest:
            print(f"[复用] 集合 {collection} 已有记忆 → 跳过入库（省 token）。重灌加 --force-ingest")
        elif args.parallel_extract > 1:
            print(f"[入库] {unit}: 并行抽取 {len(messages)} 条（{args.parallel_extract} worker，无跨批合并）...")
            stats = ingest_parallel(mem, client, args.agent_model, messages, unit,
                                    args.ingest_batch, args.parallel_extract, args.llm_max_tokens)
            print(f"[计时] 入库 {stats['ingest_total_s']:.1f}s（抽取 {stats['extract_s']}s+存 {stats['store_s']}s，"
                  f"{stats['n_facts']} 条事实）")
        else:
            print(f"[入库] {unit}: 串行 additive {len(messages)} 条 ...")
            stats = ingest(mem, messages, unit, args.ingest_batch)
            print(f"[计时] 入库 {stats['ingest_total_s']:.1f}s / {stats['n_batches']} 批")

        summ = run_unit(args.benchmark, unit, questions, mem, client, args.agent_model,
                        args.judge_model, agent_system, judge_system, args.top_k,
                        Path(args.results_dir), qtype=args.qtype, limit=args.limit,
                        qa_workers=args.qa_workers)
        all_summary.update(summ)

    from datetime import datetime
    all_summary["_computed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = Path(args.results_dir, f"summary_mem0_{args.benchmark}.json")
    out.write_text(json.dumps(all_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n汇总写入 {out}（{all_summary['_computed_at']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
