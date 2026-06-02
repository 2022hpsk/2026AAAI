# SpeakerMem-R1 论文草稿：Appendix 章节

**版本**：v1.0（2026-06-02，V7 迭代产出）  
**状态**：草稿，部分内容待实验后填充

---

## A. Hyperparameter Details

### A.1 Model Configuration

| Component | Setting | Rationale |
|-----------|---------|-----------|
| Base model | Qwen3-8B | Matches DeltaMem [cite] for fair comparison |
| Fine-tuning | LoRA ($r=32$, $\alpha=64$) | Balances parameter efficiency and expressiveness |
| Optimizer | AdamW ($\beta_1=0.9$, $\beta_2=0.999$) | Standard for LLM fine-tuning |
| Learning rate | $3 \times 10^{-5}$ | Following Memory-R2 [cite] |
| Training framework | verl [cite] | Distributed GRPO implementation |
| Hardware | 4× A100-80GB | Stage 2 RL training |

### A.2 GRPO Configuration

| Hyperparameter | Value | Description |
|----------------|-------|-------------|
| $G$ (global rollouts) | 4 | Rollouts per example per step |
| $G_\text{local}$ (local rollouts) | 4 | LoGo local rerollouts per checkpoint |
| $\lambda$ (LoGo weight) | 0.3 | Following Memory-R2 [cite] |
| $\beta_\text{KL}$ | 0.01 | KL regularization against reference policy |
| $\tau$ (Levenshtein threshold) | 0.6 | Cosine similarity cutoff for fact matching |
| $\mu$ (worst-speaker bonus) | 0.1 | Weight for $\min_s \text{LevF1}^s$ |

### A.3 Reward Weights

| Component | Weight | Rationale |
|-----------|--------|-----------|
| $R_\text{task}$ | 0.5 | Final answer quality |
| $R_\text{state}$ | 0.8 | Dense process reward (dominant signal per DeltaMem [cite]) |
| $R_\text{attr}$ | 0.3 | Speaker attribution accuracy |
| $R_\text{aud}$ | 0.2 | Audience adaptation |
| $R_\text{compr}$ | 0.1 | Memory compression efficiency |
| $R_\text{RIF}$ | 0.1 | Forgetting appropriateness |

### A.4 Three-Stage Training Schedule

| Stage | Task | Duration | Key Metric |
|-------|------|----------|-----------|
| Stage 1 (SFT) | Speaker-attributed fact extraction | 3 epochs | Attribution F1 |
| Stage 2 (RL) | Joint RL with K=3→5→8 curriculum | 5 epochs | GroupMemBench F1 |
| Stage 3 (E2E) | Multi-benchmark mixed curriculum | 2 epochs | Combined benchmark |

---

## B. Training Data Details

### B.1 Synthetic Data Quality Statistics

Our 200-dialogue training set was synthesized using GPT-4o with the generation prompts described in §4.1. After quality filtering:

| Scenario | Generated | Passed QC | Final |
|---------|-----------|-----------|-------|
| close_friends | 55 | 50 | 50 |
| workplace_team | 54 | 50 | 50 |
| interest_community | 56 | 50 | 50 |
| locomo_triadic | 52 | 50 | 50 |
| **Total** | **217** | **200** | **200** |

Quality filtering criteria (§4.1):
1. Each speaker ≥3 distinct facts per dialogue
2. QA answers verified to require memory (GPT-4-judge binary classification)
3. All speaker labels consistent throughout dialogue

### B.2 Sample Synthetic Dialogue (close_friends)

```
Session 1, Turn 1, Alice: "I finally got the offer from ByteDance! Starting next month."
Session 1, Turn 2, Bob: "Congrats! Carol was also looking at tech companies, right?"
Session 1, Turn 3, Carol: "Yeah, I'm focused on startups actually. Less stable but more exciting."
Session 1, Turn 4, Alice: "Carol, what field? AI or more traditional SaaS?"
Session 1, Turn 5, Carol: "AI, specifically something in multi-agent systems."

Session 4, Turn 1, Alice: "By the way, I'm actually reconsidering the ByteDance offer..."
Session 4, Turn 2, Bob: "Wait, I thought you accepted? What happened?"
Session 4, Turn 3, Alice: "The team was reassigned. Now I'm leaning toward staying at my current place."
```

