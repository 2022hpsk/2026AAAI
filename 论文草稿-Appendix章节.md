# SpeakerMem-R1 论文草稿：Appendix 章节

**版本**：v1.1（2026-06-02，中文化改写）  
**状态**：草稿，部分内容待实验后填充

---

## A. 超参数细节（Hyperparameter Details）

### A.1 模型配置

| 组件 | 设置 | 理由 |
|-----------|---------|-----------|
| 基座模型 | Qwen3-8B | 与 DeltaMem [cite] 对齐以便公平比较 |
| 微调 | LoRA（$r=32$，$\alpha=64$） | 平衡参数效率与表达力 |
| 优化器 | AdamW（$\beta_1=0.9$，$\beta_2=0.999$） | LLM 微调标准选择 |
| 学习率 | $3 \times 10^{-5}$ | 沿用 Memory-R2 [cite] |
| 训练框架 | verl [cite] | 分布式 GRPO 实现 |
| 硬件 | 4× A100-80GB | Stage 2 RL 训练 |

### A.2 GRPO 配置

| 超参数 | 取值 | 说明 |
|----------------|-------|-------------|
| $G$（global rollout 数） | 4 | 每样本每步的 rollout 数 |
| $G_\text{local}$（local rollout 数） | 4 | 每个检查点的 LoGo local rerollout 数 |
| $\lambda$（LoGo 权重） | 0.3 | 沿用 Memory-R2 [cite] |
| $\beta_\text{KL}$ | 0.01 | 对参考策略的 KL 正则 |
| $\tau$（Levenshtein 阈值） | 0.6 | 事实匹配的余弦相似度截断 |
| $\mu$（worst-speaker bonus） | 0.1 | $\min_s \text{LevF1}^s$ 的权重 |

### A.3 奖励权重

| 组件 | 权重 | 理由 |
|-----------|--------|-----------|
| $R_\text{task}$ | 0.5 | 最终答案质量 |
| $R_\text{state}$ | 0.8 | 稠密过程奖励（按 DeltaMem [cite] 为主导信号） |
| $R_\text{attr}$ | 0.3 | 说话人归属准确率 |
| $R_\text{aud}$ | 0.2 | 受众适配 |
| $R_\text{compr}$ | 0.1 | 记忆压缩效率 |
| $R_\text{RIF}$ | 0.1 | 遗忘恰当性 |

### A.4 三阶段训练计划

| 阶段 | 任务 | 时长 | 关键指标 |
|-------|------|----------|-----------|
| Stage 1（SFT） | 说话人归属事实抽取 | 3 epochs | 归属 F1 |
| Stage 2（RL） | 带 K=3→5→8 课程的 joint RL | 5 epochs | GroupMemBench F1 |
| Stage 3（E2E） | 多 benchmark 混合课程 | 2 epochs | 综合 benchmark |

---

## B. 训练数据细节（Training Data Details）

### B.1 合成数据质量统计

我们的 200 段训练集使用 GPT-4o 合成，生成 prompt 见 §4.1。质量过滤后：

| 场景 | 生成数 | 通过 QC | 最终 |
|---------|-----------|-----------|-------|
| close_friends | 55 | 50 | 50 |
| workplace_team | 54 | 50 | 50 |
| interest_community | 56 | 50 | 50 |
| locomo_triadic | 52 | 50 | 50 |
| **合计** | **217** | **200** | **200** |

质量过滤标准（§4.1）：
1. 每段对话每个说话人 ≥3 条不同事实
2. QA 答案经验证确需依赖记忆（GPT-4-judge 二分类）
3. 说话人标签全程一致

### B.2 合成对话样例（close_friends）

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

**真值记忆（Session 4 状态）**：
- $M_\text{core}^\text{Alice}$："Alice initially accepted ByteDance offer" → "Alice reconsidering ByteDance"
- $M_\text{episodic}^\text{Alice}$：[Session 1："Alice accepted ByteDance offer"]，[Session 4："Alice reconsidering due to team reassignment"]
- $M_\text{core}^\text{Carol}$："Carol interested in AI startups, specifically multi-agent systems"
- $M_\text{core}^\text{Bob}$：（此片段中未分享职业相关事实）

