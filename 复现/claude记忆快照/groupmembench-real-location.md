---
name: groupmembench-real-location
description: GroupMemBench 与 SocialMemBench 数据集的真实下载位置（项目自带文档里的 URL 是错的占位符）
metadata: 
  node_type: memory
  type: reference
  originSessionId: ebb81088-a7be-49ea-a3f5-b3aa3a90992c
---

**GroupMemBench**（arXiv 2605.14498，Jingbo Yang / Shiyu Chang 等，UCSB-NLP）真实公开位置：
- **GitHub: https://github.com/UCSB-NLP-Chang/GroupMemBench**（数据直接在仓库里，约 152MB，无需另外下载）
- HF 镜像: https://huggingface.co/datasets/kimperyang/GroupMemBench

⚠️ 项目自带的 `CLAUDE.md` 和 `核心代码实现/evaluation.py` 写的是假 URL `huggingface.co/datasets/GroupMemBench`（无命名空间，404）——别用它，用 UCSB-NLP 这个仓库。

包含内容：4 个领域（Finance/Technology/Healthcare/Manufacturing），每个领域一个约 3 万条消息的对话 JSON（`data/final/<领域>/synthetic_domain_channels_rolevariants_<领域>.json`，按频道名做 key 的字典）。6 类问题 × 4 领域 = 共 **745 题**（`questions/<领域>/<类型>.jsonl`，字段 `id, question, answer, asking_user_id`）。6 类：multi_hop, knowledge_update, term_ambiguity, user_implicit, temporal, abstention。

**公开 baseline 只有 BM25 + text-embedding-3-large。** Mem0/A-MEM/hipporag/memgpt 被提及（summarize 默认值、`build_mem0_llm_config`）但没放出来 → 必须自己重建。两个 baseline 都把检索到的段落喂给 **gpt-5 QA agent + gpt-5 judge**（OpenAI/Azure），走 OpenAI 形态的 `client.chat.completions.create`。见 [[aaai-repro-env]]。

**SocialMemBench**（第二个多方 benchmark，开源系统 0.12–0.18，目标 >0.35）：HF 数据集 **anon4data/socialmembench**（4 配置：networks 43 / personas 430 / conversations 7355 / qa 1031），代码匿名库 **anonymous.4open.science/r/SocialMemBench**（其文件可经 API `…/api/repo/SocialMemBench/files/` 取，网页/raw 会 403/超时）。9 类正式代号 SR/GD/MA/AP/TM/NI/RE/TS/DM（=HF 的 Q1–Q9）。官方评测 `python -m eval.cli --condition <记忆系统> --network <id>`。下载脚本 复现/get_socialmembench.py。

**EverMemBench**（第三个 benchmark，Oracle 多跳约 26%）：代码库 **github.com/EverMind-AI/EverMemBench**（eval/ 框架，四阶段 Add→Search→Answer→Evaluate，被测系统 Memos/Mem0/Memobase/EverMemOS/Zep+llm长上下文，OpenRouter gpt-4.1-mini 答 + gemini 判）；数据 HF **EverMind-AI/EverMemBench-Dynamic**（3 配置：dialogues 1263 / qars 2400 Q-A-R三元组(开放式+多选) / profiles 170，约 83MB，下载注意 date 是 Timestamp 要 default=str）。下载脚本 复现/get_evermembench.py。

注：SocialMemBench / EverMemBench 数据形态都与 GroupMemBench 不同（长表/多选/长答/证据锚点），run_baseline.py 目前只接了 GroupMemBench，另两个的 loader 待写。三数据集详细格式+样例见 复现/数据与流程说明.md。
