#!/usr/bin/env python3
"""下载 SocialMemBench 数据集（HF: anon4data/socialmembench）并导出为本地 JSONL。

SocialMemBench 是本项目要报的第二个多方记忆 benchmark（开源系统只有 0.12–0.18，
目标 >0.35）。HF 仓库分 4 个配置(config)，靠 network_id 关联：
  - networks      ：社交群组（人设/关系/群规），43 行
  - personas      ：人设档案，430 行
  - conversations ：聊天轮次（长表，一行一句），7355 行（348 session）
  - qa            ：问题 + 标准答案 + 证据锚点，1031 行，9 类(Q1–Q9 = SR/GD/MA/AP/TM/NI/RE/TS/DM)

用法：
  PYTHONPATH=. ./venv/bin/python get_socialmembench.py
输出：
  复现/SocialMemBench/{networks,conversations,qa}.jsonl  +  meta.json（字段/规模说明）
"""
from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset

HF_REPO = "anon4data/socialmembench"
CONFIGS = ["networks", "personas", "conversations", "qa"]
OUT_DIR = Path(__file__).resolve().parent / "SocialMemBench"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"hf_repo": HF_REPO, "configs": {}}

    for cfg in CONFIGS:
        print(f"[下载] {HF_REPO} :: {cfg} ...")
        ds = load_dataset(HF_REPO, cfg, split="train")
        out = OUT_DIR / f"{cfg}.jsonl"
        with open(out, "w", encoding="utf-8") as f:
            for row in ds:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        meta["configs"][cfg] = {"行数": len(ds), "字段": list(ds.features.keys()),
                                "文件": str(out.name)}
        print(f"     -> {out}  共 {len(ds)} 行；字段：{list(ds.features.keys())}")

    (OUT_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[完成] 已写入 {OUT_DIR}（含 meta.json）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
