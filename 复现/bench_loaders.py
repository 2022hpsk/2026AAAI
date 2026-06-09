"""三个多方记忆 benchmark 的统一 loader。

把 GroupMemBench / SocialMemBench / EverMemBench 各自的原始格式，统一成 run_baseline.py
能直接用的两样东西：
  - messages：list[dict]，每条至少有 content（用于 BM25 索引）+ author/_channel/timestamp/
              msg_node 等（用于拼成展示给 LLM 的段落，复用 eval_lib.format_retrieved_message）。
  - questions：list[dict]，每条有 id/question/answer/asking_user_id/category。
              多选题会把选项拼进 question，gold 用"字母. 文本"形式，方便 judge 比对。

每个 benchmark 按"单元"(unit)切分（GroupMemBench=领域；SocialMemBench=network；
EverMemBench=topic），每个单元单独建 BM25 索引、各自检索（不跨单元串台）。

接口：iter_units(benchmark, here, unit_filter="all") -> 迭代 (unit名, messages, questions)
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

# 复用上游 GroupMemBench 的对话/问题加载器
import sys


def _gmb_helpers(here: Path):
    repo = here / "GroupMemBench"
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from baselines.rag_common.eval_lib import load_conversation_messages, load_questions
    return load_conversation_messages, load_questions, repo


def _read_jsonl(path: Path) -> List[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _clean(s: Any) -> str:
    return html.unescape(s).strip() if isinstance(s, str) else ""


# --------------------------------------------------------------------------- #
# GroupMemBench：领域 = 单元（沿用上游格式）
# --------------------------------------------------------------------------- #
GMB_DOMAINS = ["Finance", "Technology", "Healthcare", "Manufacturing"]
GMB_QTYPES = ["multi_hop", "knowledge_update", "term_ambiguity",
              "user_implicit", "temporal", "abstention"]


def iter_groupmem(here: Path, unit_filter: str = "all") -> Iterator[Tuple[str, List[dict], List[dict]]]:
    load_conv, load_q, repo = _gmb_helpers(here)
    domains = GMB_DOMAINS if unit_filter == "all" else [unit_filter]
    for dom in domains:
        cp = repo / "data/final" / dom / f"synthetic_domain_channels_rolevariants_{dom}.json"
        if not cp.exists():
            continue
        messages = load_conv(str(cp))
        questions: List[dict] = []
        for qt in GMB_QTYPES:
            qp = repo / "questions" / dom / f"{qt}.jsonl"
            if not qp.exists():
                continue
            for q in load_q(str(qp)):
                questions.append({"id": q.get("id", ""), "question": q["question"],
                                  "answer": q.get("answer", ""),
                                  "asking_user_id": q.get("asking_user_id", ""),
                                  "category": qt})
        yield dom, messages, questions


# --------------------------------------------------------------------------- #
# SocialMemBench：network = 单元
# --------------------------------------------------------------------------- #
def _mc_question(question: str, options: Dict[str, str]) -> str:
    """把多选选项拼进问题文本。"""
    if not options:
        return question
    lines = [f"{k}. {v}" for k, v in options.items()]
    return f"{question}\n\nOptions:\n" + "\n".join(lines)


def iter_socialmem(here: Path, unit_filter: str = "all") -> Iterator[Tuple[str, List[dict], List[dict]]]:
    base = here / "SocialMemBench"
    convs = _read_jsonl(base / "conversations.jsonl")
    qas = _read_jsonl(base / "qa.jsonl")

    # 按 network 分组消息
    by_net_msg: Dict[str, List[dict]] = {}
    for c in convs:
        m = {"content": _clean(c.get("message", "")),
             "author": c.get("speaker_display_name", "?"),
             "_channel": c.get("session_id", ""),
             "topic": c.get("session_topic", ""),
             "timestamp": str(c.get("timestamp", "")),
             "reply_to": c.get("reply_to_turn_id", ""),
             "msg_node": c.get("turn_id", "")}
        by_net_msg.setdefault(c.get("network_id", ""), []).append(m)
    for msgs in by_net_msg.values():
        msgs.sort(key=lambda x: (x["_channel"], x["timestamp"], x["msg_node"]))

    # 按 network 分组问题
    by_net_q: Dict[str, List[dict]] = {}
    for q in qas:
        opts = {}
        oj = q.get("options_json")
        if oj and oj not in ("[]", ""):
            try:
                parsed = json.loads(oj)
                if isinstance(parsed, dict):
                    opts = parsed
            except Exception:  # noqa
                opts = {}
        gold = q.get("answer", "")
        if opts and q.get("correct_option"):  # 多选：gold 用"字母. 文本"
            letter = q["correct_option"]
            gold = f"{letter}. {opts.get(letter, gold)}"
        by_net_q.setdefault(q.get("network_id", ""), []).append({
            "id": q.get("qa_id", ""),
            "question": _mc_question(q["question"], opts),
            "answer": gold,
            "asking_user_id": "",   # SocialMemBench 无 asker 绑定
            "category": q.get("query_type", "unknown")})

    nets = sorted(by_net_msg) if unit_filter == "all" else [unit_filter]
    for net in nets:
        if net in by_net_msg and net in by_net_q:
            yield net, by_net_msg[net], by_net_q[net]


# --------------------------------------------------------------------------- #
# EverMemBench：topic = 单元
# --------------------------------------------------------------------------- #
def iter_evermem(here: Path, unit_filter: str = "all") -> Iterator[Tuple[str, List[dict], List[dict]]]:
    base = here / "EverMemBench-Dynamic"
    dials = _read_jsonl(base / "dialogues.jsonl")
    qars = _read_jsonl(base / "qars.jsonl")

    # dialogues：一行 = 某 topic 某天的 {Group: [msgs]}；按 topic 聚合
    by_topic_msg: Dict[str, List[dict]] = {}
    for row in dials:
        tid = str(row.get("topic_id", ""))
        date = str(row.get("date", ""))
        groups = row.get("dialogues", {}) or {}
        if not isinstance(groups, dict):
            continue
        for gname, msgs in groups.items():
            if not isinstance(msgs, list):
                continue
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                by_topic_msg.setdefault(tid, []).append({
                    "content": _clean(m.get("dialogue", "")),
                    "author": m.get("speaker", "?"),
                    "_channel": gname,
                    "timestamp": str(m.get("time", "")),
                    "msg_node": f"{date}|{gname}|{m.get('message_index', '')}"})
    for msgs in by_topic_msg.values():
        msgs.sort(key=lambda x: (x["timestamp"], x["_channel"], x["msg_node"]))

    by_topic_q: Dict[str, List[dict]] = {}
    for q in qars:
        tid = str(q.get("topic_id", ""))
        opts = q.get("options") if isinstance(q.get("options"), dict) else {}
        gold = q.get("A", "")
        if opts and isinstance(gold, str) and gold in opts:  # 多选：gold 用"字母. 文本"
            gold = f"{gold}. {opts[gold]}"
        by_topic_q.setdefault(tid, []).append({
            "id": q.get("id", ""),
            "question": _mc_question(q.get("Q", ""), opts),
            "answer": gold,
            "asking_user_id": "",
            "category": ("multiple_choice" if opts else "open_ended")})

    topics = sorted(by_topic_msg) if unit_filter == "all" else [unit_filter]
    for tid in topics:
        if tid in by_topic_msg and tid in by_topic_q:
            yield tid, by_topic_msg[tid], by_topic_q[tid]


LOADERS = {"groupmem": iter_groupmem, "socialmem": iter_socialmem, "evermem": iter_evermem}


def iter_units(benchmark: str, here: Path, unit_filter: str = "all"):
    if benchmark not in LOADERS:
        raise ValueError(f"未知 benchmark: {benchmark}。可用：{list(LOADERS)}")
    return LOADERS[benchmark](here, unit_filter)
