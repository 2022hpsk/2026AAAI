#!/usr/bin/env bash
# GroupMemBench 复现的一键环境搭建（P4 · 梯队①）。
# - 克隆上游 benchmark（数据就在仓库里，约 152MB）
# - 用 conda 的 python 建 venv（系统 python3 没有 pip）
# - 安装 BM25 路线的依赖
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-/opt/conda/bin/python}

if [ ! -d GroupMemBench ]; then
  echo "[setup] 正在克隆 UCSB-NLP-Chang/GroupMemBench ..."
  git clone --depth 1 https://github.com/UCSB-NLP-Chang/GroupMemBench.git
else
  echo "[setup] GroupMemBench/ 已存在，跳过克隆"
fi

if [ ! -d venv ]; then
  echo "[setup] 用 $PY 创建 venv ..."
  "$PY" -m venv venv
fi

echo "[setup] 安装依赖 ..."
./venv/bin/pip install -q --disable-pip-version-check -r requirements.txt

echo "[setup] 完成。冒烟测试（不用 LLM）："
echo "  PYTHONPATH=. ./venv/bin/python run_baseline.py --baseline bm25 --domain all --qtype all --retrieval-only"
