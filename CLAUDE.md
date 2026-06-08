# CLAUDE.md — 项目圣经 / 新会话记忆引导

> **任何新 Claude Code 会话（含远程 SSH）先完整读本文件**，再按需展开读 `汇报V2-问题导向文档.md`、`SpeakerMem-R1-v2-方法spec.md`、`项目概览-SpeakerMem-R1.md`。读完本文件即可"继承记忆"、接着干。
> 最近更新：2026-06-03。

---

## 0. 项目一句话

**SpeakerMem-R1** = **首个面向多方对话（3+ 人 / 群聊）的 speaker-grounded 强化学习记忆管理框架**。目标会议 AAAI（投稿期约 2027）。
**核心能力**：在多角色对话里**精准区分"谁说了什么"**——把不同说话人的事实/观点/答案分清，按**正确的人 / 时间 / 受众**归属并作答。
**研究空白（卖点）**：现有 RL 记忆方法全是 **dyadic（一对一）**；现有多方记忆工作全是 **training-free / 仅评测**。"多方 + 说话人锚定 + RL 训练"截至 2026/6 **零篇先例**。

---

## 1. 问题与动机（为什么做这个）

- **真实刚需**：企业群聊（Slack/飞书/Teams）、在线教育（一师多生）、医疗多学科会诊、客服/合规、multi-agent 协作。
- **现有系统集体失败（硬数据）**：
  - SocialMemBench：开源记忆系统（Mem0/LangMem/Graphiti/Cognee）多方场景仅 **0.12–0.18**（≈没有记忆）；目标 >0.35。
  - GroupMemBench：最强系统仅 **46%**，连 **BM25** 都能追平 → 瓶颈是**结构性缺陷**（没把信息归属到说话人），不是模型不够聪明。
  - EverMemBench：Oracle 多跳归因仅 **~26%**。
- **三个 speaker-blind 结构缺陷**（dyadic 中不存在、多方才有，调参解决不了）：① Action space 缺 speaker_id；② Reward 不分说话人（整体内容对、归属错仍高分）；③ Credit assignment 不按说话人（不同 rollout 说话人分布不同、奖励不可比）。

---

## 2. 方法（SpeakerMem-R1，"怎么做"是次要的，问题导向优先）

**三大技术贡献**（分别修上面三个盲区）：
1. **SpeakerLevenshtein 奖励** — 按说话人分桶的稠密过程奖励，区分"归属错"vs"事实错"，含 worst-speaker bonus（扩展 DeltaMem 的 flat Levenshtein）。
2. **Speaker-Conditioned LoGo-GRPO** — local rerollout 按 active speaker set 分层，保证组内"相同说话人分布"才可比（扩展 Memory-R2 的 LoGo）。
3. **5 层 Speaker-Indexed Memory** — per-speaker(core/episodic/profile) + group(interaction/insight)，对应 SocialMemBench 5 类失败模式。

**系统数据流（推理时，一个模型扮三角色）**：
`对话流 C(带说话人标签) → [A_mem 写记忆，逐轮在线] → M(5层,按说话人分桶) → [A_ret 检索，按"提问者可见+相关"] → [A_ans 回答，适配提问者] → 答案 a`

**完整奖励**：`R = 0.5·R_task + 0.8·R_state(主导,稠密,按说话人) + 0.3·R_attr + 0.2·R_aud + 0.1·R_compr + 0.1·R_RIF − 0.3·R_leak(跨说话人泄漏)`

**三阶段训练**：Stage1 SFT 热启动(role-masked, attribution F1>50%) → Stage2 Joint RL(SpeakerMem-GRPO, 二维课程 K=3→5→8 × session 8→16→32) → Stage3 端到端(三 benchmark 混合)。

> 细节见 `SpeakerMem-R1-v2-方法spec.md`（可实现级，含公式/超参）和 `具体实验细节文档.md`（逐步 I/O + 多角色示例）。

---

## 3. 从 0 到投稿的全流程（项目生命周期 + 进度标记）

