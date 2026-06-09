#!/usr/bin/env python3
"""A-MEM（Agentic Memory）baseline —— 在多方 benchmark 上跑（P4 · 梯队/扩展）。

状态：脚本就绪，但**未实跑/未验证**，因为：
  (1) 需要先装 A-MEM：`git clone https://github.com/agiresearch/A-mem && cd A-mem && pip install .`
      （包名 agentic_memory；依赖 chromadb + sentence-transformers，我们已装）。
  (2) A-MEM 的 note 构建会调商用 LLM（llm_backend="openai"）；我们指向 DeepSeek
      （设 OPENAI_API_KEY=DeepSeek key、OPENAI_BASE_URL=https://api.deepseek.com，
      llm_model="deepseek-v4-flash"）。⚠️ 需确认 A-MEM 是否透传 OPENAI_BASE_URL；
      若不透传，要么改用 Ollama 本地后端，要么小补丁。
  (3) 未经用户允许不发真实 API 调用。

A-MEM 与 Mem0 同构（开源框架 + 本地 embedding + 调 LLM 做"笔记/记忆构建"），
所以这里复用 run_mem0 的"检索回记忆文本 -> 拼成上游 agent/judge 提示"的同一套 QA 循环。

A-MEM API（来自官方 README）：
  from agentic_memory.memory_system import AgenticMemorySystem
  ms = AgenticMemorySystem(model_name='all-MiniLM-L6-v2', llm_backend='openai', llm_model='deepseek-v4-flash')
  ms.add_note(content=..., tags=[...], category=..., timestamp='YYYYMMDDHHmm')
  results = ms.search_agentic(query, k=10)   # 返回若干条记忆

用法（解封后）：
  python run_amem.py --benchmark groupmem --domain Finance --max-messages 4000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "GroupMemBench"))

from baselines.rag_common.eval_lib import (  # noqa: E402
    call_chat, load_env_file, read_text, split_reasoning_and_final, parse_judgment,
)


def build_amem(model_embed: str, llm_model: str):
    """构造 A-MEM；LLM 走 OpenAI 兼容后端（指向 DeepSeek）。"""
    from agentic_memory.memory_system import AgenticMemorySystem  # 需先安装 A-MEM
    # A-MEM 用 OpenAI SDK；用 DeepSeek 的 key/base_url 顶替
    os.environ.setdefault("OPENAI_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
    os.environ.setdefault("OPENAI_BASE_URL", os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    return AgenticMemorySystem(model_name=model_embed, llm_backend="openai", llm_model=llm_model)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default="groupmem", choices=["groupmem", "socialmem", "evermem"])
    ap.add_argument("--domain", default="Finance", help="单元过滤")
    ap.add_argument("--max-messages", type=int, default=4000, help="入库消息上限（A-MEM 每条都会调 LLM）")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--embed-model", default="all-MiniLM-L6-v2")
    ap.add_argument("--llm-model", default="deepseek-v4-flash")
    ap.add_argument("--results-dir", default=str(HERE / "results"))
    args = ap.parse_args()

    load_env_file(str(HERE / ".env"))
    from bench_loaders import iter_units
    agent_system = read_text(str(HERE / "GroupMemBench/prompts/hipporag_agent_system.txt"))
    judge_system = read_text(str(HERE / "GroupMemBench/prompts/hipporag_judge_system.txt"))

    # QA/judge 仍走我们统一的 DeepSeek 客户端（与 BM25/Mem0 一致，保证可比）
    from llm_clients import make_client
    client = make_client("deepseek")

    ms = build_amem(args.embed_model, args.llm_model)

    summary = {}
    for unit, messages, questions in iter_units(args.benchmark, HERE, args.domain):
        # 入库（每条消息一条 note；A-MEM 会调 LLM 做笔记构建）
        for m in messages[: args.max_messages]:
            content = (m.get("content") or "").strip()
            if content:
                ms.add_note(content=f"[{m.get('author','?')}] {content}",
                            tags=[m.get("author", "?")], category=m.get("_channel", ""))
        # 检索 + 作答 + 判分
        for q in questions:
            hits = ms.search_agentic(q["question"], k=args.top_k)
            passages = "\n\n".join(f"[{i}] {h}" for i, h in enumerate(hits, 1))
            au = (f"Question:\n{q['question']}\n\nRetrieved passages:\n{passages}\n\n"
                  "Answer the question using the retrieved passages.")
            _, af = split_reasoning_and_final(call_chat(client, args.llm_model, agent_system, au, 1024))
            ju = f"Question:\n{q['question']}\n\nGold Answer:\n{q.get('answer','')}\n\nAgent Answer:\n{af}\n"
            _, jf = split_reasoning_and_final(call_chat(client, args.llm_model, judge_system, ju, 512))
            key = f"{unit}/{q.get('category','?')}"
            s = summary.setdefault(key, {"correct": 0, "total": 0})
            s["total"] += 1
            s["correct"] += 1 if parse_judgment(jf) is True else 0
        print(f"[amem] {unit} 完成")

    Path(args.results_dir).mkdir(parents=True, exist_ok=True)
    Path(args.results_dir, f"summary_amem_{args.benchmark}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
