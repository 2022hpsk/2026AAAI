#!/usr/bin/env python3
"""Mem0 失效归因：对 BM25对/Mem0错 的案例，重建两边的检索内容做对照。
- BM25：本地 rank_bm25 检索原始消息(免费)。
- Mem0：连持久化 chroma，mem.search 取已入库记忆(只本地 embed 查询，免费、不调 LLM)。
- 答案：从 results/*.jsonl 读各自 agent_answer + verdict。
用法：./venv/bin/python analyze_mem0_fail.py
"""
from __future__ import annotations
import os, sys, json, glob, re
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "8")
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "GroupMemBench"))
from baselines.rag_common.eval_lib import load_env_file
load_env_file(str(HERE / ".env"))
from bench_loaders import iter_units
from run_baseline import build_bm25_retriever
from baselines.rag_common.eval_lib import format_retrieved_message
from run_mem0 import build_mem0

# 要剖析的代表案例：(bench, unit, qid, 标签)
CASES = [
    ("groupmem", "Finance", "temporal_7",         "时序(谁最先/最后说X)"),
    ("groupmem", "Finance", "multi_hop_35",       "多跳(A提的→B负责的→…)"),
    ("groupmem", "Finance", "user_implicit_4",    "隐式指代(我/我们)"),
    ("groupmem", "Finance", "knowledge_update_30","知识更新(旧值被覆盖)"),
    ("socialmem", "grp_2b3c4d5e", "Q4_n2e5f6a7",  "Q4 归属探针(谁说了X)"),
    ("socialmem", "grp_3c4d5e6f", "Q5_r3e5f6a7",  "Q5 ToM 心理揣测"),
    ("socialmem", "grp_1a2b3c4d", "Q7_a7b8c9d0",  "Q7 关系边(谁和谁)"),
    ("evermem",  "01", "F_SH_Top01_026",          "open_ended 精确事实"),
]

def load_results(bench, unit, qid):
    """从 bm25__*/mem0__* jsonl 找该 qid 的 agent_answer+verdict。"""
    out = {}
    for base in ("bm25", "mem0"):
        for f in glob.glob(f"results/{bench}/{unit}/{base}__*.jsonl"):
            for line in open(f):
                r = json.loads(line)
                if r.get("id") == qid:
                    out[base] = {"ans": r.get("agent_answer", ""), "verdict": r.get("verdict", "")}
                    break
    return out

# 按 unit 缓存(每个 unit 只构建一次 bm25/mem0)
_cache = {}
def get_unit(bench, unit):
    key = (bench, unit)
    if key in _cache:
        return _cache[key]
    msgs = qs = None
    for u, m, q in iter_units(bench, HERE, unit):
        if str(u) == unit:
            msgs, qs = m, q; break
    bm25 = build_bm25_retriever(msgs)
    safe = re.sub(r"[^a-zA-Z0-9._-]", "-", unit)
    coll = f"{bench}__{safe}__m{len(msgs)}"
    persist = str(HERE / ".mem0_chroma" / bench)
    mem = build_mem0("deepseek", "deepseek-v4-flash", "all-MiniLM-L6-v2",
                     collection=coll, persist_path=persist)
    _cache[key] = (msgs, {x["id"]: x for x in qs}, bm25, mem, unit)
    return _cache[key]

def main():
    for bench, unit, qid, tag in CASES:
        try:
            msgs, qmap, bm25, mem, u = get_unit(bench, unit)
        except Exception as e:
            print(f"\n#### [{bench}/{unit}/{qid}] 加载失败: {e}"); continue
        q = qmap.get(qid)
        if not q:
            print(f"\n#### [{bench}/{unit}/{qid}] 题目未找到"); continue
        res = load_results(bench, unit, qid)
        print("\n" + "=" * 92)
        print(f"#### 【{tag}】 {bench}/{unit}/{qid}")
        print(f"问题: {q['question']}")
        print(f"标准答案: {q.get('answer','')}")
        b = res.get("bm25", {}); m = res.get("mem0", {})
        print(f"BM25 答案[{b.get('verdict','?')}]: {b.get('ans','')[:200]}")
        print(f"Mem0 答案[{m.get('verdict','?')}]: {m.get('ans','')[:200]}")
        # BM25 检索
        print("\n  -- BM25 检索到的原始消息 top5 --")
        idxs = bm25(q["question"], 5)
        for i in idxs:
            if 0 <= i < len(msgs):
                print("   • " + format_retrieved_message(msgs[i]).replace("\n", " ")[:170])
        # Mem0 检索
        print("  -- Mem0 检索到的记忆 top5 --")
        try:
            hits = mem.search(q["question"], top_k=5, filters={"user_id": unit}).get("results", [])
            if not hits:
                print("   (无命中)")
            for h in hits:
                print(f"   • [{h.get('score',0):.2f}] " + str(h.get("memory", ""))[:170])
        except Exception as e:
            print(f"   (Mem0 search 失败: {e})")

if __name__ == "__main__":
    main()
