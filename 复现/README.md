# 复现 — P4 · 梯队①（多方记忆 benchmark 上跑 BM25 + Mem0）

对应 `CLAUDE.md §10` / `汇报V2 §5.5` 的第一复现梯队：在多方记忆 benchmark 上跑
**BM25** 和 **Mem0** baseline，目的有两个——(1) 验证我们的评测流程能跑通；
(2) 复现 motivation 的关键数字"BM25 ≈ Mem0（~31.7% vs 34.0%），最强系统也只有 46%"。

本目录只放**我们自己的适配代码**；三个 benchmark 的数据由脚本拉取并被 `.gitignore`，
保证以后能干净地 `git pull`。

> 📖 **想先看懂三个数据集长什么样、整条流程怎么走？读 [`数据与流程说明.md`](数据与流程说明.md)**
> （大白话 + 真实样例，分步骤）。
> 📖 **想看 BM25 vs Mem0 同一题的全流程对比 + 指标(EM/F1/judge)怎么算？读 [`BM25-vs-Mem0-全流程实例.md`](BM25-vs-Mem0-全流程实例.md)**。
>
> **Mem0 现已接 `bench_loaders`，三数据集(GroupMem/SocialMem/EverMem)全流程均可跑**（2026-06-09，各单 batch 冒烟通过；`run_mem0.py --benchmark {groupmem,socialmem,evermem}`）。
>
> **A-MEM (agiresearch/A-mem) 已适配复现** ✅（`run_amem.py`，2026-06-09 e2e 通过）：装官方包 + 两处补丁——
> ① openai SDK 自动读 `OPENAI_BASE_URL` 指向 DeepSeek（需强制赋值，.env 里空 `OPENAI_API_KEY=` 会被 setdefault 卡住）；
> ② A-MEM 原用 json_schema 结构化输出，DeepSeek 不支持→monkeypatch 改 `json_object`+调大 max_tokens。
> ⚠️ A-MEM 每条消息 1 次推理 LLM 做笔记构建(~12s/条,串行)→**全量极贵**(SocialMem 7355 条≈24h)，需 `--max-messages` 截断。
>
> **HiPPoRAG (2.0.0a4) 已适配复现 + e2e 通过** ✅(`run_hipporag.py`，2026-06-10，独立 conda env `hippo`)：
> NER→DeepSeek OpenIE 抽三元组→建知识图谱→Contriever 嵌入→Personalized PageRank 检索→QA(1/1 通过)。
> 安装(conda 隔离，不污染主环境)：`conda create -n hippo python=3.10`；`pip install hipporag==2.0.0a4 --no-deps`；
> 补依赖 `torch==2.5.1(cpu) transformers==4.45.2 openai litellm networkx python-igraph tiktoken pydantic tenacity einops gritlm pandas scikit-learn accelerate pyarrow sentence-transformers`(**跳过 vllm**)；
> `run_hipporag.py` 顶部注入 **vllm 桩**(HippoRAG 顶层 import vllm，但我们用 DeepSeek 后端不需要)。
> LLM 走 DeepSeek(`llm_base_url`)；嵌入默认本地 Contriever(CPU)，或用 `embed_server.py`(本地 Qwen 嵌入服务,OpenAI兼容)替换。

## 当前状态（2026-06-09）

| 事项 | 状态 |
|---|---|
| GroupMemBench 数据 | ✅ `setup.sh` 克隆——4 领域 × ~3万消息，**745 题** |
| SocialMemBench 数据 | ✅ `get_socialmembench.py`——43 网络 / 7355 轮 / **1031 题** / 430 人设 |
| EverMemBench 数据 + 代码库 | ✅ `get_evermembench.py` + 克隆——1263 对话块 / **2400 题** / 170 人设 |
| Python 环境（conda py3.11 建 venv） | ✅ 完成（系统 python3 没有 pip） |
| LLM 接入：**DeepSeek（deepseek-v4-flash）** | ✅ 已接 + 离线验证（key 在 `.env`，**未经允许不真实调用**） |
| 备用 LLM 适配器（Anthropic / 本地 vLLM） | ✅ 已写 + 离线单测（`llm_clients.py`） |
| BM25 检索流程（GroupMemBench） | ✅ **已在真实数据上跑通**（`--retrieval-only`，不用 LLM） |
| BM25 完整跑分（QA-agent + judge） | ⏳ 代码就绪，**等你点头才真实调 DeepSeek** |
| Mem0 baseline | 🟡 脚本已搭（`run_mem0.py`），依赖安装中；逻辑未验证 |
| SocialMemBench / EverMemBench 的 loader | ⏳ 待写（数据形态与 GroupMemBench 不同） |

