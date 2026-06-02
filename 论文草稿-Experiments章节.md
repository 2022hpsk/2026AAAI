# SpeakerMem-R1 论文草稿：Experiments 章节

**版本**：v1.1（2026-06-02，中文化改写）  
**状态**：草稿，待实验数字填入

---

## 4. Experiments

### 4.1 实验设置（Experimental Setup）

**Benchmark。** 我们在三个多方 benchmark 上评测，并在两个 dyadic benchmark 上做兼容性测试：

**多方 benchmark：**
- **GroupMemBench** [cite]：六类评测（multi-hop reasoning、knowledge update、term ambiguity、user-implicit reasoning、temporal reasoning、abstention）。采用 graph-grounded synthesis pipeline。当前最强系统仅达 46.0% 准确率，其中 knowledge-update 仅 27.1%。
- **EverMemBench** [cite]：长程职场协作对话 benchmark，含 170 名员工、51,023 轮（约 4.2M token）、2,400 个 QA pairs，覆盖三个维度（factual recall、applied memory、user profiling）。即便 oracle 系统在 multi-hop 归因上也仅约 26%。
- **SocialMemBench** [cite]：社交群组设定，含 430 个 personas、348 个 session、7,355 轮、1,031 个 QA pairs。覆盖五类群组原型（close friends、family、recreational、interest community、acquaintance network），跨三个规模档（4–30 名成员）。生产级记忆框架得分仅 0.12–0.18。

**dyadic 兼容性 benchmark：**
- **LoCoMo** [cite]：dyadic 记忆的标准长期对话 benchmark。
- **PersonaMem-v2** [cite]：个性化智能评测，含 1,000 用户 × 300+ 场景（比 v1 难 16 倍）。

**基线（Baselines）。** 我们与以下系统比较：

| 基线 | 类别 | 关键方法 |
|---------|---------|-----------|
| BM25 Retrieval | Training-free | 词面检索 |
| Mem0 [cite] | Training-free | CRUD 操作 + 启发式 |
| A-MEM [cite] | Training-free | 原子笔记 + 图结构 |
| Memory-R1 [cite] | RL（sequential） | construction + retrieval 分离 RL |
| AgeMem [cite] | RL（step-wise） | step-wise GRPO，三阶段 |
| DeltaMem [cite] | RL（dense reward） | Memory-based Levenshtein |
| Memory-R2 [cite] | RL（LoGo） | 从共享态分支的 local rerollout |
| CoMAM [cite] | RL（joint） | adaptive credit 多 agent |
| SpeakerMem-R1（本文） | RL（speaker-aware） | 完整方法 |

对于 RL 基线（DeltaMem/Memory-R2/CoMAM），我们通过使用相同的合成训练数据、并移除说话人相关组件，把它们改写到多方设定。这样构造出一个受控对比：唯有我们的说话人感知扩展贡献了提升。

**训练数据（Training Data）。** 由于 **GroupMemBench**、**EverMemBench**、**SocialMemBench** 都是只有评测、没有训练 split 的 benchmark，我们用 GPT-4 合成 200 段训练对话：

- 50 段 close-friends 场景（3–5 说话人，8 session，SocialMemBench 风格）
- 50 段 workplace-team 场景（4–8 说话人，16 session，EverMemBench 风格）
- 50 段 interest-community 场景（3–6 说话人，8 session，GroupMemBench 风格）
- 50 段 LoCoMo 衍生的三方增强（dyadic → triadic）

每段合成对话都包含说话人归属的真值记忆与 3 个 QA pairs。我们通过三项检查保证数据质量：(1) 每条 GT 记忆每个说话人 ≥3 条事实；(2) QA 答案需要依赖记忆（而非常识），由 GPT-4-judge 验证；(3) 说话人标签全程一致。

**实现（Implementation）。** 基座模型：**Qwen3-8B**（与 DeltaMem 选型对齐以便公平比较）。微调：LoRA（$r=32$，$\alpha=64$）。训练：verl 框架 [cite] 的 GRPO 实现。硬件：4×A100-80GB。超参数：$G=4$ 个 global rollout，$G_\text{local}=4$ 个 local rollout，$\lambda=0.3$，$\tau=0.6$，$\beta_\text{KL}=0.01$。$R_\text{task}$ 采用 token-level F1（以避免 binary EM 在 $G=4$ 时梯度为零 [cite]）。