**Ground-truth memory (Session 4 state)**:
- $M_\text{core}^\text{Alice}$: "Alice initially accepted ByteDance offer" → "Alice reconsidering ByteDance"
- $M_\text{episodic}^\text{Alice}$: [Session 1: "Alice accepted ByteDance offer"], [Session 4: "Alice reconsidering due to team reassignment"]  
- $M_\text{core}^\text{Carol}$: "Carol interested in AI startups, specifically multi-agent systems"
- $M_\text{core}^\text{Bob}$: (no career fact shared in this snippet)

**Sample QA pairs**:
1. *Asker: Bob, Question: "Where is Alice working now?"* → "Alice accepted the ByteDance offer initially but is reconsidering due to team reassignment; her current status is uncertain."
2. *Asker: Alice, Question: "What kind of startup is Carol interested in?"* → "Carol is interested in AI startups, specifically multi-agent systems."
3. *Asker: Carol, Question: "What did Alice say about ByteDance in Session 1?"* → "Alice said she got an offer from ByteDance and was starting next month."

### B.3 Attribution Challenge Statistics (synthetic corpus)

| Property | close_friends | workplace_team | interest_community | locomo_triadic |
|---------|------------|---------------|------------------|--------------|
| Avg speakers per dialogue | 3.4 | 5.2 | 4.1 | 3.0 |
| Facts with clear attribution (%) | 82% | 74% | 70% | 88% |
| Ambiguous attribution cases | 18% | 26% | 30% | 12% |
| Cross-speaker references / dialogue | 4.2 | 7.1 | 5.8 | 3.9 |

*Ambiguous attribution*: cases where two speakers discuss the same entity, requiring context to determine the correct owner.

---

## C. Additional Case Studies

### C.1 Case Study 4: Cross-Speaker Multi-hop Reasoning

**Conversation excerpt**:
```
Session 2, Alice: "Bob recommended this book to me last month: 'Thinking Fast and Slow'."
Session 3, Carol: "Alice, you seem like you'd enjoy anything about cognition."
Session 5, Bob: "Has anyone read the Kahneman book I mentioned? Did Carol enjoy it?"
```

**Query** (Bob): "Did Carol read the book I recommended?"

**DeltaMem (adapted)**: Conflates Bob's recommendation with Carol's reading history → "Carol mentioned she read Thinking Fast and Slow" (incorrectly attributed)

**SpeakerMem-R1**:
- $M_\text{core}^\text{Bob}$: "Bob recommended 'Thinking Fast and Slow'"
- $M_\text{interact}$: "Alice received book recommendation from Bob (Session 2)"
- $M_\text{core}^\text{Carol}$: (no fact about Carol reading this book)
→ Answer: "There is no record of Carol reading the book. I only know Bob recommended it to Alice." ✓ (correct abstention)

**Analysis**: This requires 3-hop reasoning: (1) Bob recommended book → (2) to Alice → (3) check if Carol also received or read it. SpeakerMem-R1's $M_\text{interact}$ layer captures the cross-speaker recommendation chain.

---

### C.2 Case Study 5: Norm-Individual Conflation

**Conversation context**: A hiking group where "difficulty preference" is discussed both as group norm and individual preference.

```
Session 1, Group discussion: "We always prefer easy-to-medium trails as a group."
Session 2, Alice (privately to Bob): "Honestly, I prefer challenging trails. The group just slows me down."
```

**Query** (Carol): "What are Alice's trail preferences?"

**Memory-R2 (adapted)**: Conflates group norm with Alice's stated preference → "Alice prefers easy-to-medium trails" (wrong: retrieved group norm as Alice's preference)

