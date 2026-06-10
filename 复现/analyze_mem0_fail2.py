#!/usr/bin/env python3
"""Mem0 失效根因细判：对每个 BM25对/Mem0错 的案例，区分两种根因——
  (A) 抽取丢失：原文事实压根没进 Mem0 库（LLM 摘要时丢了）；
  (B) 检索未命中：事实进了库，但问题 top-k 没把它捞出来。
判定法：
  - 原文出处：SocialMem 用 qa.jsonl 的 evidence_anchors_json(精确 turn_id+说话人) → 按 msg_node 取原始消息；
             GroupMem 无锚点 → 按 gold/关键词在消息里定位。
  - dump 整个 Mem0 集合(绕过 get_all 20 上限, 走 chroma client)，统计压缩比。
  - 关键词覆盖：从 gold+原文锚点取判别性词，扫"全部"记忆有无覆盖。
  - 语义探针：mem.search(gold) top-10，看覆盖锚点的记忆排到第几（问题检索 vs 用答案兜底检索）。
  - 据此分类 (A)/(B)。
用法：PYTHONPATH=. ./venv/bin/python analyze_mem0_fail2.py
"""
from __future__ import annotations
import os, sys, json, glob, re
for _v in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"): os.environ.setdefault(_v,"8")
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/"GroupMemBench"))
from baselines.rag_common.eval_lib import load_env_file, format_retrieved_message
load_env_file(str(HERE/".env"))
from bench_loaders import iter_units
from run_baseline import build_bm25_retriever
from run_mem0 import build_mem0

STOP = set("the a an and or of to in on for with that this is are was were be been has have had "
           "who what when where why how does do did will would should could about their her his "
           "they she he it its as at by from into than then them you your our we i me my not no "
           "but if so up out over under more most some any each which whom whose said say says "
           "person group member people one two three first last also only just very can may".split())

def keywords(text, n=12):
    toks = [t for t in re.findall(r"[a-zA-Z][a-zA-Z'\-]+", (text or "").lower()) if len(t) > 3 and t not in STOP]
    seen, out = set(), []
    for t in toks:
        if t not in seen: seen.add(t); out.append(t)
    return out[:n]

# ---- SocialMem evidence anchors + raw messages ----
def load_social_anchors():
    qa = {}
    for line in open(HERE/"SocialMemBench/qa.jsonl"):
        d = json.loads(line)
        anchors = json.loads(d.get("evidence_anchors_json") or "[]")
        qa[d["qa_id"]] = {"net": d["network_id"], "anchors": anchors,
                          "foil": d.get("contamination_foil",""), "qtype": d.get("query_type")}
    return qa

CASES = [
    ("socialmem","grp_2b3c4d5e","Q4_n2e5f6a7","Q4 归属(谁反对圣诞日期)"),
    ("socialmem","grp_3c4d5e6f","Q5_r3e5f6a7","Q5 ToM(Cass素食,谁知道)"),
    ("socialmem","grp_1a2b3c4d","Q7_a7b8c9d0","Q7 关系(Priya-Lena)"),
    ("socialmem","grp_1a2b3c4d","Q8_c9d0e1f2","Q8 时间漂移"),
    ("groupmem","Finance","temporal_7","时序(截止日2025-07-18)"),
]

_cache = {}
def get_unit(bench, unit):
    if (bench,unit) in _cache: return _cache[(bench,unit)]
    msgs=qs=None
    for u,m,q in iter_units(bench,HERE,unit):
        if str(u)==unit: msgs,qs=m,q; break
    bm25 = build_bm25_retriever(msgs)
    safe = re.sub(r"[^a-zA-Z0-9._-]","-",unit)
    coll = f"{bench}__{safe}__m{len(msgs)}"
    mem = build_mem0("deepseek","deepseek-v4-flash","all-MiniLM-L6-v2",
                     collection=coll, persist_path=str(HERE/".mem0_chroma"/bench))
    # dump 全部记忆（mem0/chroma 把记忆文本存在 metadata["data"]，documents 为空！）
    allmem=[]
    try:
        cl = mem.vector_store.client
        c = cl.get_collection(coll)
        got = c.get(include=["documents","metadatas"], limit=100000)
        docs = got.get("documents") or []
        metas = got.get("metadatas") or []
        for i in range(len(got.get("ids",[]))):
            t = (docs[i] if i < len(docs) and docs[i] else "") or (metas[i].get("data","") if i < len(metas) else "")
            allmem.append(t)
    except Exception as e:
        allmem=[]
    _cache[(bench,unit)] = (msgs,{x["id"]:x for x in qs},bm25,mem,coll,allmem,len(msgs))
    return _cache[(bench,unit)]

def res_answer(bench,unit,qid):
    out={}
    for base in ("bm25","mem0"):
        for f in glob.glob(f"results/{bench}/{unit}/{base}__*.jsonl"):
            for l in open(f):
                r=json.loads(l)
                if r.get("id")==qid: out[base]={"ans":r.get("agent_answer",""),"v":r.get("verdict","")}
    return out