| 阶段 | 内容 | 状态 |
|----|----|----|
| **P0 选题 + 文献调研** | 30+ 篇精读、确认零篇空白 | ✅ 完成（`*/详解.md`、`深度调研.md`、`调研.md`、`迭代V*`） |
| **P1 方法设计** | 三大贡献 + 5 层记忆 + 奖励 + 三阶段训练 | ✅ 完成（`SpeakerMem-R1-v2-方法spec.md`） |
| **P2 论文骨架** | 7 章草稿 + BibTeX + 写作指南 | ✅ 完成（`论文草稿-*.md`，数字为占位符） |
| **P3 代码框架** | 6 模块，dry-run/mock 通过 | ✅ 完成（`核心代码实现/`，**未真实训练**） |
| **P4 复现 baseline + 合成数据** | Mem0/BM25 跑通、合成 200 条训练数据、Stage1 SFT | 🔜 **现在开始（你在这里）** |
| **P5 核心训练实验** | Stage2 Joint RL → Stage3 端到端（~4×A100） | ⏳ 未开始 |
| **P6 主实验 + 消融** | 三多方 benchmark + LoCoMo 兼容性 + Top-3 消融 | ⏳ 未开始 |
| **P7 回填数字 + 写作 + 投稿** | 填实验数字 → arXiv preprint → 投 AAAI | ⏳ 未开始 |

**实验内部 pipeline（P4→P6 真正跑起来后的数据流）**：
`合成数据(对话+GT memory+QA标注) → Stage1 SFT → Stage2 RL(rollout G=4 → 完整奖励打分 → group-relative advantage → GRPO + SC-LoGo 局部分支) → Stage3 端到端 → 评测(EM/F1/attribution acc/per-category/leakage/LoCoMo) → 消融`

---

## 4. 现在进行到哪里（当前状态，重要）

- ✅ **纸面准备全部就位**：调研 + 方法 + 7 章论文 + 6 模块代码（dry-run 通过）。
- ❌ **唯一硬缺口：真实实验一项没跑**（无训练数据、无算力投入）；论文里所有实验数字是占位符。这是距"强提交/Highlight"的唯一差距（自评：Novelty 9 / Significance 8.5 / **Soundness 6–7** / Clarity 8.5 / 综合 ~7.4–7.75）。
- 🔜 **当前任务：进入 P4，开始复现**。优先做"梯队①"（见 §6）。
- 🌐 **环境迁移中**：实验将在用户的**远程 SSH 机器**上做（GPU/数据在那边）。本仓库已 push 到 `github.com/2022hpsk/2026AAAI`，远程 `git clone/pull` 即可同步全部上下文。

---

## 5. 之前做了什么 + 有什么缺漏

**已完成产出**：
- 文献：33 个 `详解.md`（每篇相关工作/ benchmark 的中文精读，含"对本研究的借鉴与 delta"）。
- 方法：可实现级 spec、奖励公式、5 层记忆、3 阶段训练、二维课程。
- 论文：7 章草稿（Abstract-Intro / RelatedWork / Method / Experiments / Conclusion / Appendix）+ 31 条 BibTeX + AAAI 写作指南。
- 代码：6 模块（见 §8），dry-run/mock 通过。
- 数据方案：图驱动合成 pipeline 设计（`数据合成Pipeline设计.md`、`迭代V3-benchmark数据与训练数据方案.md`）。
- 汇报：进度汇报、问题导向 V2 文档 + PPT、具体实验细节文档。

**缺漏 / 风险（必须正视）**：
1. **实验全未跑**（最大缺口）——下一步全部围绕补这个。
2. **三个多方 benchmark 都无训练集** → 训练数据须**完全合成**（质量能否撑 RL 是未知数，必要时人工标注种子兜底）。
3. **竞品 DeltaMem / Memory-R2 / CoMAM / TreeMem 均无公开代码** → baseline 须自实现（但 reviewer 也更难质疑）。
4. **算力/经费待确认**（估算 4×A100 + ~$1,100 训练 + ~$50–100 数据 API）。
5. **AAAI CFP 截止年份需官方核实**（早期文档有一处把年份记混）——直接决定是否冲刺。
6. base model 未最终定：Qwen3-8B（对齐 DeltaMem）vs Qwen2.5-7B。

---

## 6. 未来规划