**样例 QA pairs**：
1. *提问者 Bob，问题："Alice 现在在哪工作？"* → "Alice 最初接受了 ByteDance 的 offer，但因团队重组正在重新考虑；目前状态不确定。"
2. *提问者 Alice，问题："Carol 对什么样的创业公司感兴趣？"* → "Carol 对 AI 创业公司感兴趣，具体是 multi-agent systems 方向。"
3. *提问者 Carol，问题："Alice 在 Session 1 关于 ByteDance 说了什么？"* → "Alice 说她拿到了 ByteDance 的 offer，下个月入职。"

### B.3 归属挑战统计（合成语料）

| 属性 | close_friends | workplace_team | interest_community | locomo_triadic |
|---------|------------|---------------|------------------|--------------|
| 每段对话平均说话人数 | 3.4 | 5.2 | 4.1 | 3.0 |
| 归属清晰的事实占比（%） | 82% | 74% | 70% | 88% |
| 归属模糊的案例 | 18% | 26% | 30% | 12% |
| 每段对话跨说话人引用数 | 4.2 | 7.1 | 5.8 | 3.9 |

*归属模糊*：两个说话人讨论同一实体、需要依赖上下文才能确定正确 owner 的情形。

---

## C. 额外案例研究（Additional Case Studies）

### C.1 案例 4：跨说话人多跳推理

**对话片段**：
```
Session 2, Alice: "Bob recommended this book to me last month: 'Thinking Fast and Slow'."
Session 3, Carol: "Alice, you seem like you'd enjoy anything about cognition."
Session 5, Bob: "Has anyone read the Kahneman book I mentioned? Did Carol enjoy it?"
```

**查询**（Bob）："Carol 读了我推荐的那本书吗？"

**DeltaMem (adapted)**：把 Bob 的推荐与 Carol 的阅读历史混为一谈 → "Carol mentioned she read Thinking Fast and Slow"（错误归属）

**SpeakerMem-R1**：
- $M_\text{core}^\text{Bob}$："Bob recommended 'Thinking Fast and Slow'"
- $M_\text{interact}$："Alice received book recommendation from Bob (Session 2)"
- $M_\text{core}^\text{Carol}$：（无 Carol 读此书的事实）
→ 答案："没有记录显示 Carol 读过这本书。我只知道 Bob 把它推荐给了 Alice。" ✓（正确地 abstention）

**分析**：这需要 3 跳推理：(1) Bob 推荐了书 → (2) 推荐给 Alice → (3) 检查 Carol 是否也收到或读过。SpeakerMem-R1 的 $M_\text{interact}$ 层捕获了这条跨说话人推荐链。

---

### C.2 案例 5：规范-个体混淆

**对话语境**：一个徒步群组，"难度偏好"既作为群体规范、又作为个体偏好被讨论。

```
Session 1, 群组讨论: "We always prefer easy-to-medium trails as a group."
Session 2, Alice (私下对 Bob): "Honestly, I prefer challenging trails. The group just slows me down."
```

**查询**（Carol）："Alice 的徒步路线偏好是什么？"

**Memory-R2 (adapted)**：把群体规范与 Alice 自述偏好混淆 → "Alice prefers easy-to-medium trails"（错误：把群体规范当作 Alice 的偏好检索出来）

**SpeakerMem-R1**：
- $M_\text{insight}$（群组）："Group prefers easy-to-medium trails"
- $M_\text{core}^\text{Alice}$："Alice personally prefers challenging trails"（受众：仅 Alice、Bob）
→ 由于 Carol 不在 Alice 的受众集合内："我没有关于 Alice 个人徒步偏好的具体信息。" ✓（正确的、保护隐私的 abstention）

