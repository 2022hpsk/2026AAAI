# SpeakerMem-R1 论文草稿：Method 章节

**版本**：v1.0（2026-06-02，V5 迭代产出）  
**状态**：草稿，供写作参考和技术审查

---

## 3. Method

### 3.1 Problem Formulation

**Multi-Party Memory Management.** 
We consider a conversation $C = \{(s_t, u_t)\}_{t=1}^T$ with $K$ speakers $S = \{s_1, \ldots, s_K\}$, where each utterance $u_t$ is attributed to speaker $s_t$. Given a query $q = (s_\text{ask}, s_\text{target}, q_\text{text})$ — specifying the asker, the target subject, and the question text — a memory agent must maintain a speaker-indexed memory structure $M$ and retrieve relevant information to answer $q$.

The core challenges absent in dyadic settings are:

**(1) Speaker Attribution:** Each memory fact $f$ must be associated with its source speaker: $f = (\text{content}, s_\text{owner})$. In dyadic settings, the owner is always the single counterpart; in multi-party settings, attribution is ambiguous when multiple speakers discuss the same entity.

**(2) Audience Adaptation:** Answering $q$ requires considering the asker $s_\text{ask}$'s perspective, relationship with $s_\text{target}$, and access permissions.

**(3) Cross-Speaker Privacy:** Information owned by $s_i$ may not be accessible to $s_j$, requiring explicit access control in the memory structure.

---

### 3.2 Five-Layer Speaker-Indexed Memory

We introduce a structured memory architecture that makes speaker grounding a first-class design principle:

$$M = \{M_\text{core}^s, M_\text{episodic}^s, M_\text{profile}^s\}_{s \in S} \cup \{M_\text{interact}, M_\text{insight}\}$$

The five layers serve distinct purposes:

| Layer | Scope | Content Type | Example |
|-------|-------|-------------|---------|
| $M_\text{core}^s$ | per-speaker | Persistent facts | "Alice works at ByteDance" |
| $M_\text{episodic}^s$ | per-speaker | Time-indexed episodes | "Alice mentioned job change (turn 42)" |
| $M_\text{profile}^s$ | per-speaker | Communication style, preferences | "Bob uses formal English" |
| $M_\text{interact}$ | group | Cross-speaker events, relationships | "Alice and Bob have worked together" |
| $M_\text{insight}$ | group | High-level meta-knowledge | "This group focuses on AI startups" |

Each entry $e \in M_\text{core}^s$ is a tuple $(s_\text{owner}, \text{content}, A_e, l_e, t_e)$ where $A_e \subseteq S$ is the audience set (access control), $l_e$ is the layer, and $t_e$ is the creation turn.

This layered structure directly addresses the five failure modes documented in SocialMemBench [cite]:
- **Single-stream conflation** → $M_\text{core}^s$ ensures facts stay speaker-attributed
- **Temporal-state overwrite** → $M_\text{episodic}^s$ preserves time-indexed versions
- **Entity merging** → unique $s_\text{owner}$ prevents persona conflation
- **Cross-persona knowledge gap** → $M_\text{interact}$ tracks cross-speaker relationships
- **Norm-individual conflation** → $M_\text{insight}$ (norms) separated from $M_\text{core}^s$ (individuals)

---

### 3.3 Speaker-Attributed Action Space

Building on AgeMem's [cite] observation that memory operations should be modeled as learnable discrete actions, we extend the action space to include speaker grounding as mandatory metadata:

