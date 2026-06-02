# SpeakerMem-R1：Method 章节完整版
**版本**：v4（融合 V3/V4 所有技术升级）  
**对应论文节**：§3（问题形式化）+ §4（方法）

---

## §3 Problem Formulation

### 3.1 Multi-Party Conversation Memory Setting

设 $\mathcal{P} = \{p_1, p_2, \ldots, p_N\}$ 为群组中 $N$ 个 speaker 的集合。

**Multi-party conversation session**：
$$S_t = \{(u_i, p_i^{\text{from}}, \mathcal{A}_i)\}_{i=1}^{T_t}$$

其中：
- $u_i$：第 $i$ 轮发言内容
- $p_i^{\text{from}} \in \mathcal{P}$：发言的 speaker
- $\mathcal{A}_i \subseteq \mathcal{P}$：该发言的受众集合（谁能看到这条信息）

**Memory state**（core contribution）：
$$M_t = \left(\{M_{p_k}\}_{k=1}^{N},\ M_G\right)$$

其中每个 speaker $p_k$ 的记忆是四维的：
$$M_{p_k} = \left(M_{p_k}^{\text{core}},\ M_{p_k}^{\text{epi}},\ M_{p_k}^{\text{sem}},\ M_{p_k}^{\text{ins}}\right)$$

以及群体记忆：
$$M_G = \left(M_G^{\text{inter}},\ M_G^{\text{ins}}\right)$$

**Memory agent policy**：
$$\pi_\theta(a_t \mid c_t, M_{t-1}, p_{\text{context}})$$

其中 $c_t$ 是当前对话上下文，$p_{\text{context}}$ 是 speaker 上下文（谁在场，谁在问问题）。

### 3.2 Multi-Party Memory Actions

action space $\mathcal{A}$ 包含以下操作，每个操作必须指定 speaker attribution（信息属于谁）和 audience 权限：

| Action | 描述 | 必填参数 |
|--------|------|---------|
| WRITE\_CORE | 写入核心身份事实 | content, speaker\_id |
| WRITE\_EPI | 写入具体事件 | content, speaker\_id, audience\_set |
| WRITE\_SEM | 写入抽象知识/偏好 | content, speaker\_id |
| UPDATE | 更新现有片段 | fragment\_id, new\_content |
| DELETE | 删除片段 | fragment\_id, reason |
| SUMMARY | 压缩多条为摘要 | fragment\_ids, output\_layer |
| PROMOTE | 升华：episodic → insight | fragment\_id, from, to |
| SUPPRESS | 降权/软遗忘 | fragment\_id, strength ∈ [0,1] |
| QUARANTINE | 隔离可疑信息 | fragment\_id |
| READ\_CROSS | 跨 speaker 访问（需权限检查）| asker\_id, target\_speaker\_id |
| CROSS\_REF | 建立跨 speaker 关联 | frag\_a, frag\_b, relation |
| NOOP | 不操作 | - |

### 3.3 Evaluation Dimensions

**Task-level**（直接优化目标）：
- Token-level F1 of QA answers（而非 binary EM）

**Speaker Attribution**（核心新维度）：
$$F1_{\text{attr}} = \frac{2 \cdot P_{\text{attr}} \cdot R_{\text{attr}}}{P_{\text{attr}} + R_{\text{attr}}}$$

其中 $P_{\text{attr}}$ = 正确归因的记忆 / 所有记忆；$R_{\text{attr}}$ = 正确归因的记忆 / GT 中的记忆。

**Audience Adaptation**：系统回答是否遵循 audience 访问权限（不泄露受限信息）。

**Group Dynamics Recall**：群体层面的互动模式是否被正确记录。

---

## §4 Method: SpeakerMem-R1

### 4.1 Speaker-Structured Memory Architecture

**MemoryFragment**（基础存储单元）：

```python
@dataclass
class MemoryFragment:
    content: str              # 记忆内容
    speaker_id: str           # 信息属于哪个 speaker（来源）
    audience_set: frozenset   # 可见范围
    confidence: float         # 置信度（基于 corroboration）
    timestamp: int            # session index（when created/updated）
    layer: Literal['core', 'episodic', 'semantic', 'insight', 'quarantine']
    retrieval_count: int = 0  # 被检索次数（用于信用分配）
    attribution_verified: bool = False  # 归因是否经过验证
    trust_weight: float = 1.0  # 来源 speaker 的信任分数
```

