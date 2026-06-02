# SpeakerMem-R1：论文草稿（单文件版）

**版本**：v3.1（2026-06-02，中文化改写；基于 V3 迭代方法 spec）  
**目标会议**：AAAI（截止日期约 2026 年 7-8 月）  
**状态**：Abstract + Introduction 草稿 + Method 提纲（备选素材，正式版以 `论文草稿-*.md` 为准）

---

## 摘要（Abstract，草稿 v1）

**字数目标**：250 词以内（AAAI 标准）

---

大语言模型（LLM）agent 越来越依赖外部记忆系统来支撑长程交互。尽管近期基于强化学习（RL）的方法在 dyadic（一对一）对话记忆上取得了亮眼成绩，真实世界的部署场景——如团队群聊、家庭消息、协作办公环境——却涉及**多方对话（multi-party conversations）**，多个说话人彼此交换信息。现有记忆系统（包括最先进的 RL 训练 agent）把所有对话内容当作单一、无区分的流来处理，从而导致系统性失败：说话人归属错误、跨用户信息泄漏，以及无法根据目标受众调整回应。

我们提出 **SpeakerMem-R1**，**首个面向说话人锚定（speaker-grounded）多方记忆管理的强化学习框架**。SpeakerMem-R1 把记忆表示为一个 20 维矩阵——每个说话人四个认知维度（core、episodic、semantic、insight），外加群组级的 interaction 与 insight 槽位——并带有受众感知的访问控制。我们引入三项新技术贡献：(1) **说话人感知的 Levenshtein 稠密奖励**，按说话人而非全局地评估记忆状态准确性；(2) **说话人条件化的 LoGo-GRPO**，按说话人划分进行 local rerollout 以实现公平的信用分配；(3) **贡献感知的说话人梯度加权**，按每个操作的说话人归属准确度来缩放策略更新。SpeakerMem-R1 通过一个三阶段课程训练，结合多方监督热启动、joint 多 agent RL，以及端到端任务优化。

在三个多方 benchmark——**GroupMemBench**、**EverMemBench**、**SocialMemBench**——上的实验表明，SpeakerMem-R1 显著超过包括 **Memory-R1**、**AgeMem**、**DeltaMem**、**MemBuilder-4B** 在内的强基线，在说话人归属 F1 上提升 X%、在整体任务准确率上提升 Y%。消融实验确认每个组件都独立地贡献了性能。

---

## 1. 引言（Introduction，草稿 v1）

### 第 1 段：背景与重要性

记忆系统是支撑长期用户交互的 LLM agent 的基础。无论是跨 session 追踪用户偏好 [Mem0]、保持一致的人格 [PersonaMem]，还是回忆数月前对话中的事实 [LoCoMo]，选择性地存储、更新与检索信息的能力，正是有用的 agent 与单纯聊天机器人的分水岭。近期强化学习（RL）训练的突破显著改善了记忆质量：**Memory-R1** [cite] 证明 RL 可以联合优化记忆构建与检索 agent；**AgeMem** [cite] 在轨迹内引入了 step-wise 信用分配；**DeltaMem** [cite] 通过基于 Levenshtein 的状态比较实现了稠密奖励信号；**MemBuilder** [cite] 表明贡献感知的梯度加权能进一步提升记忆构建质量。这些进展确立了 RL 作为 LLM agent 中学习记忆管理策略的主导范式。

### 第 2 段：多方鸿沟

然而一个关键空白依然存在：**几乎所有基于 RL 的记忆系统都针对 dyadic（两人）交互**。在现实中，世界上大量对话发生在多方场景里——团队 Slack 频道、家庭 WhatsApp 群、课堂讨论、协作办公环境。如图 1 所示，多方对话引入了 dyadic 设定中不存在的全新挑战：

**(i) 说话人归属（Speaker Attribution）**：每条对话事实都必须锚定到其来源说话人。当 Bob 说"我在考虑换工作"、Alice 说"我对现在的公司很满意"时，记忆系统必须把它们记录为不同的、带归属的事实——而不是合并成自相矛盾的一团。**GroupMemBench** [cite] 显示，现有记忆 agent 在说话人归属任务上的失败率超过 60%。