$$\mathcal{A} = \{\texttt{WRITE}(c, s, A, l),\ \texttt{UPDATE}(e, c),\ \texttt{DELETE}(e),\ \texttt{SUMMARY}(E, l),\ \texttt{PROMOTE}(e),\ \texttt{SUPPRESS}(e, \lambda),\ \texttt{READ}(s, s'),\ \texttt{NOOP}\}$$

where $c$ is content, $s$ is speaker owner, $A$ is audience set, $l$ is target layer, $e$ is an entry ID, and $s'$ is a target speaker for cross-speaker access.

This is fundamentally different from dyadic memory action spaces (Memory-R1 [cite], AgeMem [cite], DeltaMem [cite]) where actions lack speaker conditioning. The speaker metadata enables the reward functions described next.

---

### 3.4 Speaker-Aware Levenshtein Reward (SpeakerLevenshtein)

Motivated by DeltaMem's [cite] insight that rewarding memory state transitions yields denser training signal than final answer correctness, we introduce SpeakerLevenshtein, a speaker-bucketed extension for multi-party settings.

**Per-Speaker State Diff.** At each turn $t$, we compute the delta between the predicted and ground-truth memory states for each speaker separately:

$$\Delta^s_\text{pred} = M^s_t - M^s_{t-1}, \quad \Delta^s_\text{gt} = M^{s,*}_t - M^{s,*}_{t-1}$$

**Speaker-Bucketed F1.** For each speaker $s$, we compute a Levenshtein F1:

$$\text{LevF1}^s = \frac{2 \cdot \text{SP}^s \cdot \text{SR}^s}{\text{SP}^s + \text{SR}^s}$$

where the soft precision $\text{SP}^s$ and recall $\text{SR}^s$ are computed via optimal transport matching (Hungarian algorithm) on the embedding cosine similarity matrix of $\Delta^s_\text{pred}$ and $\Delta^s_\text{gt}$, filtered by threshold $\tau$, augmented with lexical fidelity (following DeltaMem [cite]):

$$\text{Sim}(f_i, f_j) = \text{cos}(\mathbf{e}_i, \mathbf{e}_j) \cdot \left(1 + 0.2 \cdot \text{KeyCov}(f_i, f_j)\right)$$

**Cross-Speaker Leakage Penalty.** To penalize attribution errors (Alice's fact appearing in Bob's bucket):

$$R_\text{leak} = -\frac{1}{N} \sum_{s \in S} \sum_{f \in M^s_t} \mathbb{1}[\text{TrueOwner}(f) \neq s]$$

**Total State Reward:**

$$R_\text{state} = \underbrace{\frac{1}{K} \sum_{s=1}^K \text{LevF1}^s}_{\text{per-speaker avg}} + \underbrace{\mu \cdot \min_s \text{LevF1}^s}_{\text{worst-speaker bonus}} + R_\text{leak}$$

The worst-speaker bonus $\mu \cdot \min_s \text{LevF1}^s$ prevents the agent from "giving up" on harder speakers.

**Why per-speaker bucketing is non-trivial.** A naïve extension would concatenate all facts across speakers and apply DeltaMem's Levenshtein reward globally. This approach fails for two distinct reasons:

*(1) Attribution-content conflation.* Global Levenshtein assigns the same penalty to a factual error ("Alice works at Google" when ground truth is "ByteDance") and an attribution error ("Alice works at ByteDance" stored in Bob's bucket). These represent fundamentally different failure modes: factual errors indicate information loss, while attribution errors indicate cross-speaker contamination. Conflating them prevents the agent from learning which failure to prioritize.

*(2) Speaker imbalance.* Averaging over speakers allows the agent to succeed on K-1 easy speakers while ignoring the hardest. Attribution difficulty is highly uneven on GroupMemBench — speakers with many cross-references face substantially harder attribution than peripheral members. Our worst-speaker bonus $\mu \cdot \min_s \text{LevF1}^s$ prevents this degeneracy.

On GroupMemBench, attribution errors are the primary failure mode (27.1% on knowledge-update, 37.7% on term-ambiguity). DeltaMem's flat Levenshtein reward cannot distinguish "Alice's fact in Bob's bucket" from "correct fact in correct bucket," whereas SpeakerLevenshtein explicitly penalizes such cross-speaker contamination via separate per-speaker computation.

---

### 3.5 Speaker-Conditioned LoGo-GRPO

**Motivation.** Memory-R2 [cite] identifies that across rollouts, diverging memory states violate GRPO's group-relative comparison assumption, and proposes LoGo-GRPO with local rerollouts from shared intermediate states. In multi-party settings, this problem is amplified K-fold: different rollouts may have not only different memory states but also different active speaker compositions, rendering global group comparison doubly invalid.

**Why speaker-conditioning is a logical necessity, not a convenience.** Memory-R2's LoGo-GRPO ensures comparable starting memory states; in multi-party settings, comparability also requires *identical speaker compositions*, since memory operation strategies fundamentally differ between "a turn where only Alice speaks" and "a turn where Alice and Bob speak simultaneously about each other." Without speaker conditioning, two local rollouts may process turns with different active speakers — rendering the within-group comparison as unfair as the global comparison. Speaker-conditioned rerollouts are thus not an optional refinement but a prerequisite for valid local credit assignment in multi-party RL.

**Speaker-Conditioned Local Rerollout.** We extend LoGo-GRPO with speaker stratification. At each intermediate checkpoint $m$ in the global trajectory, we condition local rerollouts on the active speaker set:

$$\mathcal{T}_\text{local}^m = \{r_1, \ldots, r_G\} \text{ from } (M_m, C_{t:}, \text{speakers}(C_{t:}))$$

All $G$ local rollouts share the same intermediate memory state $M_m$ AND the same active speaker set, ensuring fair comparison within identical contexts.

**Per-Speaker Adaptive Credit.** Inspired by CoMAM's [cite] rank-consistency credit assignment, we compute per-speaker credit weights $\alpha_s$ based on how well each speaker's local reward aligns with the global reward:

$$\alpha_s = \text{normalize}(\text{SpearmanCorr}(R_\text{local}^s, R_\text{global}))$$

This ensures that speakers whose memory operations contribute more to the final answer receive proportionally more gradient signal.

**Combined Objective:**

$$\mathcal{L}_\text{total} = \mathcal{L}_\text{global} + \lambda \cdot \mathcal{L}_\text{local} + \beta \cdot \mathcal{L}_\text{KL}$$

where $\mathcal{L}_\text{global}$ is the standard GRPO loss over full trajectories, $\mathcal{L}_\text{local}$ is the LoGo local loss over speaker-conditioned rerollouts, and $\mathcal{L}_\text{KL}$ is a KL regularization term (following WebAgent-R1 [cite]) to prevent the "Echo Trap."

---

### 3.6 Complete Reward Function

The full reward signal combines task-level and process-level signals:

$$R = \underbrace{0.5 \cdot R_\text{task}}_{\text{outcome}} + \underbrace{0.8 \cdot R_\text{state}}_{\text{dense process}} + \underbrace{0.3 \cdot R_\text{attr}}_{\text{attribution}} + \underbrace{0.2 \cdot R_\text{aud}}_{\text{audience}} + \underbrace{0.1 \cdot R_\text{compr} + 0.1 \cdot R_\text{RIF}}_{\text{structure}}$$

where:
- $R_\text{task}$: token-level F1 between model answer and ground truth (following [cite] which shows binary EM yields zero gradient at $G=4$)
- $R_\text{state}$: SpeakerLevenshtein (§3.4), weighted 0.8 as the dominant signal (following DeltaMem [cite])
- $R_\text{attr}$: speaker attribution accuracy (fraction of facts correctly attributed to source speaker)
- $R_\text{aud}$: audience adaptation score (whether the answer appropriately adapts to the asker)
- $R_\text{compr}$: memory compression ratio reward (following Mem-α [cite])
- $R_\text{RIF}$: forgetting appropriateness (following MOOM [cite])

The dominant role of $R_\text{state}$ (weight 0.8) reflects DeltaMem's empirical finding that dense process rewards accelerate convergence more than outcome rewards [cite].

---

### 3.7 Three-Stage Training Pipeline

**Stage 1: Speaker-Attributed SFT.** We first perform supervised fine-tuning on 200 synthesized multi-party dialogues (§4.3) with speaker-masked cross-entropy loss to teach the model the speaker-attributed memory operation format. This warm-start is critical: Memory-R2 [cite]'s ablation shows that RL without a strong initialization yields F1 drop from 49.67 to 28.30 when the fact extractor is undertrained.

**Stage 2: Joint RL with Speaker-Conditioned LoGo.** We train all agents jointly (construction + retrieval + answer, sharing one backbone following Memory-R2 [cite]) using our SpeakerMem-GRPO objective. We adopt a curriculum that progressively increases speaker count and session length:

$$\text{Stage 2: } K=3, N_\text{sess}=8 \to K=5, N_\text{sess}=16 \to K=8, N_\text{sess}=32$$

inspired by Memory-R2's curriculum design [cite] and extended along the speaker dimension.

**Stage 3: End-to-End Multi-Benchmark Fine-tune.** We finish with mixed-curriculum training on GroupMemBench, EverMemBench, and SocialMemBench evaluation data (with train-test split from our synthesized curriculum), following MemSearcher's [cite] multi-context GRPO paradigm to prevent single-benchmark overfitting.

---

### 3.8 Connection to Existing Work

Table 1 summarizes how SpeakerMem-R1 extends prior methods:

| Component | Inspired By | Our Extension |
|-----------|------------|---------------|
| Dense state reward | DeltaMem [cite] | Per-speaker bucketed Levenshtein |
| Local rerollout | Memory-R2 [cite] | Speaker-conditioned stratification |
| Joint training | CoMAM [cite] | Per-speaker adaptive credit |
| Step-wise credit | AgeMem [cite] | K-fold speaker dimension |
| Process reward | Mem-α [cite] | Multi-component multi-party reward |
| Forgetting | MOOM [cite] | SUPPRESS action in speaker-indexed memory |

---

## 写作技术备注

### §3.4 SpeakerLevenshtein 的 novelty 论证

在写作中必须清晰表达为什么 per-speaker bucketing 不是 trivial：

> "A naïve extension would simply concatenate all facts across speakers and apply DeltaMem's Levenshtein reward globally. This fails for two reasons: (1) it conflates attribution errors (a fact in the wrong speaker bucket) with factual errors (wrong fact content), both penalized identically; (2) it averages over speakers, allowing the model to succeed on easy speakers (K-1) while ignoring hard ones. SpeakerLevenshtein addresses both by computing per-speaker deltas and adding a worst-speaker bonus."

### §3.5 Speaker-conditioned LoGo 的 novelty 论证

> "Memory-R2's LoGo-GRPO ensures comparable starting states; in multi-party settings, comparability also requires identical speaker compositions, since memory operation strategies fundamentally differ between 'turn where only Alice speaks' and 'turn where Alice and Bob speak simultaneously about each other.' Speaker-conditioned rerollouts are thus not merely a convenience but a logical necessity."

### §3.7 课程设计的 novelty 论证

> "Prior curriculum designs for memory RL (Memory-R2 [cite]) increase session count from 8 to 32. We augment this with a speaker-count dimension (K=3→5→8), reflecting the progressive difficulty of multi-party attribution: 3-speaker conversations have unambiguous attribution in ~85% of facts, while 8-speaker conversations reduce this to ~40% (measured on our synthesized corpus). The 2D curriculum (session length × speaker count) is novel to multi-party memory RL."

---

*草稿版本 v1.0 | 2026-06-02 | V5 迭代产出*