**SpeakerMemorySlot**（per-speaker 四维记忆槽）：

```python
@dataclass
class SpeakerMemorySlot:
    speaker_id: str
    core: list[MemoryFragment]       # 稳定身份事实（姓名/职业/关系）
    episodic: list[MemoryFragment]   # 时间戳事件（"昨天去了..."}
    semantic: list[MemoryFragment]   # 抽象偏好/知识（"喜欢咖啡"）
    insight: list[MemoryFragment]    # 由 PROMOTE 升华的角色洞察
    quarantine: list[MemoryFragment] # 可疑信息隔离区
    trust_score: float = 1.0         # SSGM 风格的动态信任分数
    
    def total_fragments(self):
        return sum(len(getattr(self, d)) for d in ['core', 'episodic', 'semantic', 'insight'])

@dataclass
class GroupMemorySlot:
    interaction_patterns: list[str]   # speaker 间互动模式
    group_insight: list[str]           # 群体级别洞察
    consensus: dict[str, str]          # 话题 → 共识
    dissent: dict[str, list[str]]      # 话题 → 持异见的 speaker 列表
```

**完整记忆矩阵**：
$$\underbrace{N \times 4}_{\text{per-speaker}} + \underbrace{2}_{\text{group}} = N \times 4 + 2 \text{ dimensions}$$

对于 $N=5$ 的群组：22 维记忆空间。

**Speaker Trust Modeling**（基于 SSGM）：

```python
def update_speaker_trust(speaker_id: str, history: list) -> float:
    """动态信任分 = 历史一致性 × 佐证验证"""
    # 该 speaker 过去声明的事实是否前后一致
    consistency = fact_consistency_score(speaker_id, history)  # 0-1
    # 是否有其他 speaker 或 external source 佐证
    corroboration = cross_speaker_verification(speaker_id, history)  # 0-1
    return 0.7 * consistency + 0.3 * corroboration

def write_policy(content: str, speaker_id: str, trust: float) -> str:
    """基于信任分决定写入层"""
    if trust > 0.8:
        return 'core'         # 高信任 → 直接写核心
    elif trust > 0.5:
        return 'episodic'     # 中信任 → 写情节，降权
    else:
        return 'quarantine'   # 低信任 → 隔离
```

---

### 4.2 Speaker-Aware Levenshtein Dense Reward (SpeakerLev)

**回顾 DeltaMem 的 Levenshtein 奖励**：

DeltaMem 计算预测记忆状态 $\hat{M}$ 和 ground truth 状态 $M^*$ 之间的差分：
$$R_{\text{state}} = F1(\Delta\hat{M},\ \Delta M^*)$$

其中 $\Delta M = M_t - M_{t-1}$（新增 + 删除的记忆集合），用最优传输计算相似度。

**SpeakerLev：per-speaker 扩展**：

$$R_{\text{SpeakerLev}} = \frac{1}{N} \sum_{k=1}^{N} F1\left(\Delta\hat{M}_{p_k},\ \Delta M^*_{p_k}\right)$$

每个 speaker 的 memory state diff 单独计算，然后平均。

**Cross-Speaker Leakage Penalty**（新增）：

$$R_{\text{leak}} = -\lambda_{\text{leak}} \sum_{j \neq k} \text{ContaminationScore}\left(\hat{M}_{p_j},\ \text{Facts}(p_k)\right)$$

其中 $\text{ContaminationScore}(M_A, F_B)$ 衡量 speaker $A$ 的记忆中有多少 speaker $B$ 的事实（越小越好）。

**完整奖励函数**（8 个组件）：

$$R_{\text{total}} = w_1 R_{\text{task}} + w_2 R_{\text{attr}} + w_3 R_{\text{SpeakerLev}} + w_4 R_{\text{aud}} + w_5 R_{\text{compr}} + w_6 R_{\text{RIF}} + w_7 R_{\text{privacy}} + w_8 R_{\text{format}}$$