### LLM 接入现状
现在主用 **DeepSeek**（`deepseek-v4-flash`，OpenAI 兼容，base_url `https://api.deepseek.com`），
key 已写入 gitignore 的 `.env`，runner 默认 `--llm-provider deepseek`。
> ⚠️ 按你的要求：**未经你允许，不会发起任何真实 API 调用**。现在能跑的是
> `--retrieval-only`（不调 LLM）。要出真实准确率数字，请明确说"可以跑"。
>
> ⚠️ judge 混淆项：论文用它自己的 gpt-5 judge 评分；我们用 DeepSeek 评分会让绝对数字偏移，
> 但**相对比较**（BM25 vs Mem0，这才是 motivation 要的）只要同一 judge 评两者就成立。
>
> 备用：`--llm-provider anthropic`（需 ANTHROPIC_API_KEY）/ `local`（GPU 到位后本地 vLLM，零费用）。

## 目录结构
```
复现/
├── setup.sh                # 一键：克隆 GroupMemBench + 建 venv + pip 安装
├── requirements.txt
├── .env.example / .env     # 凭据模板 / 真实凭据(gitignore，已填 DeepSeek key)
├── llm_clients.py          # 仿 OpenAI 接口，底层走 DeepSeek / Anthropic / 本地 vLLM
├── bench_loaders.py        # ★ 三个 benchmark 统一 loader（unit/messages/questions）
├── run_baseline.py         # BM25 运行器：--benchmark {groupmem,socialmem,evermem}；仅检索 OR 完整 QA+judge
├── run_mem0.py             # Mem0 baseline（依赖装好、API 对齐 2.0.4、Memory 可构造）
├── run_amem.py             # A-MEM baseline（脚本，需装 A-MEM + 授权调 API）
├── baseline调研-HippoRAG-A-MEM.md  # HippoRAG/A-MEM 可复现性 + 集成方案
├── get_socialmembench.py   # 下载 SocialMemBench 数据 (HF) -> 本地 JSONL
├── get_socialmembench_code.py  # 下载 SocialMemBench 匿名代码库 (zip)
├── get_evermembench.py     # 下载 EverMemBench-Dynamic (HF) -> 本地 JSONL
├── 数据与流程说明.md        # ★ 三个数据集格式 + 评测流程 + 真实样例
├── P4实验进度汇报.md         # 实验进度文档（汇报用）
├── P4实验进度汇报.pptx       # 进度汇报 PPT（gen_p4_ppt.py 生成）
├── gen_p4_ppt.py            # PPT 生成器（python-pptx，套项目调色板；本机无 node 故不用 gen.js）
├── GroupMemBench/          # 克隆的上游代码+数据（.gitignore）
├── SocialMemBench/ + -code/    # 数据 4 表 + 匿名代码库（.gitignore）
├── EverMemBench/ + -Dynamic/   # 上游代码 + 数据 3 表（.gitignore）
├── venv/  results/         # .gitignore
```

## 四个 baseline / 三个 benchmark 状态
| baseline | 检索可跑(无API) | 完整跑分(需授权调API) |
|---|---|---|
| BM25 | ✅ 三个 benchmark 都通 | 代码就绪 |
| Mem0 | —（本身就要LLM入库） | 依赖装好 + API 对齐 2.0.4 + Memory 可构造 |
| A-MEM | — | `run_amem.py` 就绪，待装包+验证 base_url 透传 |
| HippoRAG | — | 集成方案已写（见调研文档），较重 |

三个 benchmark 的 loader 都已写进 `bench_loaders.py` 并接入 `run_baseline.py`（`--benchmark` 切换）。

## 快速开始
```bash
bash setup.sh                                          # 克隆 GroupMemBench + venv + 装依赖
PYTHONPATH=. ./venv/bin/python get_socialmembench.py   # 下载 SocialMemBench
PYTHONPATH=. ./venv/bin/python get_evermembench.py     # 下载 EverMemBench

# (1) 不需要任何 key —— 端到端验证"数据+检索"链路（现在就能跑）：
PYTHONPATH=. ./venv/bin/python run_baseline.py \
    --baseline bm25 --domain all --qtype all --retrieval-only

# (2) 完整 BM25 准确率（DeepSeek 已在 .env 配好）—— ★ 会真实调用 API，需你同意后再跑：
PYTHONPATH=. ./venv/bin/python run_baseline.py \
    --baseline bm25 --domain Finance --qtype multi_hop --limit 20   # 先小规模试跑
```