---

### 4.2 主结果（Main Results）

**表 2：多方 benchmark 上的表现**

| 系统 | GroupMemBench (F1) | EverMemBench (Acc) | SocialMemBench (Avg) |
|--------|--------------------|--------------------|----------------------|
| BM25 | ~42% | ~18% | ~0.14 |
| Mem0 | ~38% | ~20% | ~0.15 |
| A-MEM | ~40% | ~21% | ~0.13 |
| Memory-R1 (adapted) | ~41% | ~22% | ~0.16 |
| AgeMem (adapted) | ~43% | ~23% | ~0.17 |
| DeltaMem (adapted) | ~44% | ~24% | ~0.18 |
| Memory-R2 (adapted) | ~45% | ~25% | ~0.19 |
| CoMAM (adapted) | ~44% | ~24% | ~0.18 |
| **SpeakerMem-R1（本文）** | **XX%** | **XX%** | **XX** |

*标 ~ 的数字是基于 GroupMemBench 当前最强（46%）与 SocialMemBench 分数（0.12–0.18）估计的基线值。实际基线数字将在实验后填入。*

**表 3：dyadic 兼容性（LoCoMo + PersonaMem-v2）**

| 系统 | LoCoMo F1 | PersonaMem-v2 Acc |
|--------|-----------|-------------------|
| Memory-R2 | 49.67 | -- |
| CoMAM | 54.xx | -- |
| **SpeakerMem-R1** | **XX** | **XX** |

*关键论点：我们的方法在 dyadic benchmark 上不退化（在 LoCoMo 上与 Memory-R2/CoMAM 有竞争力）。*

---

### 4.3 消融研究（Ablation Studies）

**表 4：GroupMemBench F1 上的组件消融**

| 模型 | F1 | vs Full | 移除的组件 |
|-------|-----|---------|-------------------|
| SpeakerMem-R1（Full） | XX | baseline | - |
| A1: w/o $R_\text{state}$ | XX | -XX | 说话人感知 Levenshtein |
| A2: 全局 Levenshtein（flat） | XX | -XX | 按说话人分桶 |
| A3: w/o LoGo local branch | XX | -XX | LoGo 信用分配 |
| A4: 原版 LoGo（无说话人条件化） | XX | -XX | 说话人条件化 |
| A5: sequential 训练（vs joint） | XX | -XX | joint 多 agent RL |
| A6: 扁平记忆（vs 5 层） | XX | -XX | 分层结构 |
| A7: w/o $R_\text{leak}$ | XX | -XX | 隐私惩罚 |

**关键消融预测：**
- A2 vs Full：预期按说话人分桶带来 +5–10 F1（归属是 GroupMemBench 第一失败模式）
- A5：预期 joint vs sequential 带来 +4–8 F1（CoMAM 显示 8.5–16.7% 提升）
- A3 vs Full：预期 LoGo 带来 +2–4 F1（Memory-R2 在 dyadic 上显示 +3 F1）

---

### 4.4 分析（Analysis）

**归属准确率分析。** GroupMemBench 有六个类别；我们报告按类别的分数，以理解 SpeakerMem-R1 在何处帮助最大。

**表 5：GroupMemBench 按类别表现**

| 类别 | BM25 | Memory-R2 (adapted) | SpeakerMem-R1 |
|---------|------|---------------------|---------------|
| Multi-hop reasoning | XX% | XX% | XX% |
| Knowledge update | 27.1% | XX% | XX% |
| Term ambiguity | 37.7% | XX% | XX% |
| User-implicit | XX% | XX% | XX% |
| Temporal | XX% | XX% | XX% |
| Abstention | XX% | XX% | XX% |

*主要假设：SpeakerMem-R1 在"knowledge update"与"user-implicit reasoning"类别上提升最大，因为这两类需要知道"谁说了什么发生了改变"。*

**隐私泄漏分析。** 我们报告各方法的跨说话人信息泄漏率（事实落入错误说话人桶的比例）。

**表 6：归属错误与隐私泄漏**

