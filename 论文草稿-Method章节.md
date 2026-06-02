# SpeakerMem-R1 论文草稿：Method 章节

**版本**：v1.1（2026-06-02，中文化改写）  
**状态**：草稿，供写作参考与技术审查

---

## 3. Method

### 3.1 问题形式化（Problem Formulation）

**多方记忆管理。**
考虑一段对话 $C = \{(s_t, u_t)\}_{t=1}^T$，包含 $K$ 个说话人 $S = \{s_1, \ldots, s_K\}$，其中每条话语 $u_t$ 归属于说话人 $s_t$。给定一个查询 $q = (s_\text{ask}, s_\text{target}, q_\text{text})$——分别指定提问者、被询问的目标对象与问题文本——记忆 agent 必须维护一个说话人索引的记忆结构 $M$，并检索相关信息来回答 $q$。

dyadic 设定中不存在、而多方设定中才出现的核心挑战是：

**(1) 说话人归属（Speaker Attribution）：** 每条记忆事实 $f$ 必须关联到其来源说话人：$f = (\text{content}, s_\text{owner})$。在 dyadic 设定中，owner 永远是那唯一的对方；而在多方设定中，当多个说话人讨论同一实体时，归属是模糊的。

**(2) 受众适配（Audience Adaptation）：** 回答 $q$ 需要考虑提问者 $s_\text{ask}$ 的视角、其与 $s_\text{target}$ 的关系，以及访问权限。

**(3) 跨说话人隐私（Cross-Speaker Privacy）：** $s_i$ 拥有的信息可能不应被 $s_j$ 访问，这要求记忆结构中具备显式的访问控制。

---

### 3.2 五层说话人索引记忆（Five-Layer Speaker-Indexed Memory）

我们引入一个结构化记忆架构，把说话人锚定作为一等设计原则：

$$M = \{M_\text{core}^s, M_\text{episodic}^s, M_\text{profile}^s\}_{s \in S} \cup \{M_\text{interact}, M_\text{insight}\}$$

五个层各司其职：

| 层 | 作用域 | 内容类型 | 示例 |
|-------|-------|-------------|---------|
| $M_\text{core}^s$ | 单说话人 | 持久事实 | "Alice works at ByteDance" |
| $M_\text{episodic}^s$ | 单说话人 | 时间索引的情节 | "Alice mentioned job change (turn 42)" |
| $M_\text{profile}^s$ | 单说话人 | 表达风格、偏好 | "Bob uses formal English" |
| $M_\text{interact}$ | 群组 | 跨说话人事件、关系 | "Alice and Bob have worked together" |
| $M_\text{insight}$ | 群组 | 高层元知识 | "This group focuses on AI startups" |

每条 $M_\text{core}^s$ 中的条目 $e$ 是一个元组 $(s_\text{owner}, \text{content}, A_e, l_e, t_e)$，其中 $A_e \subseteq S$ 是受众集合（访问控制），$l_e$ 是所属层，$t_e$ 是创建轮次。

这一分层结构直接对应 **SocialMemBench** [cite] 记录的五种失败模式：
- **单流混淆（single-stream conflation）** → $M_\text{core}^s$ 确保事实保持说话人归属
- **时序状态覆盖（temporal-state overwrite）** → $M_\text{episodic}^s$ 保留时间索引的版本
- **实体合并（entity merging）** → 唯一的 $s_\text{owner}$ 防止人格混淆
- **跨人格知识鸿沟（cross-persona knowledge gap）** → $M_\text{interact}$ 追踪跨说话人关系
- **规范-个体混淆（norm-individual conflation）** → $M_\text{insight}$（群体规范）与 $M_\text{core}^s$（个体）相分离

---

### 3.3 说话人归属的动作空间（Speaker-Attributed Action Space）

基于 **AgeMem** [cite] 的观察——记忆操作应被建模为可学习的离散动作——我们扩展动作空间，把说话人锚定作为强制的元数据：