## 已记录的数字
_每次评分跑完后填到这里。格式：`baseline | judge 模型 | 各类 % | 总体 %`。_

### 仅检索的"标准答案子串 recall@10"（只是 sanity 代理，不是 benchmark 正式指标）
- **GroupMemBench** BM25 全领域：multi_hop 28.2 / knowledge_update 0.0 / term_ambiguity 17.7 /
  user_implicit 42.1 / temporal 0.7 / abstention 不适用 —— 总体 14.8。
- **EverMemBench** BM25：open_ended ~64 / multiple_choice 0（MC 的 gold 是"字母. 文本"，子串测不到）。
- **SocialMemBench** BM25：各类 ~0–4（答案是长文本描述，子串代理对长答**完全不适用**）。

> ⚠️ 子串 recall 只对"短答"（日期/实体/数值）有意义；对长答/多选会严重低估。它只用来证明
> "检索链路通、能把相关消息捞上来"。**三个 benchmark 的真实准确率必须靠 LLM judge 评**（待授权）。

### BM25 —— 代码已升级：按题并行 + 详细指标（2026-06-09）
- `run_baseline.py` 新增 `--workers`（按题并行 QA；检索只读+每题无状态→**并行无损精度**）。
- 详细指标落盘：每类/每单元/总体的 **judge准确率 / EM / token-F1 / 不明率**，加各阶段计时（建索引/检索/agent/judge/墙钟）；逐题记录(verdict/EM/F1/答案)写 `results/<bench>/<unit>/bm25__<cat>.jsonl`。
- 三数据集小批验证(8并发)：GroupMem Finance/multi_hop 8题 acc 62.5%；SocialMem 1网络6题 acc 66.7%；EverMem topic01 8题 acc 75%。不明率均 0%（token/temp 修复稳）。
- ✅ **已升级为全局题级并行**（`run_global_qa`）：建好所有单元索引后，把全部题汇成一个任务池一起并发，解决 SocialMemBench 小组并行收益低的问题。
- 验证(2026-06-09)：SocialMemBench 510 题样本(limit2×43网络) @16并发 **345s** 跑完（串行需~5360s，**16×**）；总体 acc 32.7% / EM 7.1% / F1 18.5% / 不明 0.8%（Q4 群规63.6%最高、Q3聚合5.6%最低）。
- 全量预估@16并发：GroupMem(745)~6min + EverMem(2400)~18min + SocialMem(1031)~12min ≈ 共 ~35min。

### BM25 —— 全量结果（DeepSeek deepseek-v4-flash 做 agent+judge；指标由 compute_metrics.py 重算，含时间戳）
**三数据集 BM25 vs Mem0 全量对比（2026-06-10，metrics_*.json，含时间戳）** —— 详细按类别表见 [`实验结果.md`](实验结果.md)：

| Benchmark | 题数 | BM25 judge acc | Mem0 judge acc | BM25 EM/F1 | 关键发现 |
|---|---|---|---|---|---|
| GroupMemBench | 745 | **44.6%** | **21.6%** | 13.8 / 25.0 | BM25 远超 Mem0(论文同:BM25 43.22>Mem0 25.73) |
| SocialMemBench | 1031 | **28.6%** | **13.7%** | 3.6 / 15.7 | **BM25 完胜 Mem0**；Mem0∈论文 0.12–0.18 |
| EverMemBench | 2400 | **52.5%** | **19.9%** | 4.8 / 9.9 | BM25 远超 Mem0；MC 64%/开放式 27% |

→ **BM25 在三数据集全面碾压 Mem0**（44.6>21.6 / 28.6>13.7 / 52.5>19.9）；详细按类别表见 [`实验结果.md`](实验结果.md)。

SocialMemBench 按类别 BM25/Mem0（acc）：Q4归属 66/11 · Q5 ToM 38/3 · Q7关系 30/9 · Q1单人 25/21 · Q8时间 21/12 · 总体 28.6/13.7（差距最大在归属/ToM/关系——Mem0 有损抽取丢精确归属，正是 speaker-grounded 要补的）。