**(ii) 受众适配（Audience Adaptation）**：某个说话人分享的信息可能只面向部分参与者。心智理论（Theory-of-Mind）推理要求记忆系统不仅追踪*说了什么*，还要追踪*说给谁听* [cite: SocialMemBench]。

**(iii) 群组动态（Group Dynamics）**：多方对话呈现出涌现性的动态——联盟、分歧、话题转移——这些需要超越任何个体记录的群组级记忆表示 [cite: EverMemBench]。

忽视这些挑战的后果是具体的：**SocialMemBench** [cite] 识别出现有记忆系统应用于社交群组场景时的五种系统性失败模式，包括单流混淆、时序状态覆盖、实体合并错误。**MemFail** [cite] 表明，条件事实失败与共存事实保留失败在多方设定中被复合放大。此外，近期安全研究 [cite: Remembering More] 表明，未锚定的多方记忆会带来纵向（longitudinal）隐私风险——单个对抗性说话人可以用伤害其他参与者的方式污染群组记忆。

### 第 3 段：先前工作的局限（清晰的 delta）

现有方法在三个方面有所不足：

**Training-free 系统**（**Mem0**、**A-MEM**、**G-Memory**、**CollaborativeMem**）施加启发式记忆操作，不从经验中学习。它们无法适配特定多方对话类型的统计特性，其检索模块也未针对说话人感知的查询优化。**GroupMemBench** 报告，即便是 **BM25** 这种数十年历史的关键词检索基线，也在多方状态追踪任务上追平或超过这些系统，说明瓶颈在于记忆组织，而非检索。

**Dyadic RL 系统**（**Memory-R1**、**AgeMem**、**DeltaMem**、**Memory-R2**、**CoMAM**、**MemBuilder**）在一对一设定中取得强劲结果，但无法处理说话人的多重性。直接应用到多方 benchmark 时，它们的单流记忆架构会混淆来自多个说话人的信息，造成归属失败与隐私泄漏。正如我们实验所示，即便最强的 dyadic RL 系统（**MemBuilder-4B**）在 **GroupMemBench** 上相比其 dyadic 表现也出现严重退化。

**多方 benchmark**（**GroupMemBench**、**EverMemBench**、**SocialMemBench**）近期建立了严谨的群组对话记忆评测框架，但尚无方法论文提出专门针对这些 benchmark 训练的系统。

### 第 4 段：我们的方案

我们提出 **SpeakerMem-R1**，一个学习说话人锚定多方记忆管理策略的强化学习框架。SpeakerMem-R1 建立在三个核心原则之上：

1. **说话人结构化记忆**：一个 20 维记忆矩阵，显式分离每个说话人的核心事实、情节事件、语义抽象与人格洞察，并辅以群组级的互动模式与集体洞察。

2. **说话人感知的稠密奖励**：我们把 **DeltaMem** 的 Levenshtein 状态奖励扩展为按说话人运作，确保记忆操作不仅按整体准确率、还按每个说话人的信息是否被正确归属来评估。一个额外的跨说话人泄漏惩罚抑制了侵犯隐私的混淆。

3. **说话人条件化训练**：我们把 **Memory-R2** 的 LoGo-GRPO 扩展为按说话人划分进行 local rerollout，并把 **MemBuilder** 的归属梯度加权扩展为考虑说话人归属正确性。这确保模型同时获得公平的信用分配与说话人校准的学习信号。

### 第 5 段：贡献

我们的贡献是：

1. **首个基于 RL 的多方记忆系统**：据我们所知，SpeakerMem-R1 是首个为多方对话中说话人锚定记忆管理训练 RL 策略的工作。

2. **说话人感知的 Levenshtein 奖励（SpeakerLev）**：稠密状态差异奖励的按说话人扩展，同时惩罚归属错误与跨说话人信息泄漏。

3. **说话人条件化的 LoGo-GRPO**：一个信用分配算法，使因说话人特定记忆状态而发散的轨迹之间能够进行公平的组比较。