### 6.1 复现优先级（来自 `汇报V2-问题导向文档.md` §5.5；判断原则：必报 baseline + 有无开源代码 + 是否我们方法的直接前身。**不盲目复现全部 SOTA**）
- **梯队①（立刻，低成本，必做）**：`Mem0`（开源，跑通=验证评测 pipeline + 拿 training-free 对照数字）；`BM25`（几行 rank-bm25，坐实"BM25 追平 46%"这个 motivation 核武器）。
- **梯队②（有开源代码可 fork）**：`MemAgent`（Multi-Conv DAPO；"K 个独立 context 共享一个 trajectory 奖励"与"每说话人一条独立流"同构 → fork 成 per-speaker 多流，是最省力的 RL 起点）；可选 `LightMem`（zjunlp 开源, ICLR'26）。
- **梯队③（无公开代码、须自实现，按收益排序）**：`DeltaMem` 的 Memory-based Levenshtein 奖励（贡献①基础，先单独验证能分好/坏记忆）→ `Memory-R2` 的 **fact-extractor co-learning**（贡献②基础；**关键洞察：Memory-R2 自己的消融显示 LoGo 只 +3 F1，fact-extractor 才是命脉，单训它崩到 28.30 → 先做 fact-extractor，LoGo 次之**）→ `Memory-R1`（outcome-only RL baseline 对照）。
- **暂不优先**：CoMAM / Mem-T / TreeMem / MemoryOS / MemGAS / GAM（无代码或开销大，cite 即可；CoMAM 的 adaptive credit 只是 Spearman 排名相关、可后期几行加上）。

### 6.2 三阶段路线图（若冲刺 AAAI）
- Phase 1（即刻–7月初）：合成 200 条数据($50–100)、跑通 BM25/Mem0 baseline、Qwen SFT(Stage1)。
- Phase 2（7–9月，~4×A100/~$1,100）：Joint RL → 端到端；三多方 benchmark 主实验 + LoCoMo 兼容性；Top-3 消融（per-speaker vs flat Levenshtein +5–10 / joint vs sequential +4–8 / LoGo vs 无 +2–4）。
- Phase 3（9–11月）：回填实验数字 → arXiv preprint → 投稿。

### 6.3 待导师拍板的开放决策
时间线（冲 AAAI 还是稍晚会议）/ 算力经费 / 数据策略（纯合成够不够、要不要人工种子）/ 基座模型 / 降级方案（SFT-only 还是转分析型论文）/ 是否拆 SpeakerLevenshtein 成 short paper。

---

## 7. 关键数字 / 事实速查

- benchmark：SocialMemBench 开源 0.12–0.18（uncompressed 0.345，Gemini full-ctx 上界 0.721，目标 >0.35）；GroupMemBench 最强 46%（知识更新 27.1% / 术语歧义 37.7%）；EverMemBench Oracle 多跳 ~26%；LoCoMo dyadic 标准（Memory-R2 报 49.67 F1，去掉 fact-extractor 崩到 28.30）。
- 训练经验：用 token-level F1 不用 binary EM（G=4 时 EM 梯度=0）；Memory-R1 仅 152 条即 +48%（小样本可行）；DeltaMem τ≈0.5–0.7、训练 reward 稳定在 ~0.75。
- 效率叙事：2k 记忆 ≈ 32k context（16× 效率，来自 PersonaMem）。

---

## 8. 仓库结构（详细）

### 8.1 顶层核心文档（最常用）
- `项目概览-SpeakerMem-R1.md` — 项目总览 + 三大贡献 + 文件地图 + 关键数字备忘。
- `进度.md` — 实时进度跟踪（调研清单勾选）。
- `汇报V2-问题导向文档.md` — **问题 / 指标 / SOTA / RelatedWork 逐篇(动机·方法·自身不足,按时间) / §5.5 复现优先级**。新会话必读。
- `具体实验细节文档.md` — 方法输入输出 / 三 agent 逐步 I/O / 训练流程 / 6 类多角色"谁说了什么"示例。
- `SpeakerMem-R1-v2-方法spec.md` — **可实现级方法规格书**（符号、5 层记忆 dataclass、动作空间、奖励公式与伪代码、三阶段训练、超参 yaml、评测/消融设计、合成数据 prompt）。
- `进度汇报-给导师-2026-06-02.md` — 给导师的进度汇报（含风险/时间线/待定问题）。

### 8.2 论文草稿（7 章）
`论文草稿-Abstract-Introduction.md` / `论文草稿-RelatedWork章节.md` / `论文草稿-Method章节.md` / `论文草稿-Experiments章节.md`（数字待填）/ `论文草稿-Conclusion章节.md` / `论文草稿-Appendix章节.md` / `论文写作指南-AAAI格式.md` / `论文参考文献.bib`。
`备选草稿/` — 旧分支的备选 Method/RelatedWork 草稿（G8AV3、kO4UN）。

### 8.3 方法/实验/数据设计
`数据合成Pipeline设计.md`、`迭代V3-benchmark数据与训练数据方案.md`、`50天冲刺实验指南.md`、`Idea7-SpeakerLevenshtein-独立成文评估.md`、`idea综合评估与论证.md`、`整体评估-V5版.md`、`整合说明-三分支合并.md`。