def main():
    social = load_social_anchors()
    for bench,unit,qid,tag in CASES:
        msgs,qmap,bm25,mem,coll,allmem,nmsg = get_unit(bench,unit)
        q = qmap.get(qid)
        if not q: print(f"\n[{qid}] 未找到"); continue
        r = res_answer(bench,unit,qid)
        print("\n"+"="*96)
        print(f"#### 【{tag}】 {bench}/{unit}/{qid}")
        print(f"问题: {q['question'][:160]}")
        print(f"标准答案: {q.get('answer','')[:240]}")
        print(f"BM25[{r.get('bm25',{}).get('v','?')}]: {r.get('bm25',{}).get('ans','')[:140]}")
        print(f"Mem0[{r.get('mem0',{}).get('v','?')}]: {r.get('mem0',{}).get('ans','')[:140]}")

        # 1) 原文出处
        anchor_msgs=[]
        if bench=="socialmem" and qid in social:
            anchor_turns={a.get("turn_id") for a in social[qid]["anchors"]}
            anchor_msgs=[m for m in msgs if m.get("msg_node") in anchor_turns]
            print(f"\n  ★ 原文出处(evidence_anchors, {len(anchor_turns)} 锚点, foil={social[qid]['foil'] or '无'}):")
        else:
            # GroupMem: 用 gold 关键词在消息里找
            kw=set(keywords(q.get('answer','')+" "+q['question'],15))
            scored=sorted(msgs,key=lambda m:-len(kw & set(keywords(m.get('content',''),40))))
            anchor_msgs=scored[:2]
            print(f"\n  ★ 原文出处(按 gold 关键词定位 top2):")
        for m in anchor_msgs[:4]:
            print("    | "+format_retrieved_message(m).replace("\n"," ")[:200])

        # 锚点判别词(用于扫库) + 字面量(日期/数字/专有名词)
        akw=set()
        for m in anchor_msgs: akw|=set(keywords(m.get('content',''),20))
        akw|=set(keywords(q.get('answer',''),12))
        # 字面量：日期、纯数字、首字母大写的专有名词(人名/工件名)
        lit=set(re.findall(r"\d{4}-\d{2}-\d{2}|\b\d{2,}\b", q.get('answer','')))
        for m in anchor_msgs: lit|=set(re.findall(r"\d{4}-\d{2}-\d{2}|\b\d{2,}\b", m.get('content','')))
        names=set(re.findall(r"\b[A-Z][a-z]{2,}\b", (q.get('answer','')+" "+" ".join(m.get('content','') for m in anchor_msgs))))
        names-= {"The","Does","Session","Cafe"}

        # 2) Mem0 库压缩比 + 是否覆盖锚点(抽取检查)
        print(f"\n  ▶ Mem0 库: {nmsg} 条消息 → {len(allmem)} 条记忆 (压缩 {(1-len(allmem)/max(nmsg,1))*100:.0f}%)")
        def covers(d):
            dl=d.lower()
            kw_ov=akw & set(keywords(d,60))
            lit_ov={x for x in lit if x in d}
            return len(kw_ov)>=2 or len(lit_ov)>=1, kw_ov, lit_ov
        covered=[]
        for d in allmem:
            ok,kw_ov,lit_ov=covers(d)
            if ok: covered.append((len(kw_ov)+len(lit_ov),d,kw_ov|lit_ov))
        covered.sort(reverse=True)
        if covered:
            print(f"  ▶ 全库中覆盖锚点(关键词≥2 或 命中字面量)的记忆: {len(covered)}/{len(allmem)} 条；最佳:")
            for ov,d,k in covered[:2]: print(f"      [{sorted(k)[:6]}] {d[:160]}")
        else:
            print(f"  ▶ 全库 {len(allmem)} 条记忆中【没有】任何条覆盖锚点(判别词 {sorted(akw)[:6]} / 字面量 {sorted(lit)[:4]}{sorted(names)[:4]}) → 抽取阶段已丢")

        # 3) 检索探针: 问题 top-5 vs 用 gold 兜底 top-10
        def search(qy,k):
            try: return [h.get("memory","") for h in mem.search(qy,top_k=k,filters={"user_id":unit}).get("results",[])]
            except Exception: return []
        q_hits=search(q['question'],5)
        g_hits=search(q.get('answer','')[:300],10)
        print(f"  ▶ Mem0 用【问题】检索到的 top-3 记忆(answerer 实际所见):")
        for h in q_hits[:3]: print(f"      · {h[:150]}")
        def rank_cover(hits):
            for i,h in enumerate(hits,1):
                if covers(h)[0]: return i
            return None
        rq=rank_cover(q_hits); rg=rank_cover(g_hits)
        print(f"  ▶ 命中覆盖记忆排名: 问题 top-5 @{rq or '无'};  用 gold 答案兜底 top-10 @{rg or '无'}")

        # 4) 根因判定
        if not covered:
            verdict="(A) 抽取丢失——全库无任何记忆含该事实(LLM 摘要时丢了)"
        elif rq is None and rg is not None:
            verdict="(B) 检索未命中——事实在库@%s，但问题 top-k 没捞到(用答案兜底才命中@%s)"%(covered and '库内' or '?', rg)
        elif rq is not None:
            verdict="(C) 已检索到却答错——记忆在 top-k 内但归属/聚合/推理失败"
        else:
            verdict="(B') 检索未命中——库内有但问题/答案检索都没排进前列"
        print(f"  ✦ 根因: {verdict}")

if __name__ == "__main__":
    main()