| 组件 | 来源灵感 | 权重（初始）| 描述 |
|------|---------|------------|------|
| $R_{\text{task}}$ | 标准 QA | $w_1 = 1.0$ | token-F1 answer 质量 |
| $R_{\text{attr}}$ | GroupMemBench 指标 | $w_2 = 0.5$ | speaker attribution F1 |
| $R_{\text{SpeakerLev}}$ | DeltaMem 扩展 | $w_3 = 0.6$ | per-speaker 状态差分 |
| $R_{\text{aud}}$ | SocialMemBench 指标 | $w_4 = 0.3$ | audience 适配分 |
| $R_{\text{compr}}$ | Mem-α 风格 | $w_5 = 0.1$ | 记忆压缩率 |
| $R_{\text{RIF}}$ | MOOM 风格 | $w_6 = 0.1$ | 适当遗忘分 |
| $R_{\text{privacy}}$ | 记忆安全论文 | $w_7 = 0.3$ | 隐私/安全分 |
| $R_{\text{format}}$ | 格式合规 | $w_8 = 0.1$ | 合法 JSON 输出 |

**权重选择原则**（参考 DeltaMem 经验）：
- $R_{\text{SpeakerLev}}$ 给大权重（dense signal，收敛快）
- $R_{\text{task}}$ 保持最大（最终目标）
- $R_{\text{privacy}}$ 中等权重（安全是约束而非目标）

---

### 4.3 Speaker-Conditioned LoGo-GRPO

**回顾 Memory-R2 的 LoGo-GRPO**：

Memory-R2 发现不同 rollout 的 intermediate memory state 已经发散，violating GRPO 的 group-relative 假设。解决方案：从 shared intermediate state 出发，重新 rollout（local rerollout）。

**我们的 speaker-conditioned 扩展**：

```python
def speaker_logo_grpo_update(batch, model, G=4, λ=0.5):
    """
    Speaker-Conditioned LoGo-GRPO
    
    修改 Memory-R2 的 local rerollout：
    在同一 shared state 出发时，额外按 speaker partition 分组
    只在"相同 speaker 集合"的轨迹内做局部比较
    """
    # === 全局阶段（Global GRPO）===
    global_trajectories = rollout(batch, model, G=G)
    global_reward = [reward_v3(t) for t in global_trajectories]
    
    # GRPO 全局优势（跨所有轨迹）
    global_advantage = group_relative_advantage(global_trajectories, global_reward)
    global_loss = grpo_loss(global_trajectories, global_advantage)
    
    # === 局部阶段（Speaker-Conditioned Local GRPO）===
    # 从 global_trajectories 中采样 shared intermediate state（阶段约 1/3 处）
    intermediate_states = sample_intermediate_states(global_trajectories)
    
    local_losses = []
    for state in intermediate_states:
        # 按当前对话的 speaker 集合对 rollout 分组
        speaker_partition = get_speaker_partition(batch, state)
        
        for sp in speaker_partition:
            # 从 intermediate state 出发，固定 speaker 条件，重新 rollout
            local_rollouts = rerollout(state, model, condition=sp, G=G)
            local_reward = [reward_v3(t) for t in local_rollouts]
            
            # local 优势（仅在同一 speaker partition 内比较）
            local_advantage = group_relative_advantage(local_rollouts, local_reward)
            local_losses.append(grpo_loss(local_rollouts, local_advantage))
    
    # LoGo 组合
    total_loss = global_loss + λ * mean(local_losses)
    return total_loss.backward()

def get_speaker_partition(batch, state):
    """
    把 G 条轨迹按 speaker set 相似性分组
    同一组内：speaker set 相同，可以做公平比较
    """
    return cluster_by_speaker_set(batch.speakers, state.active_speakers)
```

**为什么 speaker-conditioning 重要**：

在多方对话中，不同 rollout 不只因为 memory state 发散（Memory-R2 发现的问题），还因为**活跃 speaker 的子集可能不同**（speaker absence/presence 影响 memory state）。

如果 rollout A 中 Charlie 发言了但 rollout B 中 Charlie 没发言，它们的 intermediate state 就不可比——即使从相同 checkpoint 出发。

Speaker conditioning 解决了这个问题：只在"相同 speaker 集合"的轨迹内做 local 比较。

---