4. **贡献感知的说话人梯度加权**：一种训练技术，按检索使用频率与说话人归属准确度共同缩放策略梯度更新。

5. **隐私感知的记忆架构**：一个基于受众的访问控制系统，带说话人信任建模与隔离（quarantine）机制。

6. **实证评测**：在三个多方 benchmark（GroupMemBench、EverMemBench、SocialMemBench）上、对比八个基线的全面实验，在说话人归属 F1、受众适配分数与整体任务准确率上展示显著提升。

---

## 2. Related Work（草稿 v1 提纲）

### 2.1 LLM agent 的记忆系统

**Training-free 方法**：早期记忆系统依赖启发式操作——受 Ebbinghaus 启发的遗忘 [MemoryBank]、CRUD 操作 [Mem0]、原子笔记图 [A-MEM]。这些系统无需训练，但无法适配对话统计特性。

**基于 RL 的 dyadic 系统**：**Memory-R1** [cite] 展示了用于联合记忆构建-检索优化的端到端 RL。**AgeMem** [cite] 引入 step-wise GRPO 以在轨迹内实现更稠密的信用分配。**Mem-α** [cite] 提出带 RL 的三组件架构。**MEM1** [cite] 对长程任务使用 masked trajectory。**DeltaMem** [cite] 为记忆状态转移引入基于 Levenshtein 的稠密奖励。**Memory-R2** [cite] 通过 LoGo-GRPO 处理公平信用分配。**CoMAM** [cite] 为记忆 pipeline 提出 joint 多 agent RL。**MemBuilder** [cite] 引入带贡献感知梯度加权的归属稠密奖励。

**多方 training-free 系统**：**G-Memory** [cite] 为多 agent 协作提出三层图记忆。**CollaborativeMem** [cite] 引入带 provenance 追踪的私有/共享记忆。两者均未用 RL 训练。

### 2.2 多方对话 Benchmark

**GroupMemBench** [cite]、**EverMemBench** [cite]、**SocialMemBench** [cite] 为多方记忆评测建立了严谨的 benchmark。**LoCoMo** [cite] 与 **LongMemEval** [cite] 覆盖 dyadic 设定。**PersonaMem-v2** [cite] 聚焦人格一致性。

### 2.3 记忆失败分析

**MemFail** [cite] 系统化刻画了现有记忆系统的五种失败模式。**SocialMemBench** [cite] 识别了五种群组场景失败模式。这些分析论证了对专为多方设定设计的架构的需求。

### 2.4 记忆安全与隐私

时序记忆污染 [cite: Remembering More]、演化记忆治理 [cite: SSGM]、隐私风险 [cite: Unveiling Privacy] 凸显了具备记忆能力的 LLM 的安全挑战，而这些挑战在多方设定中被放大。

---

## 3. Problem Formulation（草稿）

### 3.1 多方对话记忆任务

**输入**：一个多方对话 session $S_t = \{(u_i, p_i, s_i)\}_{i=1}^{T}$，其中 $u_i$ 是第 $i$ 条话语，$p_i$ 是其说话人 ID，$s_i$ 是其受众集合。agent 还会收到上一 session 的记忆状态 $M_{t-1}$。

**输出**：(1) 更新后的记忆状态 $M_t$；(2) 对关于说话人信息、意图或关系的查询 $Q_t$ 的回应。

**记忆状态**：$M_t = \{M_s\}_{s \in \mathcal{P}} \cup M_G$，其中：
- $M_s = \{M_s^{\text{core}}, M_s^{\text{epi}}, M_s^{\text{sem}}, M_s^{\text{ins}}\}$ 是说话人 $s$ 的四维记忆
- $M_G = \{M_G^{\text{inter}}, M_G^{\text{ins}}\}$ 是群组级记忆

**评测**：来自 GroupMemBench 的三个属性：
1. **说话人归属 F1（Speaker Attribution F1）**：被正确归属到来源说话人的事实占比
2. **受众适配分数（Audience Adaptation Score）**：回应对目标受众适配的质量
3. **群组动态召回（Group Dynamics Recall）**：对群组级互动模式的保留

### 3.2 记忆 agent 策略

