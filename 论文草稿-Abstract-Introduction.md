# SpeakerMem-R1 论文草稿：Abstract + Introduction

**版本**：v1.0（2026-06-02，V4 迭代产出）  
**目标**：AAAI 2027 投稿（预计截止 2027 年 7-8 月）  
**状态**：草稿，用于确立 story 和 framing，实验数字待填

---

## Abstract（180-200 词）

Multi-party conversations — involving three or more participants — are ubiquitous in modern group chats, team collaborations, and social networks. Yet existing long-term memory systems for conversational AI are designed almost exclusively for **dyadic (two-party) settings**, leaving a critical gap in managing "who-said-what-to-whom" across multiple speakers. 

In this paper, we introduce **SpeakerMem-R1**, the first reinforcement learning framework for **speaker-grounded memory management** in multi-party conversations. At the core of our approach is the insight that *speaker-attributed fact extraction* — correctly associating facts with their source speakers — is the fundamental bottleneck in group memory (validated by Memory-R2's ablation showing F1 collapses from 49.67 to 28.30 when removing the fact extractor). 

SpeakerMem-R1 addresses this through: (1) a **five-layer speaker-indexed memory structure** explicitly encoding who knows what; (2) a **speaker-aware Levenshtein reward** (SpeakerLevenshtein) that measures per-speaker memory state alignment as a dense process signal; and (3) a **speaker-conditioned LoGo-GRPO** training algorithm combining local speaker-stratified rerollouts with global trajectory optimization. 

Evaluated on three multi-party benchmarks — GroupMemBench, EverMemBench, and SocialMemBench — SpeakerMem-R1 achieves **XX%/XX%/XX%** improvements over the strongest baselines (BM25, Mem0, Memory-R2), while maintaining competitive performance on dyadic benchmarks (LoCoMo). Our code and synthesized multi-party training data will be publicly released.

---

## 1. Introduction（约 900 词，5 段）

### 段落 1：动机与场景（群聊 AI 的必要性）

Real-world human communication is fundamentally multi-party. Whether in workplace team chats, family group messages, or online interest communities, conversations routinely involve three to ten or more participants, each bringing their own knowledge, preferences, relationships, and communication styles. An effective AI assistant for such settings must maintain a structured, long-term memory that tracks not only what was said, but **who said it, to whom, and in what relational context**. This capability — speaker-grounded memory — is prerequisites for any AI system operating in modern group environments, from enterprise collaboration tools to social AI companions.

### 段落 2：现有工作的局限（dyadic 偏见）

Despite the prevalence of multi-party settings, existing memory systems for conversational AI exhibit a systematic bias toward dyadic (two-party, user-assistant) interactions. Training-free systems such as Mem0 [cite], A-MEM [cite], and MemoryBank [cite] represent dialogue history as a flat fact store without speaker attribution. More recent reinforcement learning (RL) approaches — Memory-R1 [cite], AgeMem [cite], DeltaMem [cite], Memory-R2 [cite], and CoMAM [cite] — train memory agents to manage long-term context, achieving impressive results on dyadic benchmarks like LoCoMo [cite] and PersonaMem [cite]. However, **all existing RL memory methods operate exclusively in dyadic settings**: they cannot distinguish "Alice said X" from "Bob said X about Alice", nor can they manage the privacy boundaries, audience adaptation, and cross-speaker attribution that are essential in group conversations.

This limitation is not merely a matter of scale. GroupMemBench [cite] identifies **six categories of failures** specific to multi-party memory, with state-of-the-art systems achieving only 46.0% accuracy and knowledge-update categories falling to 27.1%. SocialMemBench [cite] documents **five structural failure modes** — including single-stream conflation (treating "Alice mentions Bob's preference" as Alice's preference) and cross-persona knowledge gaps — that arise specifically from the lack of speaker grounding. Strikingly, BM25 lexical retrieval matches or exceeds complex agent memory systems on these benchmarks, suggesting that the bottleneck lies in **memory writing and organization quality**, not retrieval.

### 段落 3：我们的方案（技术概述）

We present **SpeakerMem-R1**, the first RL training framework specifically designed for speaker-grounded multi-party memory. Our approach is motivated by three key insights from the recent dyadic RL memory literature:

**(I) Fact Extraction is the Bottleneck.** Memory-R2 [cite] demonstrates that removing the fact extractor collapses end-to-end F1 from 49.67 to 28.30 — a catastrophic degradation. In multi-party conversations, fact attribution is inherently ambiguous ("Alice reports that Bob is interested in NLP" — whose fact is this?). We introduce a **Speaker-Attributed Fact Extractor** that explicitly assigns each extracted fact to its source speaker, trained via speaker-masked supervised fine-tuning before RL.

**(II) Dense State Reward with Speaker Awareness.** DeltaMem [cite] shows that rewarding memory state transitions (rather than just final QA answers) dramatically improves convergence. We extend this to the multi-party setting with **SpeakerLevenshtein**, a speaker-bucketed Levenshtein reward that computes per-speaker memory state alignment and adds a cross-speaker leakage penalty for attribution errors.

**(III) Fair Credit Assignment Across Speakers.** Memory-R2 [cite] identifies that diverging memory states across rollouts violate GRPO's group-relative assumption. In multi-party settings, this is amplified by K-fold branching (one per speaker). We introduce **Speaker-Conditioned LoGo-GRPO**, which stratifies local rerollouts by active speaker set, ensuring fair credit comparison within identical speaker contexts.

These three contributions are integrated in a three-stage training pipeline with a five-layer speaker-indexed memory structure and a joint multi-agent RL objective (inspired by CoMAM [cite]).

### 段落 4：实验结果（数字待填）

We evaluate SpeakerMem-R1 on three multi-party benchmarks: **GroupMemBench** [cite] (six-category group memory evaluation), **EverMemBench** [cite] (long-horizon workplace collaborative dialogues with 51,023 turns), and **SocialMemBench** [cite] (social group settings with five documented failure modes). We additionally test on dyadic benchmarks (LoCoMo [cite]) to confirm no regression on existing settings.

SpeakerMem-R1 achieves consistent improvements over baselines including BM25, Mem0, Memory-R1, AgeMem, DeltaMem, Memory-R2, and CoMAM adapted for multi-party evaluation. Ablation studies confirm the contribution of each component: speaker-attributed extraction (+XX F1), SpeakerLevenshtein reward (+XX F1), speaker-conditioned LoGo (+XX F1), and five-layer memory structure (+XX F1). Case studies illustrate how SpeakerMem-R1 correctly handles attribution-ambiguous facts, privacy-sensitive cross-speaker queries, and long-horizon temporal reasoning across multiple speakers.

### 段落 5：贡献总结

We summarize our contributions as:
1. **Setting**: We formalize the multi-party speaker-grounded memory management problem and establish the first RL training paradigm for this setting.
2. **Method (Extraction)**: A Speaker-Attributed Fact Extractor with speaker-masked SFT that directly addresses the primary failure mode identified by Memory-R2's ablation.
3. **Method (Reward)**: SpeakerLevenshtein, a speaker-bucketed dense memory state reward with cross-speaker leakage penalty.
4. **Method (Training)**: Speaker-Conditioned LoGo-GRPO, extending Memory-R2's fair credit assignment to the K-speaker multi-party setting.
5. **Resources**: 200 synthesized multi-party training dialogues across diverse social contexts, to be publicly released to facilitate future research.

---

## 写作注意事项（给自己的提醒）

### 需要补充的实验数字
- GroupMemBench: our F1 vs BM25 (基准 ~46%) vs Mem0 vs Memory-R2 adapted
- EverMemBench: our accuracy vs oracle (~26%) vs baselines
- SocialMemBench: our score vs Gemini 2.5 Flash (0.721) vs Mem0 (0.12-0.18)
- LoCoMo: 应该接近 Memory-R2 的 49.67 F1

### Related Work 需要覆盖的论文

**Memory-augmented LLM agents（Training-free）**：
- Mem0, A-MEM, MemoryBank, G-Memory, Collaborative Memory

**RL for Memory**：
- Memory-R1, AgeMem, Mem-α, MEM1, MemSearcher, DeltaMem, Memory-R2, CoMAM

**Multi-party dialogue understanding**：
- MuPaS, SA-LLM, SHARE, MOOM

**Memory benchmarks**：
- GroupMemBench, EverMemBench, SocialMemBench, LOCOMO, PersonaMem-v2

### 关键数字备忘（写作时直接用）

| 数字 | 含义 | 来源 |
|-----|------|------|
| 46.0% | GroupMemBench 最强系统准确率 | GroupMemBench |
| 27.1% | GroupMemBench 知识更新类 | GroupMemBench |
| ~26% | EverMemBench Oracle 多跳归因 | EverMemBench |
| 0.721 | SocialMemBench Gemini 2.5 全上下文 | SocialMemBench |
| 0.12-0.18 | SocialMemBench 开源框架分数 | SocialMemBench |
| 49.67→28.30 | Memory-R2 去掉 Fact Extractor 后 F1 崩塌 | Memory-R2 消融 |
| 8.5-16.7% | CoMAM 比 sequential Memory-R1 的提升 | CoMAM |

---

## V4 草稿修订计划

### 需要在 V4 验证的核心论点

1. **"BM25 在多方 benchmark 上与 agent 系统相当"** → 需要实验数字确认
2. **"speaker-attributed extraction 是命脉"** → 需要我们自己的消融数字
3. **"multi-party benchmark 上无任何 RL 论文"** → 需要更完整的文献搜索

### 审稿人可能的质疑 + 预备回应

| 质疑 | 预备回应 |
|-----|---------|
| "只是把 dyadic 扩展到 multi-party，incremental" | 5 类失败模式（SocialMemBench）证明多方是质变，不是量变 |
| "没有真实多方训练数据，合成数据偏差大" | 合成数据多样场景（4 类）+ 验证 pipeline + 在真实评测集上评估 |
| "Memory-R2/CoMAM 可以直接扩展到多方" | 它们都无代码，且均假设单用户 MDP，speaker conditioning 是非平凡扩展 |
| "GroupMemBench 测试集太小" | 还有 EverMemBench（2,400 QA）和 SocialMemBench（1,031 QA）|
| "消融不够清晰" | 7 项精心设计的消融（见方法 spec §7.4）|

---

*草稿版本 v1.0 | 2026-06-02 | V4 迭代产出*