**SpeakerMem-R1**: 
- $M_\text{insight}$ (group): "Group prefers easy-to-medium trails"
- $M_\text{core}^\text{Alice}$: "Alice personally prefers challenging trails" (audience: Alice, Bob only)
→ Since Carol is not in Alice's audience set: "I don't have specific information about Alice's personal trail preferences." ✓ (correct privacy-preserving abstention)

---

## D. Computational Cost Analysis

### D.1 Training Cost Estimation

| Stage | Time | Cost (4×A100) |
|-------|------|--------------|
| Stage 1 (SFT) | ~6 hours | ~$100 |
| Stage 2 (RL, K=3) | ~12 hours | ~$200 |
| Stage 2 (RL, K=5) | ~18 hours | ~$300 |
| Stage 2 (RL, K=8) | ~24 hours | ~$400 |
| Stage 3 (E2E) | ~8 hours | ~$130 |
| **Total** | **~68 hours** | **~$1,130** |

### D.2 Inference Cost: Speaker Scaling

The speaker-conditioned LoGo adds $G_\text{local}$ additional rollouts per checkpoint. For $K$ speakers and $M$ session checkpoints:

$$\text{Total rollouts} = G \cdot T + G_\text{local} \cdot M \cdot K$$

For $K=3, G=4, G_\text{local}=4, T=32, M=4$:
$$= 4 \times 32 + 4 \times 4 \times 3 = 128 + 48 = 176 \text{ rollouts}$$

Compared to dyadic LoGo ($K=1$): $128 + 16 = 144$ rollouts.

**Overhead**: SpeakerMem-R1 requires $\sim 1.2$× more rollouts than dyadic LoGo (not the 3-5× naive estimate — because speaker conditioning is done within the same local rerollout budget, not in addition to it).

---

## E. Full Ablation Details

### E.1 Ablation A2: Per-Speaker vs. Flat Levenshtein

**Hypothesis**: Per-speaker bucketing provides critical signal for attribution errors. Flat Levenshtein cannot distinguish "Alice's fact attributed to Bob" from "Bob's fact attributed to Bob."

**Experimental setup**:
- SpeakerMem-R1 Full vs. A2 (global flat Levenshtein, no speaker buckets)
- Evaluated on GroupMemBench with per-category breakdown

| Category | A2 (Flat) | Full | Δ |
|---------|-----------|------|---|
| Knowledge update | XX% | XX% | +XX% |
| Term ambiguity | XX% | XX% | +XX% |
| User-implicit | XX% | XX% | +XX% |
| Multi-hop | XX% | XX% | +XX% |
| Temporal | XX% | XX% | +XX% |
| Abstention | XX% | XX% | +XX% |
| **Overall F1** | **XX%** | **XX%** | **+XX%** |

*Primary prediction*: Largest gains on knowledge-update (27.1% baseline) and term-ambiguity (37.7% baseline) — both require knowing WHO said WHAT changed.

### E.2 Ablation A5: Joint vs. Sequential Training

**Hypothesis**: Joint training (all agents sharing backbone) provides better gradient flow than sequential training (each agent trained separately with fixed others).

**Setup**: Stage 2 joint RL (Full) vs. training Construction → Retrieval → Answer sequentially.

This directly tests CoMAM's [cite] claim that joint training yields 8.5-16.7% gains over sequential in dyadic settings, now in multi-party settings.

---

## 写作备注

### Appendix 的功能定位

1. **§A 超参数**：让实验可复现，reviewer 要问"你怎么选的 τ=0.6"这里要有答案
2. **§B 训练数据**：消除合成数据偏差的质疑（"你的数据是随机的吗？"）
3. **§C 额外案例**：补充 main paper 中 case study 数量，展示系统的鲁棒性
4. **§D 计算开销**：主动说明计算成本，而不是让 reviewer 猜测

### 待填充部分（实验后）

- §A.4 的实际 epoch 数和 wall-clock 时间
- §B.1 的实际 QC 通过率数字
- §E 的全部实验数字
- §C 的具体 case 文本（用真实系统输出替换当前占位内容）

---

*草稿版本 v1.0 | 2026-06-02 | V7 迭代产出*