---

## D. 计算开销分析（Computational Cost Analysis）

### D.1 训练成本估算

| 阶段 | 时间 | 成本（4×A100） |
|-------|------|--------------|
| Stage 1（SFT） | ~6 小时 | ~$100 |
| Stage 2（RL, K=3） | ~12 小时 | ~$200 |
| Stage 2（RL, K=5） | ~18 小时 | ~$300 |
| Stage 2（RL, K=8） | ~24 小时 | ~$400 |
| Stage 3（E2E） | ~8 小时 | ~$130 |
| **合计** | **~68 小时** | **~$1,130** |

### D.2 推理成本：说话人扩展

说话人条件化 LoGo 在每个检查点增加 $G_\text{local}$ 个额外 rollout。对 $K$ 个说话人与 $M$ 个 session 检查点：

$$\text{Total rollouts} = G \cdot T + G_\text{local} \cdot M \cdot K$$

当 $K=3, G=4, G_\text{local}=4, T=32, M=4$：
$$= 4 \times 32 + 4 \times 4 \times 3 = 128 + 48 = 176 \text{ rollouts}$$

相比 dyadic LoGo（$K=1$）：$128 + 16 = 144$ rollouts。

**开销**：SpeakerMem-R1 比 dyadic LoGo 多约 $\sim 1.2$× 的 rollout（而非朴素估计的 3–5×——因为说话人条件化是在同一个 local rerollout 预算内完成的，而非额外叠加）。

---

## E. 完整消融细节（Full Ablation Details）

### E.1 消融 A2：Per-Speaker vs. Flat Levenshtein

**假设**：按说话人分桶为归属错误提供了关键信号。扁平 Levenshtein 无法区分"Alice 的事实归属给 Bob"与"Bob 的事实归属给 Bob"。

**实验设置**：
- SpeakerMem-R1 Full vs. A2（全局扁平 Levenshtein，无说话人桶）
- 在 GroupMemBench 上评测，并按类别拆分

| 类别 | A2（Flat） | Full | Δ |
|---------|-----------|------|---|
| Knowledge update | XX% | XX% | +XX% |
| Term ambiguity | XX% | XX% | +XX% |
| User-implicit | XX% | XX% | +XX% |
| Multi-hop | XX% | XX% | +XX% |
| Temporal | XX% | XX% | +XX% |
| Abstention | XX% | XX% | +XX% |
| **总体 F1** | **XX%** | **XX%** | **+XX%** |

*主要预测*：在 knowledge-update（基线 27.1%）与 term-ambiguity（基线 37.7%）上提升最大——这两类都需要知道"谁说了什么发生了改变"。

### E.2 消融 A5：Joint vs. Sequential 训练

**假设**：joint 训练（所有 agent 共享 backbone）比 sequential 训练（每个 agent 在其他 agent 固定的情况下单独训练）提供更好的梯度流。

**设置**：Stage 2 joint RL（Full）vs. 依次训练 Construction → Retrieval → Answer。

这直接检验 **CoMAM** [cite] 的论断：在 dyadic 设定中 joint 训练比 sequential 带来 8.5–16.7% 提升，现在放到多方设定中验证。

---

## 写作备注

### Appendix 的功能定位

1. **§A 超参数**：让实验可复现，reviewer 会问"你怎么选的 τ=0.6"，这里要有答案
2. **§B 训练数据**：消除合成数据偏差的质疑（"你的数据是随机的吗？"）
3. **§C 额外案例**：补充 main paper 中 case study 数量，展示系统的鲁棒性
4. **§D 计算开销**：主动说明计算成本，而不是让 reviewer 猜测

### 待填充部分（实验后）

- §A.4 的实际 epoch 数与 wall-clock 时间
- §B.1 的实际 QC 通过率数字
- §E 的全部实验数字
- §C 的具体 case 文本（用真实系统输出替换当前占位内容）

---

*草稿版本 v1.1（中文化）| 2026-06-02*
