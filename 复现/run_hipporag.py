#!/usr/bin/env python3
"""HippoRAG (2.0, OSU-NLP-Group) baseline —— 三数据集统一跑。

HippoRAG = RAG + 知识图谱(OpenIE 抽三元组) + Personalized PageRank 检索。
检索单位是"passage"(段落)，所以先把每个单元的多方对话按 session/频道切成 passage 再 index。
QA-agent + judge 仍走我们统一的 DeepSeek 客户端(eval_patches 抬token+temp0)，与 BM25/Mem0/A-MEM 可比。
逐题结果写 results/<benchmark>/<unit>/hipporag__<cat>.jsonl → compute_metrics.py --baseline hipporag 可重算。

★ 安装（独立 venv，避免污染主环境/降级 torch）：
  /opt/conda/bin/python -m venv venv_hippo
  venv_hippo/bin/pip install hipporag==2.0.0a4   # 含 torch2.5.1/transformers4.45.2/igraph 等；vllm 非顶层可跳过
  （若 vllm 装不上(无GPU)：--no-deps 装 hipporag，再手装 networkx python-igraph tiktoken gritlm tenacity einops openai litellm transformers==4.45.2 torch==2.5.1+cpu）

★ 接 DeepSeek + 本地嵌入（关键）：
  - LLM(OpenIE/linking)：llm_model_name="deepseek-v4-flash", llm_base_url="https://api.deepseek.com",
    并设 OPENAI_API_KEY=<DeepSeek key>（HippoRAG 的 openai_gpt.py 走 OpenAI SDK）。
  - 嵌入：DeepSeek 无 embedding API → 用本地 Contriever(CPU)：embedding_model_name="facebook/contriever"。

⚠️ OpenIE 索引 = 大量 LLM 调用(每 passage 抽三元组)，比 A-MEM 还重 → 用 --max-passages 截断先验证。
用法（在 venv_hippo 里）：
  PYTHONPATH=. venv_hippo/bin/python run_hipporag.py --benchmark socialmem --domain grp_xxx --max-passages 40 --qtype Q1 --limit 2
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "8")

# ★ vllm 桩：HippoRAG.py 顶层会 import openie_vllm_offline → import vllm(要GPU/CUDA)。
#   我们用 DeepSeek(OpenAI) 后端、根本不用 vllm，故注入假 vllm 满足 import，避免装重型 vllm。
import sys as _sys, types as _types
if "vllm" not in _sys.modules:
    class _VStub:
        def __init__(self, *a, **k): pass
    _v = _types.ModuleType("vllm"); _v.SamplingParams = _VStub; _v.LLM = _VStub
    _sys.modules["vllm"] = _v
    for _m in ("vllm.model_executor", "vllm.model_executor.guided_decoding"):
        _sys.modules[_m] = _types.ModuleType(_m)
    _gf = _types.ModuleType("vllm.model_executor.guided_decoding.guided_fields")
    _gf.GuidedDecodingRequest = _VStub
    _sys.modules["vllm.model_executor.guided_decoding.guided_fields"] = _gf

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "GroupMemBench"))

from baselines.rag_common.eval_lib import (  # noqa: E402
    load_env_file, read_text, split_reasoning_and_final, parse_judgment,
)

call_chat = None  # eval_patches 注入


def messages_to_passages(messages: List[dict], max_passages: int) -> List[str]:
    """把多方对话按 频道+session 分块成 passage（HippoRAG 的检索单位）。
    每个 passage = 同一频道/会话内若干连续消息拼接(带作者)。"""
    by_ch: Dict[str, List[dict]] = {}
    for m in messages:
        by_ch.setdefault(str(m.get("_channel", "")), []).append(m)
    passages: List[str] = []
    CHUNK = 8  # 每 8 条消息成一个 passage
    for ch, msgs in by_ch.items():
        for i in range(0, len(msgs), CHUNK):
            block = msgs[i:i + CHUNK]
            txt = "\n".join(f"[{m.get('author','?')}] {(m.get('content') or '').strip()}"
                            for m in block if (m.get('content') or '').strip())
            if txt:
                passages.append(txt)
    return passages[:max_passages]


def build_hipporag(save_dir: str, llm_model: str, embed_model: str):
    """构造 HippoRAG：LLM 走 DeepSeek(OpenAI 兼容)，嵌入用本地 Contriever。"""
    from hipporag import HippoRAG
    dk = os.environ.get("DEEPSEEK_API_KEY", "")
    if dk:
        os.environ["OPENAI_API_KEY"] = dk   # HippoRAG 的 openai_gpt 走 OpenAI SDK
    return HippoRAG(
        save_dir=save_dir,
        llm_model_name=llm_model,
        llm_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        embedding_model_name=embed_model,   # 本地 Contriever，CPU
    )


def run_unit(benchmark, unit, hr, passages, questions, client, llm_model,
             agent_system, judge_system, top_k, results_dir, qtype="all", limit=None, qa_workers=8):
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
        # HippoRAG 检索 top-k passage
        res = hr.retrieve(queries=[q["question"]], num_to_retrieve=top_k)
        docs = res[0].docs if hasattr(res[0], "docs") else res[0].get("docs", [])
        passages_txt = "\n\n".join(f"[{i}] {d}" for i, d in enumerate(docs, 1))
        au = (f"Question:\n{q['question']}\n\nRetrieved passages:\n{passages_txt}\n\n"
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
        out = results_dir / benchmark / unit / f"hipporag__{cat}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        c = sum(1 for r in recs if r["verdict"] == "correct")
        summary[f"{unit}/{cat}"] = {"accuracy": c / len(recs) if recs else 0.0,
                                    "correct": c, "total": len(recs)}
    n = len(tasks); cc = sum(s["correct"] for s in summary.values())
    print(f"[hipporag] {unit}: {n} 题，acc {cc/n*100:.1f}% ({cc}/{n})" if n else f"[hipporag] {unit}: 0 题")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default="groupmem", choices=["groupmem", "socialmem", "evermem"])
    ap.add_argument("--domain", "--unit", dest="domain", default="Finance")
    ap.add_argument("--qtype", default="all")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-passages", type=int, default=200, help="每单元最多索引多少 passage(OpenIE 很贵)")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--llm-model", default="deepseek-v4-flash", help="QA-agent/judge 模型(思考模式)")
    ap.add_argument("--openie-llm", default="deepseek-chat",
                    help="OpenIE(NER+三元组抽取)模型。默认 deepseek-chat(非思考)→抽取不需推理，省 ~2.4× token")
    ap.add_argument("--embed-model", default="facebook/contriever")
    ap.add_argument("--qa-workers", type=int, default=8)
    ap.add_argument("--save-dir", default=str(HERE / ".hipporag_store"))
    ap.add_argument("--results-dir", default=str(HERE / "results"))
    args = ap.parse_args()

    load_env_file(str(HERE / ".env"))
    from eval_patches import patch_token_budgets
    patch_token_budgets()
    import baselines.rag_common.eval_lib as _elib
    globals()["call_chat"] = _elib.call_chat
    from llm_clients import make_client
    from bench_loaders import iter_units
    client = make_client("deepseek")
    agent_system = read_text(str(HERE / "GroupMemBench/prompts/hipporag_agent_system.txt"))
    judge_system = read_text(str(HERE / "GroupMemBench/prompts/hipporag_judge_system.txt"))

    all_summary: Dict[str, Dict] = {}
    for unit, messages, questions in iter_units(args.benchmark, HERE, args.domain):
        passages = messages_to_passages(messages, args.max_passages)
        print(f"\n=== [hipporag/{args.benchmark}] 单元 {unit}：{len(passages)} 个 passage -> OpenIE 索引 ===")
        hr = build_hipporag(os.path.join(args.save_dir, f"{args.benchmark}_{unit}"),
                            args.openie_llm, args.embed_model)  # OpenIE 用非思考模型省 token
        hr.index(docs=passages)   # OpenIE 抽三元组 + 建图 + 嵌入（大量 LLM 调用）
        summ = run_unit(args.benchmark, unit, hr, passages, questions, client, args.llm_model,
                        agent_system, judge_system, args.top_k, Path(args.results_dir),
                        qtype=args.qtype, limit=args.limit, qa_workers=args.qa_workers)
        all_summary.update(summ)

    out = Path(args.results_dir, f"summary_hipporag_{args.benchmark}.json")
    out.write_text(json.dumps(all_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n汇总写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