按类别要点：
- GroupMem：abstention 89.9% / user_implicit 46.9% / multi_hop 41.8% / temporal 41.4% / knowledge_update 23.4% / term_ambiguity 15.1%。
- SocialMem(Q1–Q9)：Q4群规66.2%最高 / Q3聚合4.5%、Q9离群成员10%最低；**归属acc 在此可算**(gold 含人名)，Q5 60.6%/Q7 56%。
- EverMem：multiple_choice 64.4%(4选1,random25%) / open_ended 27.0%（≈论文 oracle 多跳 26%）。

→ 🎯 **motivation 坐实**：GroupMem BM25 44.6% 几乎追平论文最强 46%；SocialMem BM25 28.6% 已**超过**论文里开源记忆系统的 0.12–0.18（judge 换 DeepSeek 故绝对值有偏移，方向一致）。
⚠️ 注：judge/EM/F1 用 DeepSeek 评，与论文 gpt-5 judge 有系统性偏移；多选题 random baseline=25%(EverMem MC)；归属acc 是名字重合启发式。

**指标说明（对齐论文/汇报V2 §6.2）**：
- 主指标：judge准确率(LLM判,主) / EM(严格) / token-F1(部分分) / per-category —— ✅ 全有，`compute_metrics.py` 重算、带时间戳。
- attribution acc(归属准确率)：已实现(名字重合法)，但对这些 benchmark 的 baseline QA 几乎 N/A（gold 多为日期/数值、不含说话人名）→ 它本质是**我们方法的记忆结构**指标。
- cross-speaker leakage / audience adaptation：需说话人级真值标注，公开 benchmark 的 baseline QA 答案无法直接算 → 留给我们方法评估，baseline 阶段不强算（如实说明）。

### （历史）BM25 —— 早期小批 judge 准确率
- **2026-06-09 小试跑**：GroupMemBench / Finance / multi_hop / 20 题 → **35.0% (7/20)**，耗时 ~3 分钟（~40 次调用）。
  与论文 BM25 multi_hop ≈38.2% 量级吻合 → 流程忠实。✅ **QA+judge 全链路确认能出数。**
- 跑这一笔时发现并修了两个"上游为 gpt-5 调参、换 DeepSeek 不合适"的坑（见 `eval_patches.py`）：
  1. **judge/agent token 太小** → DeepSeek 啰嗦的 reasoning 把 `Final:` 行截断 → 误判 "Unclear"（按错算）。
     修复后 Unclear 5→1。已抬高预算（judge≥512 / agent≥1024）。
  2. **temperature=0.2 不可复现**（跑两次逐题结果会抖）→ 已 pin **temperature=0**。
- 全量(745 题)与其它领域/类别：待你授权后跑。

### Mem0 —— 全链路打通 + profiling/优化（2026-06-09）
**全链路确认打通**：消息经 DeepSeek 抽取入库 → 本地 chroma → 检索 → QA → judge → 出分。
但首测 0%(0/48)、~24 分钟。深挖后定位并修复了 4 个问题（`run_mem0.py` / `eval_patches.py`）：

**① 慢的真因 = 192 核致 torch 线程超额订阅（最关键）**
单次 embedding 竟要 **14s**（本地 MiniLM 本应 ~10ms）。本机 192 核，torch 默认用满全部线程 → 容器内疯狂上下文切换。
→ 限制到 8 线程（`OMP_NUM_THREADS` 等 + `torch.set_num_threads`）后：

| 步骤 | 优化前 | 优化后 |
|---|---|---|
| 检索/题 | 14.5s | **0.02s**（↓700×）|
| 入库/批(40条) | 48s | **21.5s** |
| QA agent / judge | 2.0s / 2.6s | 不变 |

**② 入库可复用**：chroma 持久化到 `.mem0_chroma/`，按 `gmb_<域>_<条数>` 建集合；已入库则跳过（省 token）。
修了 `get_all(user_id=)` → 必须 `get_all(filters={"user_id":...})`（之前异常被吞导致每次重灌）。

**③ 关闭 mem0/chromadb 遥测**（`MEM0_TELEMETRY/ANONYMIZED_TELEMETRY=False`，次要）。

**④ 0% 的真因 = deepseek-v4-flash 是推理模型**：它先花 token 推理再出 JSON，mem0 抽取默认 max_tokens(~2000) 不够 →
JSON 被截断（`Error parsing extraction response`）→ 抽出 0 条事实 → 记忆为空 → 0%。
实测把 max_tokens 调到 4000 即 `finish=stop` 正常抽出 5 条事实。已在 `build_mem0` 设 `max_tokens=8000`。
⚠️ 仍待实跑验证（且注意 DeepSeek 用 `"facts"` key、mem0 部分路径读 `"memory"`，下次实跑要盯）。

