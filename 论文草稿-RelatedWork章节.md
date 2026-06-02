# SpeakerMem-R1 论文草稿：Related Work 章节

**版本**：v2.0（2026-06-02，中文化改写；以 kO4UN 中文版为蓝本，并入 R²-Mem / 课程学习 / MemBuilder 等补充）  
**状态**：草稿，参考文献格式待填正式 BibTeX

---

## 2. Related Work

### 2.1 Dyadic RL 记忆 agent

RL 用于长期对话记忆管理的研究在过去一年快速演进。**Memory-R1** [cite] 首次把 RL 用于长期记忆管理，提出 Memory Manager + Answer Agent 的双 agent 架构，前者学习 ADD/UPDATE/DELETE/NOOP 操作，后者通过 Memory Distillation 从 60 条候选中推理答案，仅用 152 条 QA pairs 训练即在 **LoCoMo** 上取得显著提升（F1 相对提升 48%）。**AgeMem** [cite] 进一步把 LTM/STM 管理统一为六类工具动作，提出 step-wise GRPO 来解决记忆操作轨迹碎片化的优化问题，在 5 个 benchmark 上平均提升 4.82–8.57%。**Mem-α** [cite] 设计 core/episodic/semantic 三组件架构，在 30k token 上训练却能泛化到 400k+ token。**MemSearcher** [cite] 提出 multi-context GRPO，使 3B 模型超过 7B baseline。**MEM1** [cite] 用 masked trajectory 技术处理多上下文演化下的非线性轨迹。

更近的工作聚焦于信用分配（credit assignment）与奖励密度（reward density）问题。**Mem-T** [cite] 提出 Memory Operation Tree（MoT），通过树搜索探索多条操作路径，把 outcome reward 反向传播到每个操作节点，并结合 hindsight credit 精确归因，比 **A-MEM**/**Mem0** 提升达 14.92%。**DeltaMem** [cite] 引入 Memory-based Levenshtein Distance 作为稠密过程奖励（dense process reward），通过 optimal transport 计算 predicted 与 GT memory state 的距离，用 $R = 0.1 R_{format} + 0.1 R_{retrieval} + 0.8 R_{state}$ 的权重设计显著改善了收敛速度。**Memory-R2** [cite] 识别出 GRPO 在 multi-session 训练中信用分配不公平的根本原因——不同 rollout 修改了不同的 memory state，导致中间态发散——并提出 LoGo-GRPO，通过 local rerollout（从 shared intermediate state 分支）恢复公平比较，同时用 8→16→32 sessions 的渐进式 curriculum 稳定训练。**CoMAM** [cite] 指出 Memory-R1 的 sequential 双 agent 训练忽视了跨 agent 协同，提出 joint 端到端 RL，用 group-level ranking consistency 量化每个 agent 的 adaptive credit weight，在 **PersonaMem** 上提升 8.5–16.7%。此外，**MemBuilder** [cite] 提出 attributed dense reward 与四维记忆结构，是技术上最接近的近期竞品之一，可作为重要 baseline；**R²-Mem** [cite] 引入反思式经验记忆搜索（reflective memory search），在 dyadic 设定下取得 F1 +22.6% 的提升，但同样不涉及多方说话人维度。

上述所有工作均在 **dyadic（两人对话）** 设定下设计和验证，没有考虑多方场景下的说话人归属与受众适配问题。本文填补这一空白。

---

### 2.2 多方对话记忆系统

多方记忆的研究主要集中在 training-free 系统与 benchmark 构建上，缺乏 RL 训练方法。

**Collaborative Memory** [cite] 最早系统化地处理多用户 LLM agent 的共享/私有记忆，用 bipartite access control graph 编码不可变的 provenance（来源 agent、访问资源、时间戳），支持时变权限；但其写入策略是固定规则，并不可学习。

**G-Memory** [cite] 受组织记忆理论启发，为多 agent 系统设计三层图层级记忆（insight/query/interaction graph），通过 bi-directional traversal 同时检索高层洞察与底层细节，在 5 个 benchmark 上最高提升 20.89%；但 G-Memory 是 training-free 的，其图结构读写策略不经过 RL 优化。

**SHARE** [cite] 从电影剧本构建了首个包含共享记忆的多说话人长期对话数据集，涉及角色间的共同记忆与关系演化，为多方记忆评测提供了早期基础。**SA-LLM** [cite] 引入说话人感知对比学习（speaker-aware contrastive learning）进行多方对话生成，通过说话人归因的输入编码与对比学习目标提升 coherence。**MuPaS** [cite] 提出 role-masked SFT 策略训练多方对话模型，我们直接借鉴这一技术用于 Stage 1 训练。

需要强调：**G-Memory、Collaborative Memory 均是 training-free 的**，而现有多方对话 RL 工作（如 MuPaS/SA-LLM）都针对对话生成而非记忆管理。因此"多方 + 说话人锚定 + RL 记忆管理"这一交集仍是空白。

---

### 2.3 多方记忆评测 Benchmark

2026 年密集出现了专门针对多方场景的记忆评测 benchmark，揭示了现有系统的严重局限。

**GroupMemBench** [cite] 用 graph-grounded synthesis pipeline 构造多方对话，分别测量 group dynamics（群组互动动态）、speaker-grounded belief tracking（说话人归属信念追踪）与 audience-adapted language（受众适配语言），发现 **BM25** 这种简单词面匹配竟能匹配甚至超过现有神经 agent 记忆系统，揭示出词面准确性（即正确的说话人归属）才是多方记忆的真正瓶颈。

**EverMemBench** [cite] 构造了超过 100 万 token 的多方协作对话，覆盖 fine-grained recall、memory awareness 与 user profile understanding 三个维度，包含 2,400 个 QA pairs，是当前规模最大的多方长期记忆 benchmark。

**SocialMemBench** [cite] 构建了 430 个 personas、1,031 个 QA pairs 的社交群组网络，覆盖 5 类 archetype（close friends / family / recreational / interest community / acquaintance），发现现有记忆框架（**Mem0**/**LangMem**/**Graphiti**/**Cognee**）在多方场景的得分仅 0.12–0.18，而不压缩的完整对话检索 reference 为 0.345——说明**问题不在于长度，而在于结构化组织**，这正是 RL 训练的甜点。