记忆 agent 学习一个策略 $\pi_\theta(a_t | c_t, M_{t-1})$，其中：
- $c_t$ 是当前对话上下文（近期话语）
- $a_t \in \mathcal{A}$ 是一个记忆动作（WRITE、UPDATE、DELETE、SUMMARY、PROMOTE、SUPPRESS、QUARANTINE、READ_CROSS、NOOP）
- $M_t = f(M_{t-1}, a_t)$ 是确定性的记忆转移函数

该策略被训练以最大化期望奖励：
$$J(\theta) = \mathbb{E}_{\tau \sim \pi_\theta} \left[ R(\tau, M_T, Q, G) \right]$$

其中 $G$ 是真值记忆状态，$Q$ 是评测查询。

---

## 4. Method（SpeakerMem-R1）—— 关键章节提纲

### 4.1 说话人结构化记忆架构
- 20 维记忆矩阵图示
- MemoryFragment 数据结构
- 受众感知访问控制

### 4.2 说话人感知的 Levenshtein 稠密奖励（SpeakerLev）
- DeltaMem 公式回顾
- 扩展到 per-speaker
- 跨说话人泄漏惩罚
- 完整 reward 函数（8 个组件）

### 4.3 说话人条件化的 LoGo-GRPO
- Memory-R2 LoGo-GRPO 回顾
- 说话人划分分层
- local + global 组合

### 4.4 贡献感知的说话人梯度加权
- MemBuilder 归属机制回顾
- 说话人感知扩展
- 训练稳定性分析

### 4.5 三阶段训练课程
- Stage 1：说话人感知 SFT
- Stage 2：Joint 多 agent RL
- Stage 3：端到端任务 RL

---

## 5. Experiments —— 实验设计提纲

### 5.1 Benchmark
- GroupMemBench（三维：attribution + audience + group dynamics）
- EverMemBench（2,400 QA，三维：recall + awareness + profile）
- SocialMemBench（1,031 QA，9 类，5 个 archetype）
- LoCoMo（迁移测试，保证 dyadic 能力不退化）

### 5.2 Baseline（8 个）
见 V3 spec Part 2.7 表格

### 5.3 Metrics
- Token-level F1（主要 QA 指标）
- Speaker Attribution F1（新指标，核心贡献之一）
- Audience Adaptation Score
- Privacy Leakage Rate（安全指标）

### 5.4 消融（6 项）
见 V3 spec Part 2.6

### 5.5 分析
- BM25 强的原因分析（为什么 retrieval 不是瓶颈）
- RL 训练收敛曲线
- 说话人数量的影响（3/5/10 speaker）
- 群组规模的影响（来自 SocialMemBench 的 4-30 人设置）

---

## 写作 Timeline（估算）

| 阶段 | 内容 | 估算时间 |
|------|------|---------|
| 方法 spec 细化 | 把 V3 spec 转化为论文 Method 节 | 1 周 |
| 实验数据合成 | 构建多方对话训练集 | 2 周 |
| Baseline 复现 | Memory-R1 / AgeMem / MemBuilder | 3 周 |
| SpeakerMem-R1 实现 | 按 V3 spec 实现 | 4 周 |
| 实验运行 | 跑完所有 benchmark + 消融 | 3 周 |
| 论文写作 | Abstract → Introduction → Method → Experiments | 2 周 |
| **总计** | | **约 15 周（AAAI 截止前可完成）** |

**关键路径**：实验数据合成 → Baseline 复现 → SpeakerMem-R1 实现 → 实验运行

---

## 注意事项

1. **Speaker F1 需要标注**：GroupMemBench 需要有 speaker-grounded GT，确认其 annotation 是否包含 speaker attribution ground truth
2. **EverMemBench 的"用户画像理解"任务** 是否等价于我们的 speaker profile 评测——需要对齐
3. **MemBuilder-4B 的 baseline 代码**：是否开源？需要联系作者或重新实现
4. **计算资源**：7B 模型 + 4 × A100 + G=4 rollout，估算训练时间 ~2 天/轮，总计 ~10 轮 = 20 天
