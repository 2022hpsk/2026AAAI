# SpeakerMem-R1：论文草稿
**版本**：v3（基于 V3 迭代方法 spec）  
**目标会议**：AAAI 2026（截止日期约 2026 年 8 月）  
**状态**：Abstract + Introduction Draft + Method Outline

---

## Abstract（草稿 v1）

**字数目标**：250 词以内（AAAI 标准）

---

Large language model (LLM) agents increasingly depend on external memory systems to support long-horizon interactions. While recent reinforcement learning (RL)-based approaches have achieved impressive results in dyadic (one-on-one) conversation memory, real-world deployments such as team chat, family messaging, and collaborative work environments involve **multi-party conversations** where multiple speakers exchange information with one another. Existing memory systems—including state-of-the-art RL-trained agents—treat all conversational content as a single undifferentiated stream, causing systematic failures: speaker-attribution errors, cross-user information leakage, and inability to adapt responses to intended audiences.

We propose **SpeakerMem-R1**, the first reinforcement learning framework for **speaker-grounded multi-party memory management**. SpeakerMem-R1 represents memory as a 20-dimensional matrix—four cognitive dimensions (core, episodic, semantic, insight) per speaker, plus group-level interaction and insight slots—with audience-aware access control. We introduce three novel technical contributions: (1) **speaker-aware Levenshtein dense reward** that evaluates memory state accuracy per-speaker rather than globally; (2) **speaker-conditioned LoGo-GRPO** that performs local rerollouts conditioned on speaker partitions for fair credit assignment; and (3) **contribution-aware speaker gradient weighting** that scales policy updates by each operation's speaker-attribution accuracy. SpeakerMem-R1 is trained through a three-stage curriculum combining multi-party supervised warm-up, joint multi-agent RL, and end-to-end task optimization.

Experiments across three multi-party benchmarks—GroupMemBench, EverMemBench, and SocialMemBench—demonstrate that SpeakerMem-R1 substantially outperforms strong baselines including Memory-R1, AgeMem, DeltaMem, and MemBuilder-4B, achieving X% improvement in speaker attribution F1 and Y% in overall task accuracy. Ablations confirm that each component contributes independently to performance.

---

## 1. Introduction（草稿 v1）

### 段落 1：Background & Importance

Memory systems are fundamental to LLM agents that support long-term user interactions. Whether tracking a user's preferences across sessions [Mem0], maintaining consistent personas [PersonaMem], or recalling facts from months-old conversations [LoCoMo], the ability to selectively store, update, and retrieve information separates useful agents from mere chatbots. Recent breakthroughs in reinforcement learning (RL) training have substantially improved memory quality: Memory-R1 [cite] demonstrated that RL can jointly optimize memory construction and retrieval agents; AgeMem [cite] introduced step-wise credit assignment within trajectories; DeltaMem [cite] achieved dense reward signals via Levenshtein-based state comparisons; and MemBuilder [cite] showed that contribution-aware gradient weighting further boosts memory construction quality. These advances have established RL as the dominant paradigm for learning memory management policies in LLM agents.

### 段落 2：The Multi-Party Gap

Yet a critical gap remains: **virtually all RL-based memory systems target dyadic (two-party) interactions**. In reality, much of the world's conversation happens in multi-party settings—team Slack channels, family WhatsApp groups, classroom discussions, and collaborative work environments. As shown in Figure 1, multi-party conversations introduce fundamentally new challenges absent in dyadic settings:

**(i) Speaker Attribution**: Each conversational fact must be grounded to its originating speaker. When Bob says "I'm considering changing jobs" and Alice says "I'm happy at my current company," a memory system must record these as distinct, attributed facts—not merge them into a contradictory mess. GroupMemBench [cite] shows that current memory agents fail speaker-attribution tasks at rates exceeding 60%.

**(ii) Audience Adaptation**: Information shared by one speaker may be intended only for a subset of participants. Theory-of-Mind reasoning requires the memory system to track not just *what* was said, but *to whom* it was directed [cite: SocialMemBench].

**(iii) Group Dynamics**: Multi-party conversations exhibit emergent dynamics—alliances, disagreements, topic shifts—that require group-level memory representation beyond any individual's records [cite: EverMemBench].

The consequences of ignoring these challenges are concrete: SocialMemBench [cite] identifies five systematic failure modes in existing memory systems when applied to social group settings, including single-stream conflation, temporal-state overwrite, and entity-merging errors. MemFail [cite] demonstrates that conditional-fact failures and coexisting-fact preservation failures are compounded in multi-party settings. Moreover, recent safety research [cite: Remembering More] shows that ungrounded multi-party memory creates longitudinal privacy risks—a single adversarial speaker can contaminate group memory in ways that harm other participants.

### 段落 3：Prior Work Limitations（清晰 delta）

Existing approaches fall short in three ways:

**Training-free systems** (Mem0, A-MEM, G-Memory, CollaborativeMem) apply heuristic memory operations without learning from experience. They cannot adapt to the statistics of specific multi-party conversation types, and their retrieval modules are not optimized for speaker-aware queries. GroupMemBench reports that even BM25—a decades-old keyword retrieval baseline—matches or outperforms these systems on multi-party state-tracking tasks, suggesting the bottleneck lies in memory organization, not retrieval.

**Dyadic RL systems** (Memory-R1, AgeMem, DeltaMem, Memory-R2, CoMAM, MemBuilder) achieve strong results in one-on-one settings but cannot handle speaker multiplicity. When directly applied to multi-party benchmarks, their single-stream memory architecture conflates information from multiple speakers, causing attribution failures and privacy leakage. As we show experimentally, even the strongest dyadic RL systems (MemBuilder-4B) show severe performance degradation on GroupMemBench compared to their dyadic performance.

**Multi-party benchmarks** (GroupMemBench, EverMemBench, SocialMemBench) have recently established rigorous evaluation frameworks for group conversation memory, but no method paper has proposed a trained system specifically targeting these benchmarks.

### 段落 4：Our Approach

We propose **SpeakerMem-R1**, a reinforcement learning framework that learns speaker-grounded multi-party memory management policies. SpeakerMem-R1 is built on three core principles:

1. **Speaker-structured memory**: A 20-dimensional memory matrix that explicitly separates each speaker's core facts, episodic events, semantic abstractions, and persona insights, augmented by group-level interaction patterns and collective insights.

2. **Speaker-aware dense rewards**: We extend DeltaMem's Levenshtein state reward to operate per-speaker, ensuring that memory operations are evaluated not just by overall accuracy but by whether each speaker's information is correctly attributed. An additional cross-speaker leakage penalty discourages privacy-violating conflation.

3. **Speaker-conditioned training**: We extend Memory-R2's LoGo-GRPO to perform local rerollouts conditioned on speaker partitions, and extend MemBuilder's attributed gradient weighting to account for speaker-attribution correctness. This ensures that the model receives both fair credit assignment and speaker-calibrated learning signals.

### 段落 5：Contributions

Our contributions are:

1. **First RL-based multi-party memory system**: SpeakerMem-R1 is, to our knowledge, the first work that trains an RL policy for speaker-grounded memory management in multi-party conversations.

2. **Speaker-aware Levenshtein reward (SpeakerLev)**: A per-speaker extension of dense state-diff rewards that simultaneously penalizes attribution errors and cross-speaker information leakage.

3. **Speaker-conditioned LoGo-GRPO**: A credit assignment algorithm that enables fair group comparison across trajectories that diverge due to speaker-specific memory states.

4. **Contribution-aware speaker gradient weighting**: A training technique that scales policy gradient updates by both retrieval usage frequency and speaker-attribution accuracy.

5. **Privacy-aware memory architecture**: An audience-based access control system with speaker trust modeling and quarantine mechanisms.

6. **Empirical evaluation**: Comprehensive experiments on three multi-party benchmarks (GroupMemBench, EverMemBench, SocialMemBench) with eight baselines, demonstrating substantial improvements in speaker attribution F1, audience adaptation score, and overall task accuracy.

---

## 2. Related Work（草稿 v1 Outline）

### 2.1 Memory Systems for LLM Agents

**Training-free approaches**: Early memory systems relied on heuristic operations—Ebbinghaus-inspired forgetting [MemoryBank], CRUD operations [Mem0], atomic note graphs [A-MEM]. These systems require no training but cannot adapt to conversation statistics.

**RL-based dyadic systems**: Memory-R1 [cite] demonstrated end-to-end RL for joint memory construction-retrieval optimization. AgeMem [cite] introduced step-wise GRPO for denser credit assignment within trajectories. Mem-α [cite] proposed a three-component architecture with RL. MEM1 [cite] used masked trajectories for long-horizon tasks. DeltaMem [cite] introduced Levenshtein-based dense rewards for memory state transitions. Memory-R2 [cite] addressed fair credit assignment via LoGo-GRPO. CoMAM [cite] proposed joint multi-agent RL for memory pipelines. MemBuilder [cite] introduced attributed dense rewards with contribution-aware gradient weighting.

**Multi-party training-free systems**: G-Memory [cite] proposed three-tier graph memory for multi-agent collaboration. CollaborativeMem [cite] introduced private/shared memory with provenance tracking. Neither is trained with RL.

### 2.2 Multi-Party Conversation Benchmarks

GroupMemBench [cite], EverMemBench [cite], and SocialMemBench [cite] have established rigorous benchmarks for multi-party memory evaluation. LoCoMo [cite] and LongMemEval [cite] cover dyadic settings. PersonaMem-v2 [cite] focuses on persona consistency.

### 2.3 Memory Failure Analysis

