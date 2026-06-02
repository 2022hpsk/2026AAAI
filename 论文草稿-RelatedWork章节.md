# SpeakerMem-R1 论文草稿：Related Work 章节

**版本**：v1.0（2026-06-02，V5 迭代产出）

---

## 2. Related Work

### 2.1 Memory-Augmented LLM Agents (Training-Free)

Early approaches to persistent memory in conversational AI relied on heuristic pipelines. MemoryBank [cite] simulates Ebbinghaus forgetting curves to prioritize important memories for retrieval. Mem0 [cite] implements CRUD (Create/Read/Update/Delete) operations on a structured memory store with rule-based importance scoring. A-MEM [cite] extends this with atomic note creation and graph-based memory organization. These training-free methods achieve competitive performance on dyadic benchmarks like LoCoMo [cite], and BM25 retrieval even matches or outperforms them on multi-party settings (GroupMemBench [cite]), suggesting their fundamental limitation is not retrieval quality but memory organization — particularly speaker attribution in multi-party conversations.

More recently, G-Memory [cite] and Collaborative Memory [cite] extend memory to multi-agent settings with graph structures and provenance tracking. These methods address the structural side of multi-party memory but do not learn memory policies from reward signals.

### 2.2 Reinforcement Learning for Memory Management

The paradigm of training memory agents via RL was introduced by Memory-R1 [cite], which separates memory management into a Construction Agent (ADD/UPDATE/DELETE/NOOP) and an Answer Agent (memory distillation + QA), both trained via GRPO. This established the benchmark of 43.14 F1 on LoCoMo, setting the standard for subsequent work.

Several works have substantially improved upon Memory-R1. AgeMem [cite] unifies LTM and STM management into a single policy with a six-action space, and introduces *step-wise GRPO* that distributes credit across sub-trajectory steps, achieving strong performance through three-stage curriculum training. Mem-α [cite] introduces a three-component architecture with parametric compression. MEM1 [cite] proposes masked trajectory training for long-horizon memory. MemSearcher [cite] extends the paradigm to search agents with multi-context GRPO.

**Dense Reward for Memory RL.** Memory-R1's sparse outcome reward (answer correctness only) was identified as a key bottleneck. DeltaMem [cite] addresses this by proposing Memory-based Levenshtein Distance as a dense process reward: at each turn, predicted memory state changes are compared to ground-truth changes via optimal transport over embedded fact sets. Evaluated on Qwen3-8B, DeltaMem substantially outperforms Memory-R1 on LoCoMo, PersonaMem, and HaluMem. However, DeltaMem treats all facts uniformly regardless of their source speaker — a design choice that is benign in dyadic settings but problematic in multi-party conversations where attribution ambiguity is central.

**Credit Assignment in Memory RL.** Memory-R2 [cite] identifies a fundamental problem in long-horizon memory RL: across G rollouts, diverging memory states violate GRPO's group-relative comparison assumption. LoGo-GRPO resolves this via local rerollouts from shared intermediate states, improving F1 from Memory-R1's 43.14 to Memory-R2's 50.60 on combined benchmarks. Mem-T [cite] takes an orthogonal approach via tree-of-memory formulations, where sibling branches from the same decision node enable local group comparison at every step.

**Joint Multi-Agent Training.** CoMAM [cite] formalizes the memory pipeline as a joint sequential MDP and trains all agents (Extraction, Profile, Retrieval) end-to-end via GRPO with adaptive credit assignment based on rank consistency between local and global rewards. This achieves 8.5-16.7% gains over sequentially-trained Memory-R1.

**Inference-Time Experience Refinement.** R²-Mem [cite] proposes reflective experience refinement as an inference-time augmentation layer over GRPO-trained memory agents. When a memory search fails, the agent reflects on the failure cause and writes a refined search strategy to a dedicated reflective memory store, achieving 22.6% F1 improvement and 12.9% token reduction on LoCoMo. This addresses *search strategy* failures in dyadic settings but does not model speaker attribution — the primary failure mode in multi-party conversations.

**Key Gap.** All RL-based memory methods cited above operate in *dyadic* settings (single user + single assistant). Their action spaces lack speaker attribution metadata, their reward signals do not distinguish cross-speaker attribution errors, and their training data (LoCoMo, PersonaMem) involves only one conversational partner. SpeakerMem-R1 is the first work to train RL memory agents in multi-party settings.

### 2.3 Multi-Party Dialogue Understanding

Multi-party dialogue has been studied in NLP primarily from the perspective of discourse analysis and information extraction. SA-LLM [cite] and SHARE [cite] address speaker-aware generation and response selection. MuPaS [cite] introduces role-masked pre-training for multi-party speaker modeling. MOOM [cite] studies forgetting mechanisms in multi-party settings. These works address the *understanding* side of multi-party dialogue but not the *memory management* side.

### 2.4 Multi-Party Memory Benchmarks

The emergence of dedicated multi-party memory benchmarks in early 2026 creates the evaluation infrastructure necessary for our work:

**GroupMemBench** [cite] evaluates six memory capabilities specific to group conversations: multi-hop reasoning, knowledge update, term ambiguity, user-implicit reasoning, temporal reasoning, and abstention. Its graph-grounded synthesis pipeline generates adversarially attributed questions where each query is bound to a specific asker — a design that tests speaker-aware memory retrieval directly.

**EverMemBench** [cite] simulates a year-long workplace with 170 employees across five projects, generating 51,023 turns (~4.2M tokens) and 2,400 QA pairs. The benchmark reveals that even oracle systems achieve only ~26% on multi-hop attribution tasks, establishing the extraordinary difficulty of multi-party long-horizon memory.

**SocialMemBench** [cite] covers five social group prototypes (close friends, family, recreational, interest community, acquaintance) at three scales (4-30 members), with 1,031 carefully human-verified QA pairs. Its systematic identification of five failure modes — single-stream conflation, temporal-state overwrite, entity merging at scale, missing cross-persona knowledge, and norm-individual conflation — provides a diagnostic vocabulary for multi-party memory system design.

Together, these benchmarks confirm that existing memory systems fail systematically in multi-party settings and establish the evaluation targets for our work. We are the first to develop RL-trained methods evaluated on all three benchmarks.

### 2.5 Curriculum Learning for Memory RL

A recent empirical study [cite] systematically examines how training data composition affects RL memory agent specialization. Key findings: (1) binary exact-match reward yields zero gradient at $G=4$ — token-level F1 is necessary; (2) 150 training samples is the "specialization vs aggregate improvement" inflection point; (3) mixed curriculum across multiple benchmarks outperforms single-benchmark training. We adopt all three lessons in SpeakerMem-R1's training design.

---

## 写作备注

### Related Work 的位置策略

1. **Dyadic RL memory 篇幅要充分**（§2.2），因为这是我们最直接的对话对象，审稿人来自这个社区
2. **Multi-party benchmark 要详细介绍**（§2.4），但要强调"只有 benchmark，没有 method paper"
3. **结尾的 "Key Gap" 句子**是整个 Related Work 最重要的句子，要写得清晰有力

### 关键定位句（用于全文）

> "To the best of our knowledge, SpeakerMem-R1 is the first reinforcement learning framework for memory management in multi-party conversations. All prior RL memory works operate in dyadic settings; all prior multi-party memory works are training-free or evaluation-only."

这句话需要反复确认：截至 2026/6/2，多方 RL memory 零篇，这个说法是准确的。

---

*草稿版本 v1.0 | 2026-06-02 | V5 迭代产出*