### 4.4 Contribution-Aware Speaker Gradient Weighting

**回顾 MemBuilder 的贡献感知梯度加权**：

MemBuilder 把记忆操作 $a_i$ 的梯度权重设为：
$$w_i^{\text{MemBuilder}} = \frac{\text{retrieval\_count}(m_i)}{\text{total\_retrievals}}$$

**SpeakerMem-R1 的三重扩展**：

```python
def speaker_gradient_weight(action, trajectory, ground_truth):
    """
    三重加权：使用频率 × 归因准确性 × 隐私合规性
    """
    mem = action.produced_fragment
    
    # 1. 使用频率（MemBuilder style）
    usage_weight = mem.retrieval_count / max(total_retrievals, 1)
    
    # 2. Speaker Attribution 准确性
    true_speaker = ground_truth.true_speaker_of(mem.content)
    attr_accuracy = 1.0 if action.speaker_id == true_speaker else 0.2
    
    # 3. 隐私合规性（基于 MemAudit 思路）
    privacy_compliance = 1.0
    if action.action_type == 'QUARANTINE':
        # 正确隔离可疑信息 → 轻微加分
        privacy_compliance = 1.2
    elif measure_cross_speaker_leakage(action, ground_truth) > 0:
        # 错误地将 A 的信息写入 B 的 bucket → 降权
        privacy_compliance = 0.3
    
    # 综合权重
    return usage_weight * attr_accuracy * privacy_compliance
```

**SpeakerTree Credit（TreeMem 扩展）**：

对于 Stage 2/3 的稳定训练阶段，用 TreeMem 风格的树状因果分解替代简单频率计数：

```python
def speaker_tree_credit(trajectory, terminal_reward):
    """
    TreeMem → SpeakerTree：per-speaker 因果信用
    """
    credit_map = defaultdict(float)
    
    # 建立"记忆操作 → 检索 → 答案"的因果链
    for retrieved_fragment in trajectory.retrieved_fragments:
        source_op = find_source_operation(retrieved_fragment, trajectory.ops)
        speaker = source_op.speaker_id
        
        # 被检索的片段对答案质量的贡献
        contribution = mi_estimate(retrieved_fragment.content, trajectory.final_answer)
        credit_map[speaker] += terminal_reward × contribution
    
    # 归一化
    total = sum(credit_map.values()) + 1e-8
    return {s: v / total for s, v in credit_map.items()}
```

---

### 4.5 Three-Stage Training Curriculum

**总体设计原则**：
- Stage 1 提供 warm start（避免冷启动 RL 探索低效）
- Stage 2 优化 memory quality（核心创新）
- Stage 3 端到端任务优化（确保泛化）

#### Stage 1：Speaker-Aware Supervised Fine-Tuning (SFT)

**数据**：自合成多方对话 + GroupMemBench 训练子集（mixed curriculum）

**训练目标**：在标注好 speaker attribution 的 memory 操作序列上做 role-masked CE：

```python
def stage1_sft(data, model):
    """
    Role-masked SFT：只在 memory_agent 的输出 token 上计算 loss
    对话中其他角色的发言不参与梯度
    """
    for batch in data:
        loss = 0
        for token_pos, (token, role) in enumerate(zip(batch.tokens, batch.roles)):
            if role == 'memory_agent':  # 只计算 agent 输出的 loss
                loss += CrossEntropy(model.logits[token_pos], token)
        loss.backward()
    
    # MuPaS 风格：在 SFT 中加入 speaker-role 感知
    # 让模型学会区分"谁说了什么"和"应该记录在谁的 bucket 里"
```

**数据规模**：160 sessions × 20 memory ops = 3,200 (context, action) 对  
**参考**：Curriculum Study 建议 >150 samples 才有 specialization

#### Stage 2：Joint Multi-Agent RL with Speaker-LoGo-GRPO

**训练对象**：memory construction + retrieval + write_policy 三个"角色"（同一模型，不同 prompt template）

**算法**：Speaker-Conditioned LoGo-GRPO（§4.3）+ Contribution-Aware Gradient Weighting（§4.4）