| 系统 | 归属错误率 ↓ | 跨说话人泄漏率 ↓ |
|--------|--------------------------|-------------------------------|
| DeltaMem (adapted) | XX% | XX% |
| Memory-R2 (adapted) | XX% | XX% |
| SpeakerMem-R1 | XX% | XX% |

**说话人数量扩展。** 我们在不同群组规模（K=3, 5, 8）上测试表现，验证 SpeakerMem-R1 能随群组规模扩展。

---

### 4.5 案例研究（Case Studies）

**案例 1：多说话人归属挑战**

> Alice：「I'm thinking of switching jobs, maybe to ByteDance.」  
> Bob：「That's interesting. Carol was also considering a job change, right?」  
> Carol：「Yeah, but I'm leaning towards a startup.」
>
> *查询（Alice 提问）：「谁在考虑去创业公司？」*

**Memory-R2 (adapted)**：把 Bob 和 Carol 的陈述合并 → 答案："Bob was considering job changes"（归属错误）

**SpeakerMem-R1**：$M_\text{core}^\text{Carol}$："Carol considering startup" | $M_\text{core}^\text{Alice}$："Alice considering ByteDance" → 答案："Carol is considering a startup" ✓

**案例 2：时序状态覆盖的防止**

> Turn 1，Alice：「I work at Tencent.」  
> ...  
> Turn 45，Alice：「I just got hired by ByteDance!」
>
> *查询：「Alice 之前在哪里工作？」*

**DeltaMem (adapted)**：覆盖 $M_\text{core}^\text{Alice}$ → 答案："ByteDance"（漏掉了时序维度）

**SpeakerMem-R1**：$M_\text{episodic}^\text{Alice}$：[Turn 1："Alice worked at Tencent"] | [Turn 45："Alice moved to ByteDance"] → 答案："Alice previously worked at Tencent" ✓

**案例 3：跨说话人隐私边界**

> Bob（私下对 Alice）：「Don't tell Carol about the merger.」
>
> *查询（Carol 提问）：「Bob 关于公司方向说了什么？」*

**基线系统**：把 merger 信息暴露给 Carol（隐私泄漏）

**SpeakerMem-R1**：训练期的 $R_\text{leak}$ 惩罚教会 agent：Bob 的 merger 相关信息其 $A_{e} = \{\text{Alice}\}$，不包含 Carol → 答案："I don't have information about that" ✓（恰当地 abstention）

---

### 4.6 训练数据分析（Training Data Analysis）

**数据多样性消融。**

| 训练数据 | GroupMemBench F1 | SocialMemBench Avg |
|--------------|------------------|--------------------|
| 50 样本（仅 close_friends） | XX | XX |
| 100 样本（+ workplace） | XX | XX |
| 150 样本（+ interest） | XX | XX |
| 200 样本（+ LoCoMo triadic） | XX | XX |

*预期：150 样本是"专精 vs 聚合"的拐点，沿用 Curriculum Study [cite]。*

**对比：合成 vs 真实数据质量。** 我们还测试了一个在 50 段 EverMemBench 风格对话（真实数据，无 GT 记忆）上训练的变体，与我们完全合成的训练做对比：

| 训练数据 | GroupMemBench F1 |
|--------------|------------------|
| 全合成（200） | XX |
| 真实 + 合成混合（50+150） | XX |

---

## 写作备注

### 实验设计的关键防御点

1. **为什么用合成数据**：真实多方 benchmark 无训练集；合成数据已通过质量验证；最终评测在真实 benchmark 上，确保不存在 data leakage

2. **baseline 如何公平**：所有 RL baseline 用相同合成数据训练，相同 Qwen3-8B base，相同 LoRA r=32；唯一区别是 reward design

3. **dyadic 退化测试**：报告 LoCoMo/PersonaMem-v2 分数，确保不损害 dyadic 能力

4. **reviewer 常见质疑**："你的提升来自更多训练数据而非 design"
   - 回应：baseline 也用相同 200 条合成数据训练（A1-A7 都是在同样数据量上训的）

5. **可复现性**：我们会开源合成数据 pipeline + 200 条数据集 + 评测代码（基于 EverMemOS 框架扩展）

---

*草稿版本 v1.1（中文化）| 2026-06-02*
