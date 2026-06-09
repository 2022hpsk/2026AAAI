---
name: aaai-repro-env
description: SpeakerMem-R1 实验机环境（python/pip/GPU/LLM 约束）与 复现/ 脚手架现状
metadata: 
  node_type: memory
  type: project
  originSessionId: ebb81088-a7be-49ea-a3f5-b3aa3a90992c
---

AAAI SpeakerMem-R1 项目的实验机（cwd `/home/jovyan/haobo_AAAI`；仓库克隆在 `/home/jovyan/haobo_AAAI/2026AAAI`，公开于 github.com/2022hpsk/2026AAAI）。

环境约束：
- **系统 `python3`(3.10) 没有 pip/ensurepip。** 用 **`/opt/conda/bin/python`(3.11, 有 pip)**。复现的 venv 就是用它建的。
- **暂无 GPU**（`nvidia-smi` 不存在）——用户在申请。GPU 给 P5 训练用；P4 baseline 只需 LLM 做 QA-agent + judge。
- **LLM 接入 = DeepSeek**（`deepseek-v4-flash`，OpenAI 兼容，base_url `https://api.deepseek.com`）。key 在 `复现/.env`（gitignore）。⚠️ 用户给的 key 明文出现在聊天里，建议提醒轮换。
- ⚠️ **没有用户明确允许，不要发起真实 API 调用**（用户硬性要求）。能跑的零成本验证是 `run_baseline.py --retrieval-only`（不调 LLM）。
- 旧坑：`ANTHROPIC_BASE_URL=https://api.anthropic.com` 是 Claude Code 的 OAuth 端点，不能拿来批量调用（直接调 401）。

P4 梯队① 脚手架在 **`2026AAAI/复现/`**（只放自己代码；数据/venv/results 都 gitignore，用 setup.sh + get_*.py 重建）：
- `llm_clients.py` — 仿 OpenAI 接口，底层 deepseek / anthropic / 本地vLLM（离线单测过）。
- `run_baseline.py` — BM25；`--retrieval-only` 已验证；**完整 QA+judge 走 DeepSeek 已真实跑通**(Finance/multi_hop 20题=35%, 与论文≈38.2%吻合)。`eval_patches.py` 抬高 token 预算+pin temperature=0(上游为gpt-5调的256/512会截断DeepSeek的Final行→误判Unclear；temp0.2不可复现)。
- `run_mem0.py` — Mem0 baseline（依赖已装：mem0ai 2.0.4 / sentence-transformers 5.5.1 / chromadb 1.5.9 / torch 2.12 CPU）。**已对齐 2.0.4 API**：search(query, top_k=, filters={"user_id":..})→{"results":[{memory,score}]}；Memory.from_config 实测可构造(HuggingFaceEmbedding+OpenAILLM未调用+ChromaDB)，源码确认 __init__ 不发请求。Mem0=开源框架本地跑，但 add(infer=True) 事实抽取调 LLM(指 DeepSeek)；embedding/向量库本地免费。**已真实跑通**(Finance入库120条/48题, base_url指DeepSeek无401)；但 Mem0 很贵很慢(每批入库都调LLM抽取+更新, 120条+48题≈24分钟)，真实数字需全量入库(30k条)后再跑。
- `bench_loaders.py` — 三 benchmark 统一 loader(unit/messages/questions)，已接入 run_baseline 的 `--benchmark {groupmem,socialmem,evermem}`；三者 retrieval-only 都跑通。注：子串 recall 只对短答有意义，长答/多选会低估，真实分要 LLM judge。
- `run_amem.py` + `baseline调研-HippoRAG-A-MEM.md` — A-MEM(agiresearch/A-mem, 与Mem0同构)adapter 就绪待装包；HippoRAG(OSU-NLP, 重, KG+PageRank+OpenIE)给了集成方案。两者实跑需装包+调API。
- `数据与流程说明.md` = 三数据集格式+评测流程+真实样例的中文详解。
- SocialMemBench 代码：逐目录 API 会 401，用整库 zip 端点 /api/repo/SocialMemBench/zip 下载(get_socialmembench_code.py)。