我们在这三个 benchmark 上评测 SpeakerMem-R1，并把 SocialMemBench 的 0.35（uncompressed retrieval reference）设为最低目标，把 Gemini 2.5 Flash full-context reference 的 0.721 设为长期上界。

---

### 2.4 长程 RL 的信用分配

信用分配（credit assignment）是长程 RL 的核心挑战，在 LLM agent 领域受到广泛关注。

**GRPO** [cite] 的 group-relative advantage 估计在短任务上有效，但在长程任务中无法区分关键步骤与冗余步骤。**AgeMem** 的 step-wise GRPO 通过时间切片改善颗粒度。**HiPER** [cite] 提出分层 RL + 分层优势估计（HAE），在 ALFWorld 达到 97.4%、WebShop 达到 83.3%。**HCAPO** [cite] 利用 LLM 自身作为 post-hoc critic 进行 hindsight 推理，提供比 GRPO 更精确的 step-level Q-value 估计，解决了 value baseline 不对齐问题。

上述信用分配方法均在 **单一用户视角** 下工作。在多方场景中，信用分配需要在两个维度上同时精化：(1) **操作层面**——哪一步 memory 操作是关键的？(2) **说话人层面**——哪个说话人的信息写入对回答哪类问题有贡献？本文提出 speaker-conditioned LoGo-GRPO，在 **Memory-R2** 的 local rerollout 基础上，按说话人子集分层，以确保 local 组内比较的公平性。

---

### 2.5 课程学习与训练稳定性

记忆 RL 的训练稳定性高度依赖课程设计与奖励形式。已有工程研究 [cite] 表明：在长程记忆 RL 中应使用 token-level F1 而非 binary EM（后者在 $G=4$ 时梯度为零）、混合课程（mixed curriculum）优于单一难度课程，且训练样本量约在 150 条附近出现"专精 vs 聚合"的拐点。**Memory-R2** [cite] 的 session-count 渐进课程（8→16→32）是稳定 multi-session 训练的关键。我们在此基础上沿**说话人数量维度**扩展课程（K=3→5→8），构成 session 长度 × 说话人数量的二维课程，这对多方记忆 RL 是新的设计。

---

### 表 1：竞品 Landscape（多方 + RL 零篇验证）

| 方法 | 年份 | 训练方式 | Setting | 评测 Benchmark |
|------|------|---------|---------|---------------|
| Memory-R1 | 2025.08 | 2-agent GRPO | **dyadic** | LoCoMo |
| AgeMem | 2026.01 | step-wise GRPO | **dyadic** | LoCoMo |
| Mem-T | 2026.01 | MoT-GRPO | **dyadic** | LoCoMo |
| Memory-R2 | 2026.05 | LoGo-GRPO | **dyadic** | LoCoMo |
| DeltaMem | 2026.04 | Levenshtein RL | **dyadic** | LoCoMo/PersonaMem |
| CoMAM | 2026.03 | joint RL | **dyadic** | PersonaMem |
| MemBuilder | 2026.01 | attributed dense reward | **dyadic** | LoCoMo |
| G-Memory | 2025.06 | training-free | multi-agent | 5 benchmarks |
| Collab. Mem | 2025.05 | training-free | multi-agent | — |
| GroupMemBench | 2026.05 | — | **multi-party** | 自身（benchmark） |
| SocialMemBench | 2026.05 | — | **multi-party** | 自身（benchmark） |
| **SpeakerMem-R1（本文）** | **2026** | **RL** | **multi-party** | **3 benchmarks** |

**截至 2026/6/2，多方 + RL 训练的记忆管理方法为零篇。**

---

*注：上述段落为草稿版本，参考文献格式待填充正式 BibTeX；数字结果（X.XX）待实验后填入。*
