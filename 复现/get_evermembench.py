#!/usr/bin/env python3
"""下载 EverMemBench-Dynamic 数据集（HF: EverMind-AI/EverMemBench-Dynamic）。

EverMemBench 是本项目要报的第三个多方记忆 benchmark（CLAUDE.md §7：Oracle 多跳约 26%）。
HF 仓库分 3 个配置(config)：
  - dialogues ：多轮群组对话（约 1.26k 行；按 topic/date/Group 组织，每条含 speaker/time/dialogue/message_index）
  - qars      ：问答三元组 Q/A/R（约 2.4k 行；R=参考证据 date+group+message_index；可选 options 多选）
  - profiles  ：人物档案（170 人：姓名/性别/年龄/部门/职位/技能/性格）
总计约 3833 行 / 83MB。对话跨约 250 天，围绕"碳排放会计 + 资产管理平台"项目协作。

用法：
  PYTHONPATH=. ./venv/bin/python get_evermembench.py
输出：
  复现/EverMemBench-Dynamic/{dialogues,qars,profiles}.jsonl  +  meta.json
"""
from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset

HF_REPO = "EverMind-AI/EverMemBench-Dynamic"
CONFIGS = ["dialogues", "qars", "profiles"]
OUT_DIR = Path(__file__).resolve().parent / "EverMemBench-Dynamic"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"hf_repo": HF_REPO, "configs": {}}
    for cfg in CONFIGS:
        print(f"[下载] {HF_REPO} :: {cfg} ...")
        ds = load_dataset(HF_REPO, cfg, split="train")
        out = OUT_DIR / f"{cfg}.jsonl"
        with open(out, "w", encoding="utf-8") as f:
            for row in ds:
                # date 等字段可能是 Timestamp，用 default=str 兜底
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        meta["configs"][cfg] = {"行数": len(ds), "字段": list(ds.features.keys()),
                                "文件": out.name}
        print(f"     -> {out}  共 {len(ds)} 行；字段：{list(ds.features.keys())}")
    (OUT_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[完成] 已写入 {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