MemFail [cite] systematically characterizes five failure modes in existing memory systems. SocialMemBench [cite] identifies five group-setting failure patterns. These analyses motivate the need for architectures specifically designed for multi-party settings.

### 2.4 Memory Safety and Privacy

Temporal memory contamination [cite: Remembering More], evolving memory governance [cite: SSGM], and privacy risks [cite: Unveiling Privacy] highlight safety challenges in memory-equipped LLMs that are amplified in multi-party settings.

---

## 3. Problem Formulation（草稿）

### 3.1 Multi-Party Conversation Memory Task

**Input**: A multi-party conversation session $S_t = \{(u_i, p_i, s_i)\}_{i=1}^{T}$, where $u_i$ is utterance $i$, $p_i$ is its speaker ID, and $s_i$ is its audience set. The agent also receives a memory state $M_{t-1}$ from the previous session.

**Output**: (1) Updated memory state $M_t$; (2) Responses to queries $Q_t$ about speakers' information, intentions, or relationships.

**Memory state**: $M_t = \{M_s\}_{s \in \mathcal{P}} \cup M_G$, where:
- $M_s = \{M_s^{\text{core}}, M_s^{\text{epi}}, M_s^{\text{sem}}, M_s^{\text{ins}}\}$ is speaker $s$'s four-dimensional memory
- $M_G = \{M_G^{\text{inter}}, M_G^{\text{ins}}\}$ is the group-level memory

**Evaluation**: Three properties from GroupMemBench:
1. **Speaker Attribution F1**: Fraction of facts correctly attributed to their originating speaker
2. **Audience Adaptation Score**: Quality of response adaptation to intended audience
3. **Group Dynamics Recall**: Retention of group-level interaction patterns

### 3.2 Memory Agent Policy

The memory agent learns a policy $\pi_\theta(a_t | c_t, M_{t-1})$ where:
- $c_t$ is the current conversation context (recent utterances)
- $a_t \in \mathcal{A}$ is a memory action (WRITE, UPDATE, DELETE, SUMMARY, PROMOTE, SUPPRESS, QUARANTINE, READ_CROSS, NOOP)
- $M_t = f(M_{t-1}, a_t)$ is the deterministic memory transition function

The policy is trained to maximize expected reward:
$$J(\theta) = \mathbb{E}_{\tau \sim \pi_\theta} \left[ R(\tau, M_T, Q, G) \right]$$

where $G$ is the ground truth memory state and $Q$ are evaluation queries.

---

## 4. Method（SpeakerMem-R1）— 关键章节 Outline

### 4.1 Speaker-Structured Memory Architecture
- 20-dim 记忆矩阵图示
- MemoryFragment 数据结构
- Audience-aware access control

### 4.2 Speaker-Aware Levenshtein Dense Reward (SpeakerLev)
- DeltaMem 公式回顾
- 扩展到 per-speaker
- Cross-speaker leakage penalty
- 完整 reward 函数（8 个组件）

### 4.3 Speaker-Conditioned LoGo-GRPO
- Memory-R2 LoGo-GRPO 回顾
- Speaker partition stratification
- Local + global 组合

### 4.4 Contribution-Aware Speaker Gradient Weighting
- MemBuilder attribution 回顾
- Speaker-aware 扩展
- 训练稳定性分析

### 4.5 Three-Stage Training Curriculum
- Stage 1: Speaker-Aware SFT
- Stage 2: Joint Multi-Agent RL
- Stage 3: End-to-End Task RL

---

## 5. Experiments — 实验设计 Outline

### 5.1 Benchmarks
- GroupMemBench（三维：attribution + audience + group dynamics）
- EverMemBench（2,400 QA，三维：recall + awareness + profile）
- SocialMemBench（1,031 QA，9 类，5 个 archetype）
- LoCoMo（迁移测试，保证 dyadic 能力不退化）

### 5.2 Baselines（8 个）
见 V3 spec Part 2.7 表格

### 5.3 Metrics
- Token-level F1（主要 QA 指标）
- Speaker Attribution F1（新指标，核心贡献之一）
- Audience Adaptation Score
- Privacy Leakage Rate（安全指标）

### 5.4 消融（6 项）
见 V3 spec Part 2.6

### 5.5 Analysis
- BM25 强的原因分析（为什么 retrieval 不是瓶颈）
- RL 训练收敛曲线
- Speaker 数量的影响（3/5/10 speaker）
- Group size 的影响（来自 SocialMemBench 的 4-30 人设置）

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
2. **EverMemBench 的 "用户画像理解" 任务** 是否等价于我们的 speaker profile 评测——需要对齐
3. **MemBuilder-4B 的 baseline 代码**：是否开源？需要联系作者或重新实现
4. **计算资源**：7B 模型 + 4 × A100 + G=4 rollout，估算训练时间 ~2 天/轮，总计 ~10 轮 = 20 天