**结构性成本**：入库每批仍要 1 次 DeepSeek 抽取（推理模型，~50s/批）。但**入库一次即可持久化复用**。

**⑤ 0% 仍未解决的真因（2026-06-09 抽取诊断）= 截断丢事实，非覆盖/非有损设计**：
- Run A（Finance 入库 1000 条/batch=30）：chroma 仅存 **20 条**记忆，multi_hop 等全 0%，仅 abstention 80%（记忆稀疏→多答"查无此信息"恰好对拒答题）。复用验证 ✅（第二次跑自动跳过入库）。
- 诊断前 2 批：**第1批 JSON 在 ~10k 字处被截断→解析失败→该批存 0 条；第2批完整→抽出 30 条详细事实**（含 "48h SLA / July 17 2026 / 负责人" 等正是 multi_hop 要的）。
- 结论：**batch=30 一次抽 ~30 条事实，JSON+推理超 8000 token 被砍断 → 半数批次存 0**。内容/prompt 都没问题。
- **修法（已确认，2026-06-09）：放大输出上限**。单批诊断：`batch=50 + max_tokens=100000` → `finish=stop`、out_tokens≈1.06万、**完整抽出 50 条事实**（8000 装不下才被砍）。已把默认改为 `--ingest-batch 50 / --llm-max-tokens 100000`（均可调）。
  - 代价：每批 ~40-78s（输出大、推理久）；Finance 全量 30k≈600 批，串行≈8-13h。
  - 小实验：Finance 前 1000 条用新设置重灌(干净目录 .mem0_chroma_b50)+20 题，验证 chroma 条数 20→数百、看准确率。

**⑦ 重要纠正：`get_all` 有 20 条硬上限，不是真实存储数**：
- mem0 2.0.4 `get_all(limit=10000)` 仍只返回 20 → 之前"1000条只存20条"是 get_all 分页假象。
- 真实条数看 `vector_store.client.get_collection(name).count()`。截断确实让部分批次丢事实，但存储远不止 20。

**⑧ 并行A档实测（2026-06-09，Finance 1000 条，`--parallel-extract 16`）**：
- 入库 **141s**（并行抽取 115s@16worker + infer=False 直接存 26s）→ 比串行（同量 ~17–30 分钟）**快 ~7–12×**。
- 真实存 **604 条**事实（collection.count），`search` 能检索到同主题事实，链路正常。
- 准确率（每类 5 题）：fact 类全 **0%**、**abstention 100%**、总体 16.7%。
- **0% 的因是覆盖**：604 条都来自前 1000 条（全域 3.3%），而题是从整域抽的→确切答案多在没入库的 96.7% 里。**1000 条规模天然测不出事实题准确率**，只证明"快+抽得全+检索通"。
- → 要 Mem0 真实事实数字必须**按域全量入库（30k）**；并行A档让全量变可行：Finance 30k≈600批÷16≈**35–45 分钟**（串行 8–13h）。

**⑥ 单域内并行入库（提速，损精度）：`--parallel-extract N`**：
- 原理：每批**独立抽取**(existing_memories=[])、互不依赖 → N 线程并发跑慢的抽取调用；抽完用 `infer=False` 直接入库(本地 embed+写，不再调 LLM、不做跨批合并)。
- 提速：抽取 ~8-13h → ÷N（受 DeepSeek 并发/限流约束）。例 `--parallel-extract 16` 全域抽取 ~30-50min。
- 代价：丢跨批去重/知识更新覆盖 → **knowledge_update 受损 + 冗余增多**；factual recall/multi_hop 基本不亏。属"Mem0(无在线合并)变体"，需在论文里标注。
- `--parallel-extract 1`（默认）= 原版串行 additive（保留合并、慢）。
- 每个 GroupMemBench 域独立、QA 只问本域（不跨域）→ 评 Finance 只需入库 Finance 的 30k；4 域可并行（已加 `--persist-dir` 支持按域独立目录并发）。
- 其它：spaCy 未装 → mem0 图/词形功能降级（不影响主流程）；修了 `--limit` 没传进 run() 的 bug。
- **真实 Mem0 数字**：待用 `--max-messages` 适中规模、验证抽取非空后再正式跑（待授权）。