### 8.4 调研/迭代记录
`深度调研.md`、`综合分析与补充调研.md`、`调研.md`、`迭代V2-竞品分析与方案修订.md`、`迭代V3-竞品技术细节深挖.md`、`迭代V3-新竞品深挖与方案精化.md`、`迭代V3-深化方法与补充调研.md`、`迭代V4-ICLR Workshop与新论文调研.md`、`迭代V4-信用分配与安全最新调研.md`、`迭代V6-竞争确认与代码实现.md`。

### 8.5 文献精读（33 个 `<名>/详解.md`，按类）
- **RL 记忆方法（dyadic，我们的直接技术来源）**：`Memory-R1/` `Agemem/` `Mem-alpha/` `MEM1/` `MemSearcher/` `Mem-T/` `MemBuilder/` `MemAgent/` `DeltaMem/`★ `Memory-R2/`★ `CoMAM/`★ `TreeMem/` `R2-Mem/` `DeferMem/` `DualMem/`（★ = 三大贡献的直接前身）。
- **Training-free 记忆系统**：`Mem0-AMEM-MemoryBank/`（基线三件套）。
- **多方对话系统（training-free / 生成）**：`Collaborative-Memory/` `G-Memory/` `MuPaS/` `SA-LLM/` `SHARE/` `MOOM/`。
- **多方 / dyadic Benchmark**：`GroupMemBench/` `EverMemBench/` `SocialMemBench/` `LOCOMO/` `LongMemEval-PersonaMem/`。
- **长程 RL 信用分配 / 技巧**：`HCAPO/` `HiPER/` `多方经典与RL技巧/`。
- **安全 / 失败模式**：`MemorySafety/` `MemFail/`。
- **其他**：`ReasoningBank/`。

### 8.6 代码 `核心代码实现/`（6 模块，dry-run/mock 通过，**未真实训练**）
- `speaker_levenshtein.py` — SpeakerLevenshtein 奖励函数（贡献①）。
- `speaker_aware_memory.py` — 5 层 Speaker-Indexed Memory 数据结构。
- `synthetic_data_pipeline.py` — 图驱动合成训练数据（需接 GPT-4 API）。
- `memory_agent.py` — 3 阶段 Agent（Construction/Retrieval/Answer）。
- `grpo_trainer.py` — SC-LoGo-GRPO 训练循环。
- `evaluation.py` — 三个多方 benchmark 评测接口。

### 8.7 汇报/构建产物
- `SpeakerMem-R1-进度汇报-2026-06-02.pptx`（详细汇报，29 页）、`SpeakerMem-R1-汇报V2-问题导向.pptx`（精简问题导向，11 页）。
- `汇报slides-build/` — PPT 生成器：`gen.js`（详细版）、`gen_v2.js`（V2）+ `package*.json`。`node gen.js`/`node gen_v2.js` 重生成。**`node_modules/` 与渲染图 `img*/` 已 .gitignore**（远程需先 `npm install`）。

---

## 9. 工作约定

- **Slides**：只改 `汇报slides-build/gen*.js`，再 `node gen*.js` 重生成；不要手改 .pptx。导出 PNG 用 PowerPoint COM（Windows）；远程 Linux 用 LibreOffice `soffice --convert-to pdf` + `pdftoppm`。
- **git**：提交信息末尾加 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`；**只在用户明确要求时 commit/push**。大文件/构建产物已在 `.gitignore`（node_modules、渲染图、临时 pptx）。远程 1 个分支 `main`（其他已删）。
- **编辑文档**：改前先 Read；中文文档注意编码。

---

## 10. 新会话从这里继续（下一步具体动作）

**立刻做（P4 · 梯队①）**：在远程环境搭复现脚手架，先在 **GroupMemBench** 上跑通 **Mem0 + BM25** baseline，验证评测 pipeline 并复现"BM25 追平 46%"的数字。建议：
1. 在远程 `git pull` 同步本仓库；`cd 汇报slides-build && npm install`（若要重生成 slides）。
2. 新建 `复现/`（或 `experiments/`）目录：放数据下载脚本、Mem0/BM25 评测脚本、`requirements.txt`、`README.md`（记录每次跑的命令与数字）。
3. 拿到第一组对照数字后，进梯队②（fork MemAgent）和梯队③（先 DeltaMem 奖励，再 Memory-R2 fact-extractor）。

**给新会话的开场提示**：
> 读 `CLAUDE.md` 和 `汇报V2-问题导向文档.md §5.5`，从 P4 梯队① 开始：在 GroupMemBench 上跑通 Mem0 + BM25，验证评测 pipeline。