```python
def stage2_joint_rl(data, model, epochs=5):
    for epoch in range(epochs):
        for batch in data:
            # 1. 全局 rollout（G=4）
            # 2. Speaker-conditioned 局部 rerollout
            # 3. Speaker-Aware Levenshtein reward 计算
            # 4. 贡献感知梯度加权更新
            
            loss = speaker_logo_grpo_update(batch, model)
            
            # KL 正则（WebAgent-R1 风格，防 Echo Trap）
            kl_penalty = kl_divergence(model, model_init)
            (loss + β * kl_penalty).backward()
```

**关键超参数**：
- G = 4（Curriculum Study 建议，binary reward 时更多）
- λ = 0.5（LoGo local loss 权重）
- β = 0.01（KL 正则系数）
- 批量大小 = 4 sessions（A100 × 4 可承受）

#### Stage 3：End-to-End Task RL

**算法**：MultiContextGRPO（MemSearcher 风格）

**数据**：GroupMemBench + EverMemBench + SocialMemBench 训练子集（三合一 mixed）

**奖励**：完整 8 组件奖励（以 $R_{\text{task}}$ 为主导）

```python
def stage3_e2e_rl(data, model, epochs=3):
    """
    三个 benchmark 的数据交替训练
    每 100 步在验证集上 eval，保存最佳 checkpoint
    """
    benchmarks = [GroupMemBench_train, EverMemBench_train, SocialMemBench_train]
    
    for epoch in range(epochs):
        for benchmark in benchmarks:
            for batch in benchmark.batches:
                # 完整任务 rollout（包括 QA 回答）
                trajectories = full_task_rollout(batch, model, G=4)
                reward = [reward_v3(t) for t in trajectories]
                advantage = group_relative_advantage(trajectories, reward)
                grpo_update(model, trajectories, advantage)
```

---

### 4.6 整体方法图示

```
输入: 多方对话 Session S_t = {(u_i, speaker_i, audience_i)}
          ↓
[Step 1: Speaker Context Encoding]
  • 识别当前活跃 speaker set
  • 加载每个 speaker 的四维记忆槽（core/epi/sem/ins）
  • 计算 speaker trust scores
          ↓
[Step 2: Memory Action Generation]
  • Prompt: [System] + [Memory State] + [Recent Turns]
  • Action ∈ {WRITE_CORE, WRITE_EPI, ..., QUARANTINE, NOOP}
  • 必须指定 speaker_id + audience_set
          ↓
[Step 3: Action Execution + Trust Check]
  • 执行 action（更新对应 speaker 的 memory slot）
  • Quarantine 检查（低信任 speaker 的信息隔离）
  • Audience 权限检查（READ_CROSS 需要权限验证）
          ↓
[Step 4: SpeakerLev Reward Computation（训练时）]
  • per-speaker 记忆状态差分 F1
  • cross-speaker leakage penalty
  • attribution accuracy score
          ↓
[Step 5: Retrieval for QA]
  • Causal Intervention retrieval（CMI 风格）
  • 考虑 audience 权限：不返回受限记忆
  • 返回 speaker-attributed 记忆片段
          ↓
[Step 6: Response Generation]
  • 基于检索到的 speaker-attributed 记忆生成答案
  • 遵循 audience 规则（不泄露受限信息给错误受众）
          ↓
输出: 答案 + 更新后的记忆状态 M_t
```

---

### 4.7 与竞品的关键技术 Delta

| 维度 | Memory-R1 | AgeMem | DeltaMem | MemBuilder | Mem-T | TreeMem | **SpeakerMem-R1** |
|------|-----------|--------|----------|------------|-------|---------|------------------|
| Setting | dyadic | dyadic | dyadic | dyadic | dyadic | dyadic | **multi-party** |
| Memory structure | key-value | 5-ops | KV | 4-dim | 3-tier | pipeline | **N×4+group** |
| Reward | outcome | step-wise | Levenshtein | dense attr | MoT-tree | tree | **SpeakerLev** |
| Credit | sequential | step | dense | usage freq | tree-BP | tree-causal | **SpeakerTree+LOO** |
| Privacy | none | none | none | none | none | none | **quarantine+trust** |
| Multi-party eval | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓（3 benchmarks）** |

**核心 delta**：所有竞品都是 dyadic，没有 speaker attribution，没有 audience control，没有隐私层。