$$\mathcal{A} = \{\texttt{WRITE}(c, s, A, l),\ \texttt{UPDATE}(e, c),\ \texttt{DELETE}(e),\ \texttt{SUMMARY}(E, l),\ \texttt{PROMOTE}(e),\ \texttt{SUPPRESS}(e, \lambda),\ \texttt{READ}(s, s'),\ \texttt{NOOP}\}$$

其中 $c$ 是内容，$s$ 是说话人 owner，$A$ 是受众集合，$l$ 是目标层，$e$ 是条目 ID，$s'$ 是跨说话人访问的目标说话人。

这与 dyadic 记忆动作空间（**Memory-R1** [cite]、**AgeMem** [cite]、**DeltaMem** [cite]）有本质区别——后者的动作缺乏说话人条件化。说话人元数据使下文描述的奖励函数成为可能。

---

### 3.4 说话人感知的 Levenshtein 奖励（SpeakerLevenshtein）

受 **DeltaMem** [cite] 的洞察启发——奖励记忆状态转移比奖励最终答案正确性能提供更稠密的训练信号——我们提出 **SpeakerLevenshtein**，一个面向多方设定、按说话人分桶的扩展。

**按说话人的状态增量（Per-Speaker State Diff）。** 在每一轮 $t$，我们对每个说话人分别计算预测记忆状态与真实记忆状态之间的增量：

$$\Delta^s_\text{pred} = M^s_t - M^s_{t-1}, \quad \Delta^s_\text{gt} = M^{s,*}_t - M^{s,*}_{t-1}$$

**按说话人分桶的 F1（Speaker-Bucketed F1）。** 对每个说话人 $s$，计算一个 Levenshtein F1：

$$\text{LevF1}^s = \frac{2 \cdot \text{SP}^s \cdot \text{SR}^s}{\text{SP}^s + \text{SR}^s}$$

其中 soft precision $\text{SP}^s$ 与 soft recall $\text{SR}^s$ 通过在 $\Delta^s_\text{pred}$ 与 $\Delta^s_\text{gt}$ 的嵌入余弦相似度矩阵上做 optimal transport 匹配（Hungarian 算法）得到，并以阈值 $\tau$ 过滤，再叠加局部词面保真度（lexical fidelity，沿用 **DeltaMem** [cite]）：

$$\text{Sim}(f_i, f_j) = \text{cos}(\mathbf{e}_i, \mathbf{e}_j) \cdot \left(1 + 0.2 \cdot \text{KeyCov}(f_i, f_j)\right)$$

**跨说话人泄漏惩罚（Cross-Speaker Leakage Penalty）。** 为惩罚归属错误（Alice 的事实出现在 Bob 的桶里）：

$$R_\text{leak} = -\frac{1}{N} \sum_{s \in S} \sum_{f \in M^s_t} \mathbb{1}[\text{TrueOwner}(f) \neq s]$$

**总状态奖励（Total State Reward）：**

$$R_\text{state} = \underbrace{\frac{1}{K} \sum_{s=1}^K \text{LevF1}^s}_{\text{按说话人均值}} + \underbrace{\mu \cdot \min_s \text{LevF1}^s}_{\text{worst-speaker bonus}} + R_\text{leak}$$

其中 worst-speaker bonus $\mu \cdot \min_s \text{LevF1}^s$ 防止 agent 在更难的说话人上"摆烂"。

**为什么 per-speaker 分桶并非平凡（non-trivial）。** 一个朴素（naïve）的扩展会把所有说话人的事实拼接在一起、全局地套用 **DeltaMem** 的 Levenshtein 奖励。这种做法会因两个不同的原因而失败：

*(1) 归属-内容混淆。* 全局 Levenshtein 会对一个事实错误（"Alice works at Google"，而真值是 "ByteDance"）与一个归属错误（"Alice works at ByteDance" 却存进了 Bob 的桶）施加相同的惩罚。这二者代表本质不同的失败模式：事实错误意味着信息丢失，而归属错误意味着跨说话人污染。把二者混为一谈，会让 agent 无法学到该优先修复哪种失败。

*(2) 说话人不均衡。* 在说话人间取平均，会让 agent 在 K-1 个简单说话人上取得成功、却忽略最难的那一个。在 **GroupMemBench** 上，归属难度极不均衡——拥有大量交叉引用的说话人，其归属难度远高于边缘成员。我们的 worst-speaker bonus $\mu \cdot \min_s \text{LevF1}^s$ 防止了这种退化。

在 **GroupMemBench** 上，归属错误是主要失败模式（知识更新类 27.1%、术语歧义类 37.7%）。**DeltaMem** 的扁平 Levenshtein 奖励无法区分"Alice 的事实在 Bob 的桶"与"正确事实在正确的桶"，而 SpeakerLevenshtein 通过分说话人单独计算，显式惩罚这种跨说话人污染。

---

### 3.5 说话人条件化的 LoGo-GRPO（Speaker-Conditioned LoGo-GRPO）

**动机。** **Memory-R2** [cite] 指出，跨 rollout 时发散的记忆状态会破坏 GRPO 的 group-relative 比较假设，并提出 LoGo-GRPO——从共享中间态分支出 local rerollout。在多方设定中，这一问题被 K 重放大：不同 rollout 不仅可能有不同的记忆状态，还可能有不同的 active speaker 组成，使得全局组比较"双重无效"。

**为什么说话人条件化是逻辑必然，而非便利之举。** **Memory-R2** 的 LoGo-GRPO 保证了可比的起始记忆状态；而在多方设定中，可比性还要求**相同的说话人组成**——因为记忆操作策略在"只有 Alice 发言的一轮"与"Alice 和 Bob 同时彼此谈论的一轮"之间存在本质差异。没有说话人条件化，两个 local rollout 可能处理着 active speaker 不同的轮次——这会让组内比较和全局比较一样不公平。因此，说话人条件化的 rerollout 不是可选的优化，而是多方 RL 中有效 local 信用分配的前提。

**说话人条件化的 local rerollout。** 我们以说话人分层扩展 LoGo-GRPO。在 global 轨迹的每个中间检查点 $m$，我们把 local rerollout 条件化在 active speaker set 上：

$$\mathcal{T}_\text{local}^m = \{r_1, \ldots, r_G\} \text{ from } (M_m, C_{t:}, \text{speakers}(C_{t:}))$$

所有 $G$ 个 local rollout 共享同一个中间记忆状态 $M_m$，**并且**共享同一个 active speaker set，从而保证在相同语境内的公平比较。

**按说话人的自适应信用（Per-Speaker Adaptive Credit）。** 受 **CoMAM** [cite] 的 rank-consistency 信用分配启发，我们基于"每个说话人的 local reward 与 global reward 的对齐程度"计算按说话人的信用权重 $\alpha_s$：

$$\alpha_s = \text{normalize}(\text{SpearmanCorr}(R_\text{local}^s, R_\text{global}))$$

这确保了：记忆操作对最终答案贡献更大的说话人，能获得成比例更多的梯度信号。

**联合目标（Combined Objective）：**

$$\mathcal{L}_\text{total} = \mathcal{L}_\text{global} + \lambda \cdot \mathcal{L}_\text{local} + \beta \cdot \mathcal{L}_\text{KL}$$

其中 $\mathcal{L}_\text{global}$ 是在完整轨迹上的标准 GRPO loss，$\mathcal{L}_\text{local}$ 是在说话人条件化 rerollout 上的 LoGo local loss，$\mathcal{L}_\text{KL}$ 是 KL 正则项（沿用 **WebAgent-R1** [cite]），用于防止 "Echo Trap"。

---

### 3.6 完整奖励函数（Complete Reward Function）

完整奖励信号结合任务层与过程层信号：

$$R = \underbrace{0.5 \cdot R_\text{task}}_{\text{outcome}} + \underbrace{0.8 \cdot R_\text{state}}_{\text{稠密过程}} + \underbrace{0.3 \cdot R_\text{attr}}_{\text{归属}} + \underbrace{0.2 \cdot R_\text{aud}}_{\text{受众}} + \underbrace{0.1 \cdot R_\text{compr} + 0.1 \cdot R_\text{RIF}}_{\text{结构}}$$

其中：
- $R_\text{task}$：模型答案与真值之间的 token-level F1（沿用 [cite]，其表明 binary EM 在 $G=4$ 时梯度为零）
- $R_\text{state}$：SpeakerLevenshtein（§3.4），权重 0.8，作为主导信号（沿用 **DeltaMem** [cite]）
- $R_\text{attr}$：说话人归属准确率（被正确归属到来源说话人的事实占比）
- $R_\text{aud}$：受众适配得分（答案是否恰当地适配提问者）
- $R_\text{compr}$：记忆压缩率奖励（沿用 **Mem-α** [cite]）
- $R_\text{RIF}$：遗忘恰当性（沿用 **MOOM** [cite]）

$R_\text{state}$ 的主导地位（权重 0.8）反映了 **DeltaMem** 的实证发现：稠密过程奖励比 outcome 奖励更能加速收敛 [cite]。

---

### 3.7 三阶段训练流程（Three-Stage Training Pipeline）

**Stage 1：说话人归属 SFT。** 我们首先在 200 段合成多方对话（§4.3）上做监督微调，使用 speaker-masked 交叉熵 loss，教会模型说话人归属的记忆操作格式。这个热启动至关重要：**Memory-R2** [cite] 的消融显示，若 fact extractor 训练不足，无强初始化的 RL 会使 F1 从 49.67 跌到 28.30。

**Stage 2：带说话人条件化 LoGo 的 joint RL。** 我们用 SpeakerMem-GRPO 目标联合训练所有 agent（construction + retrieval + answer，共享一个 backbone，沿用 **Memory-R2** [cite]）。我们采用一个逐步增加说话人数量与 session 长度的课程：

$$\text{Stage 2: } K=3, N_\text{sess}=8 \to K=5, N_\text{sess}=16 \to K=8, N_\text{sess}=32$$

该设计受 **Memory-R2** 的课程启发 [cite]，并沿说话人维度扩展。

**Stage 3：端到端多 benchmark 微调。** 我们以混合课程（mixed curriculum）在 **GroupMemBench**、**EverMemBench**、**SocialMemBench** 的评测数据上收尾（使用我们合成课程的 train-test split），沿用 **MemSearcher** [cite] 的 multi-context GRPO 范式，以防止单一 benchmark 过拟合。

---

### 3.8 与现有工作的关联（Connection to Existing Work）

表 1 总结了 SpeakerMem-R1 如何扩展先前方法：

| 组件 | 借鉴自 | 我们的扩展 |
|-----------|------------|---------------|
| 稠密状态奖励 | DeltaMem [cite] | 按说话人分桶的 Levenshtein |
| Local rerollout | Memory-R2 [cite] | 说话人条件化的分层 |
| Joint 训练 | CoMAM [cite] | 按说话人的自适应信用 |
| Step-wise 信用 | AgeMem [cite] | K 重说话人维度 |
| 过程奖励 | Mem-α [cite] | 多组件多方奖励 |
| 遗忘 | MOOM [cite] | 说话人索引记忆中的 SUPPRESS 动作 |

---

## 写作技术备注

### §3.4 SpeakerLevenshtein 的 novelty 论证

写作中必须清晰表达为什么 per-speaker bucketing 不是 trivial：

> "A naïve extension would simply concatenate all facts across speakers and apply DeltaMem's Levenshtein reward globally. This fails for two reasons: (1) it conflates attribution errors (a fact in the wrong speaker bucket) with factual errors (wrong fact content), both penalized identically; (2) it averages over speakers, allowing the model to succeed on easy speakers (K-1) while ignoring hard ones. SpeakerLevenshtein addresses both by computing per-speaker deltas and adding a worst-speaker bonus."

### §3.5 Speaker-conditioned LoGo 的 novelty 论证

> "Memory-R2's LoGo-GRPO ensures comparable starting states; in multi-party settings, comparability also requires identical speaker compositions, since memory operation strategies fundamentally differ between 'turn where only Alice speaks' and 'turn where Alice and Bob speak simultaneously about each other.' Speaker-conditioned rerollouts are thus not merely a convenience but a logical necessity."

### §3.7 课程设计的 novelty 论证

> "Prior curriculum designs for memory RL (Memory-R2 [cite]) increase session count from 8 to 32. We augment this with a speaker-count dimension (K=3→5→8), reflecting the progressive difficulty of multi-party attribution: 3-speaker conversations have unambiguous attribution in ~85% of facts, while 8-speaker conversations reduce this to ~40% (measured on our synthesized corpus). The 2D curriculum (session length × speaker count) is novel to multi-party memory RL."

---

*草稿版本 v1.1（中文化）| 2026-06-02*
