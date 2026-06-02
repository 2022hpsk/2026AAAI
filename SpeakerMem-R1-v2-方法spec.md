# SpeakerMem-R1 v2：完整方法规格书（可实现级别）

**版本**：v2.0（2026-06-02，V3 迭代产出）  
**目标**：为 AAAI 2027 投稿准备，达到 highlight 水准  
**核心定位**：多方群聊对话场景下的 **speaker-aware RL 记忆管理**，首篇在多方 benchmark 上训练 RL memory agent

---

## 1. 问题定义

### 1.1 符号约定

| 符号 | 含义 |
|------|------|
| $S = \{s_1, ..., s_K\}$ | 对话中的 $K$ 个说话人（speaker）集合 |
| $C = (u_1, u_2, ..., u_T)$ | 对话历史，每条 $u_t = (s_k, \text{text}_t)$，带说话人标签 |
| $M$ | 当前记忆状态（5 层结构，见 §2） |
| $q$ | 查询问题（可指定询问者 $s_{ask}$ 和目标 $s_{target}$） |
| $a$ | 模型回答 |
| $A_{mem}$ | Memory Construction Agent（写记忆） |
| $A_{ret}$ | Memory Retrieval Agent（读记忆） |
| $A_{ans}$ | Answer Agent（生成回答） |

### 1.2 任务形式化

**输入**：对话历史 $C$（多方，每条带说话人标签），查询 $q$  
**输出**：答案 $a$

中间状态：
```
C → [A_mem 边读边写 M] → M → [A_ret 检索相关片段] → context → [A_ans 生成] → a
```

**多方与 dyadic 的核心区别**：
1. **归属问题**：每个 fact 必须绑定到说话人，"谁说了什么" 是一等公民
2. **观众适配**：回答策略取决于询问者和目标说话人的关系
3. **访问控制**：某些 fact 对某些说话人不可见（隐私层）
4. **交叉说话人引用**：如 "Alice 提到 Bob 喜欢咖啡" 涉及两个说话人

---

## 2. 记忆数据结构（5 层）

### 2.1 结构定义

```python
@dataclass
class MemoryEntry:
    entry_id: str              # UUID
    content: str               # 记忆文本
    speaker_id: str            # 信息来源说话人
    audience_set: set[str]     # 谁知道这条信息（访问控制）
    layer: str                 # 所属层级（见下）
    turn_created: int          # 创建于第几轮
    confidence: float          # 0~1，RL 学出的确信度
    links: list[str]           # 关联 entry_id（图结构）

class SpeakerAwareMemory:
    """5 层记忆结构，每层用途不同"""
    
    # 层1：per-speaker 核心 facts（永久性，高确信度）
    per_speaker_core: dict[str, list[MemoryEntry]]
    #   key=speaker_id，value=核心 facts（如 "Alice 职业是工程师"）
    
    # 层2：per-speaker 情节记忆（时序性，可遗忘）
    per_speaker_episodic: dict[str, list[MemoryEntry]]
    #   key=speaker_id，value=情节性 facts（如 "Alice 上周提到想换工作"）
    
    # 层3：per-speaker 人格画像（PersonaMem-v2 风格）
    per_speaker_profile: dict[str, list[MemoryEntry]]
    #   key=speaker_id，value=人格 facts（如 "Alice 性格外向，常用反问句"）
    
    # 层4：群组互动记录（多方独有）
    group_interaction: list[MemoryEntry]
    #   audience_set=全体，记录群组级别互动（如 "Alice 和 Bob 有矛盾"）
    
    # 层5：群组洞察（高度压缩的 meta-memory）
    group_insight: list[MemoryEntry]
    #   audience_set=全体，组内主题、共识、张力等（如 "这个群组关注 AI 话题"）
    
    def get_accessible(self, asker_id: str) -> list[MemoryEntry]:
        """返回 asker 有权访问的所有记忆片段"""
        accessible = []
        for layer in [self.per_speaker_core, self.per_speaker_episodic, self.per_speaker_profile]:
            for speaker_id, entries in layer.items():
                for e in entries:
                    if asker_id in e.audience_set or speaker_id == asker_id:
                        accessible.append(e)
        accessible.extend(self.group_interaction + self.group_insight)
        return accessible
```

### 2.2 记忆层选择示例

| 对话内容 | 写入层 | 说明 |
|---------|--------|------|
| Alice："我在字节跳动做 NLP" | per_speaker_core[Alice] | 稳定 fact |
| Alice："上周去了三亚旅游" | per_speaker_episodic[Alice] | 时序性，可老化 |
| Alice 总是用技术术语 | per_speaker_profile[Alice] | 语言风格 |
| "Alice 和 Bob 今天吵架了" | group_interaction | 多方关系事件 |
| "这个群组常讨论 AI 创业" | group_insight | 元洞察 |

---

## 3. Action Space 设计

### 3.1 完整动作集合

```python
class MemoryAction:
    """所有动作都携带 speaker_id 元数据"""
    
    # 写操作
    WRITE = Action(
        content: str,           # 记忆内容
        speaker_id: str,        # 归属说话人
        audience_set: set[str], # 可访问者
        layer: str,             # 目标层级
    )
    
    # 更新操作（修改已有记忆）
    UPDATE = Action(
        entry_id: str,          # 目标记忆 ID
        new_content: str,       # 新内容
        # speaker_id 不变（归属不可修改）
    )
    
    # 删除操作
    DELETE = Action(
        entry_id: str,
        reason: str,            # 删除原因（"outdated"/"wrong"/"merged"）
    )
    
    # 压缩摘要
    SUMMARY = Action(
        entry_ids: list[str],   # 被压缩的 entries
        layer: str,             # 摘要写入层
        speaker_scope: str,     # "per_speaker" 或 "group"
    )
    
    # 晋升（情节 → 核心，如反复出现的信息）
    PROMOTE = Action(
        entry_id: str,
        from_layer: str,        # e.g., "per_speaker_episodic"
        to_layer: str,          # e.g., "per_speaker_core"
    )
    
    # 抑制（MOOM 遗忘机制，不是直接删，而是降权重）
    SUPPRESS = Action(
        entry_id: str,
        strength: float,        # 0~1，遗忘强度
    )
    
    # 跨说话人访问（带访问控制）
    READ_CROSS = Action(
        asker_id: str,          # 谁在查
        target_speaker_id: str, # 查谁的信息
        query: str,
    )
    
    # 空操作（不需要更新时）
    NOOP = Action()
```

### 3.2 Action 选择 Prompt 模板

```
系统提示：
你是一个多方对话记忆管理器。当前说话人 K 人：{speaker_list}。
当前对话轮次 {turn_id}。

当前记忆状态：
[per_speaker_core]: {core_summary}
[per_speaker_episodic]: {episodic_summary}
[group_interaction]: {interaction_summary}

新的对话内容：
{speaker_id}: {utterance}

请决定需要执行的记忆操作。格式如下：
<action>WRITE</action>
<speaker_id>{speaker_id}</speaker_id>
<audience>{audience_set}</audience>
<layer>{layer}</layer>
<content>{fact}</content>

可用操作：WRITE / UPDATE / DELETE / SUMMARY / PROMOTE / SUPPRESS / NOOP
```

---

## 4. 奖励函数设计（v2 完整版）

### 4.1 奖励组件

```python
def compute_reward(
    trajectory: Trajectory,
    ground_truth: GroundTruth,
    speakers: list[str],
) -> float:
    
    # ===== 结果奖励 =====
    # R_task：下游 QA 准确率（token-level F1，避免 binary gradient=0）
    R_task = token_level_F1(trajectory.answer, ground_truth.answer)
    
    # ===== 过程奖励（主导信号，DeltaMem 经验：权重 0.8）=====
    # R_state：speaker-aware Levenshtein state diff（核心创新）
    R_state = speaker_aware_levenshtein_F1(
        pred_memory=trajectory.final_memory,
        gt_memory=ground_truth.memory,
        speakers=speakers
    )
    
    # ===== 多方专属奖励 =====
    # R_attr：说话人归属准确率（哪个 fact 属于哪个 speaker）
    R_attr = speaker_attribution_F1(
        pred_memory=trajectory.final_memory,
        gt_attribution=ground_truth.attribution,
    )
    
    # R_aud：观众适配分（回答是否考虑了询问者视角）
    R_aud = audience_adaptation_score(
        trajectory.answer,
        ground_truth.audience_profiles,
        trajectory.asker_id,
    )
    
    # ===== 结构奖励 =====
    # R_compr：压缩率奖励（避免 memory 无限膨胀，Mem-α 风格）
    R_compr = compression_ratio_reward(trajectory.memory_operations)
    
    # R_RIF：遗忘适当性（MOOM 风格，合理使用 SUPPRESS）
    R_RIF = forgetting_appropriateness(
        trajectory.suppress_ops,
        ground_truth.expected_suppressions,
    )
    
    # ===== 隐私奖励 =====
    # R_priv：访问控制违规惩罚（跨说话人信息泄漏）
    R_leak = -cross_speaker_leakage_penalty(
        trajectory.final_memory,
        ground_truth.privacy_rules,
    )
    
    # ===== 加权合并 =====
    reward = (
        0.5 * R_task           # 最终目标
        + 0.8 * R_state        # 主导 dense signal（DeltaMem 经验）
        + 0.3 * R_attr         # 多方专属：归属准确
        + 0.2 * R_aud          # 多方专属：观众适配
        + 0.1 * R_compr        # 结构质量
        + 0.1 * R_RIF          # 遗忘质量
        + 0.3 * R_leak         # 隐私惩罚（正值代表惩罚额度）
    )
    
    return reward
```

### 4.2 Speaker-aware Levenshtein F1（核心公式详解）

```python
def speaker_aware_levenshtein_F1(
    pred_memory: SpeakerAwareMemory,
    gt_memory: SpeakerAwareMemory,
    speakers: list[str],
    tau: float = 0.6,  # 匹配阈值，敏感性分析建议 0.5~0.7
) -> float:
    """
    Per-speaker bucketed memory state diff.
    
    核心思想：对每个 speaker 单独计算 Δ（状态差），然后平均。
    避免 cross-speaker confusion——不让 Alice 的 facts 被算作 Bob 的 true positive。
    """
    per_speaker_f1 = []
    
    for speaker in speakers:
        # 取 prev_state（turn t-1 的 memory，LoGo local rerollout 时共享此状态）
        prev_pred = get_speaker_entries(pred_memory, speaker, turn="prev")
        prev_gt = get_speaker_entries(gt_memory, speaker, turn="prev")
        
        # 计算 Δ（这一 turn 的增量）
        delta_pred = delta_entries(pred_memory, speaker) - prev_pred
        delta_gt = delta_entries(gt_memory, speaker) - prev_gt
        
        # Embedding 相似度矩阵
        embeddings_pred = embed(delta_pred)  # shape: (|Δ_pred|, dim)
        embeddings_gt = embed(delta_gt)      # shape: (|Δ_gt|, dim)
        
        sim_matrix = cosine_similarity(embeddings_pred, embeddings_gt)
        
        # Optimal transport 匹配（Hungarian algorithm）
        row_ind, col_ind = linear_sum_assignment(-sim_matrix)
        
        # 阈值过滤（低相似度对不算 TP）
        valid_pairs = [
            (r, c) for r, c in zip(row_ind, col_ind)
            if sim_matrix[r, c] >= tau
        ]
        
        # 加 local lexical fidelity（DeltaMem 的关键细节）
        # 检查 pred entry 是否包含 gt entry 的关键词
        lexical_bonus = sum(
            keyword_coverage(delta_pred[r], delta_gt[c])
            for r, c in valid_pairs
        ) / max(len(valid_pairs), 1)
        
        # soft-precision & soft-recall → F1
        tp = len(valid_pairs)
        soft_precision = tp / max(len(delta_pred), 1) * (1 + 0.1 * lexical_bonus)
        soft_recall = tp / max(len(delta_gt), 1)
        
        if soft_precision + soft_recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * soft_precision * soft_recall / (soft_precision + soft_recall)
        
        per_speaker_f1.append(f1)
    
    # 平均（也可以加权，重要 speaker 给高权）
    return sum(per_speaker_f1) / len(per_speaker_f1)


def cross_speaker_leakage_penalty(
    pred_memory: SpeakerAwareMemory,
    privacy_rules: dict,  # {speaker_id: list[forbidden_recipient_ids]}
) -> float:
    """
    惩罚 cross-speaker information leakage：
    Alice 的私密信息不应出现在只有 Bob 可见的 memory 中。
    """
    penalty = 0.0
    for entry in pred_memory.all_entries():
        owner = entry.speaker_id
        for recipient in entry.audience_set:
            if recipient in privacy_rules.get(owner, []):
                # 违规：owner 的信息泄漏给 forbidden recipient
                penalty += 1.0
    # 归一化到 [0,1]
    total_entries = len(pred_memory.all_entries())
    return penalty / max(total_entries, 1)
```

### 4.3 奖励权重消融实验设计

| 消融实验 | R_task | R_state | R_attr | R_aud | R_leak |
|---------|--------|---------|--------|-------|--------|
| E1：仅结果 | 1.0 | 0 | 0 | 0 | 0 |
| E2：+state diff | 0.5 | 0.8 | 0 | 0 | 0 |
| E3：+attribution | 0.5 | 0.8 | 0.3 | 0 | 0 |
| E4：+audience | 0.5 | 0.8 | 0.3 | 0.2 | 0 |
| E5：+privacy（full）| 0.5 | 0.8 | 0.3 | 0.2 | 0.3 |

预期：E5 > E4 > E3 > E2 > E1，且 R_state 的贡献最大（主 delta 来源）

---

## 5. 训练算法：SpeakerMem-GRPO（三阶段）

### 5.1 Stage 1：Speaker-Conditioned SFT（热启动）

```python
def stage1_sft(
    model: LLM,  # Qwen3-8B（V3 更新：DeltaMem 用 Qwen3 系列，便于对齐比较）
    # 备选：Qwen-2.5-7B（更常见的 baseline）
    data: Dataset,  # 合成多方训练数据（V3 更新：三大 benchmark 无训练集！）
):
    """
    目标：让模型学会 multi-party dialogue parsing 和 memory action 格式。
    
    ⚠️ V3 重要更新：GroupMemBench/EverMemBench/SocialMemBench 均无训练集！
    训练数据需要合成（见 §5.4 训练数据合成方案）。
    
    核心贡献1：Speaker-Aware Fact Extraction（基于 Memory-R2 消融发现）
    - Memory-R2 消融：仅训练 Fact Extractor F1=28.30，说明 extraction 是命脉
    - 多方场景 extraction 更难（attribution 歧义）
    - 我们用 speaker-masked CE 专门训 speaker-attributed fact extraction
    """
    for batch in data:
        # 输入：多方对话历史（带 speaker 标签）
        # 输出：speaker-attributed fact extractions + memory ops + QA 回答
        
        # Speaker-aware loss masking：重点在 attribution 正确性
        loss = speaker_masked_CE(
            model_output=model(batch.input),
            target=batch.memory_ops,
            speaker_mask=batch.speaker_assignments,
        )
        
        # 数据规模：200 条合成多方对话（V3 更新，见 §5.4）
        
        optimizer.step(loss)
```

### 5.2 Stage 2：Joint Multi-Agent RL（核心阶段）

```python
def stage2_joint_rl(
    policy: LLM,  # 同一个 model 扮演 A_mem + A_ret + A_ans
    data: Dataset,
):
    """
    受 CoMAM 启发：joint 训练 construction + retrieval + answer，而非 sequential。
    受 Memory-R2 启发：LoGo speaker-conditioned local rerollout。
    """
    for batch in data:
        # === Global branch（完整 trajectory）===
        global_trajs = rollout_G_trajectories(
            policy=policy,
            prompt=batch.dialogue,
            G=4,  # rollout 数，Curriculum Study: G=4 时 binary EM 梯度消失，必须用 F1
        )
        global_rewards = [compute_reward(t, batch.gt, batch.speakers) for t in global_trajs]
        global_advantages = group_relative(global_rewards)
        L_global = grpo_loss(global_trajs, global_advantages)
        
        # === Speaker-conditioned Local branch（Memory-R2 升级）===
        L_local = 0.0
        for traj in global_trajs:
            # 在 trajectory 中期选取"shared intermediate state"
            for checkpoint in traj.intermediate_states[::2]:  # 每隔 2 步取一次
                
                # 按说话人集合分组：同一 speaker_set 内的 rerollout 才做 local 比较
                # 这是对 Memory-R2 的"speaker-conditioned"扩展
                speaker_set = infer_active_speakers(checkpoint.context)
                
                local_rollouts = rollout_from_state(
                    policy=policy,
                    state=checkpoint,
                    G_local=4,
                    speaker_condition=speaker_set,  # 关键扩展
                )
                local_rewards = [
                    compute_reward(r, batch.gt, batch.speakers) 
                    for r in local_rollouts
                ]
                local_advantages = group_relative(local_rewards)
                L_local += grpo_loss(local_rollouts, local_advantages)
        
        # === Joint loss（CoMAM 启发：不同 agent role 共享梯度）===
        L_total = L_global + lambda_logo * L_local + beta_kl * KL_penalty(policy)
        #                    ↑ λ≈0.3 初始，可 tune   ↑ 防止 Echo Trap（WebAgent-R1）
        
        optimizer.step(L_total)
```

### 5.3 Stage 3：多方 Benchmark 端到端 Fine-tune

```python
def stage3_end2end_rl(
    policy: LLM,
    eval_benchmarks: list,  # [GroupMemBench, EverMemBench, SocialMemBench]
):
    """
    借鉴 MemSearcher 的 multi-context GRPO：
    同一 policy 在多个不同 benchmark 上混合训练，防止 single-benchmark 过拟合。
    """
    for batch in mixed_curriculum_sampler(eval_benchmarks, ratio=[0.5, 0.3, 0.2]):
        trajs = rollout_G_trajectories(policy, batch, G=8)
        rewards = compute_reward(trajs, batch.gt, batch.speakers)
        advantages = group_relative(rewards)
        
        L = grpo_loss_with_format_penalty(trajs, advantages)
        # format_penalty：强制模型输出合法的 WRITE/UPDATE/... action 格式
        
        optimizer.step(L)
        
        # 定期评估（每 100 step）
        if step % 100 == 0:
            eval_and_log(policy, eval_benchmarks)
```

---

## 6. 训练配置（超参数规格）

```yaml
# SpeakerMem-R1 v2 Training Config（V3 更新）

base_model: Qwen3-8B  # V3 更新：DeltaMem 用 Qwen3-8B，便于直接比较
# 替代方案 1: Qwen-2.5-7B（更常见 baseline，适合 ablation）
# 替代方案 2: LLaMA-3.1-8B-Instruct

# ⚠️ V3 关键更新：三大多方 benchmark 均无训练集！
# 训练数据完全依赖合成（见 §5.4）
training_data:
  source: synthetic_multi_party  # GPT-4 合成 + LoCoMo speaker扩增
  total_size: 200  # 合成对话条数（参考 Curriculum Study 的 150 条阈值）
  composition:
    - gpt4_close_friends: 50    # 3-5 人社交场景
    - gpt4_workplace_team: 50   # 4-8 人职场场景
    - gpt4_interest_community: 50  # 3-6 人兴趣社群
    - locomo_triadic_augment: 50   # LoCoMo dyadic → triadic 扩增

peft:
  method: LoRA
  r: 32
  alpha: 64
  target_modules: [q_proj, v_proj, k_proj, o_proj, gate_proj, up_proj, down_proj]
  dropout: 0.05

curriculum:
  # V3 更新：结合 Memory-R2 的 session 递进 + 说话人数递进
  stage1: {K_speakers: 3, sessions: 8,  data_subset: "3-speaker subset"}
  stage2: {K_speakers: 5, sessions: 16, data_subset: "3-5 speaker mix"}
  stage3: {K_speakers: 8, sessions: 32, data_subset: "full 3-8 speaker"}

training:
  stage1_sft:
    epochs: 3
    batch_size: 8
    lr: 2e-4
    data_size: 200
    focus: speaker_attributed_fact_extraction  # V3 核心：extraction 优先
    
  stage2_joint_rl:
    steps: 1000
    batch_size: 4
    G_global: 4
    G_local: 4
    lambda_logo: 0.3     # 待 tune（Memory-R2 未公开精确值）
    beta_kl: 0.01
    lr: 1e-5
    adaptive_credit: rank_consistency  # CoMAM 风格 per-speaker credit
    
  stage3_final:
    steps: 500
    G: 8
    eval: [GroupMemBench_test, EverMemBench_test, SocialMemBench_test]
    lr: 5e-6

reward:
  R_task_weight: 0.5
  R_state_weight: 0.8
  R_attr_weight: 0.3      # 说话人归属（对应 GroupMemBench attribution 失败）
  R_aud_weight: 0.2
  R_compr_weight: 0.1
  R_RIF_weight: 0.1
  R_leak_weight: 0.3
  tau: 0.6                # Levenshtein 阈值，建议消融 [0.45, 0.75]
  tau_mode: per_speaker   # V3 新增：per-speaker τ calibration
  use_token_f1: true      # 必须 true，避免 binary EM gradient=0

hardware:
  gpus: 4 × A100-80GB
  estimated_stage1_time: 2h
  estimated_stage2_time: 12h
  estimated_stage3_time: 6h
  total_estimated: ~20h
  
  # Qwen3-8B + LoRA r=32 + G=4
  model_memory: ~18GB per GPU
  rollout_buffer: ~8GB per GPU  
  total_vram: ~104GB（4 卡 A100 满足）
```

---

## 7. 评测设计

### 7.1 主实验：三大多方 Benchmark

| Benchmark | 测试维度 | 报告指标 |
|-----------|---------|---------|
| GroupMemBench | speaker attribution, temporal, group relations | EM, F1, attribution acc |
| EverMemBench | 长程记忆（1M+ token），多 session | Recall@K, F1 |
| SocialMemBench | 5 类社交记忆失败模式 | per-category acc |

### 7.2 兼容性测试（Dyadic）

| Benchmark | 目的 |
|-----------|------|
| LoCoMo | 验证不损害 dyadic 能力 |
| PersonaMem-v2 | 验证 speaker profile 效果 |

### 7.3 Baseline 清单（必须复现）

| Baseline | 来源 | 意义 |
|---------|------|------|
| BM25 retrieval | GroupMemBench 论文 | 强 retrieval baseline |
| Mem0（training-free） | Mem0 论文 | 强 training-free 上限 |
| Memory-R1 | 原论文 | RL memory baseline |
| AgeMem | AgeMem 论文 | Step-wise GRPO baseline |
| DeltaMem | DeltaMem 论文 | Dense reward baseline |
| Memory-R2 | Memory-R2 论文 | LoGo GRPO baseline |
| CoMAM | CoMAM 论文 | Joint RL baseline |

### 7.4 消融实验清单

| 实验编号 | 消融内容 | 验证目的 |
|---------|---------|---------|
| A1 | 去掉 R_state（仅 R_task）| 验证 dense state reward 的贡献 |
| A2 | 去掉 speaker-bucketing（global Levenshtein）| 验证 per-speaker 分桶的贡献 |
| A3 | 去掉 LoGo local branch | 验证 Memory-R2 局部信用分配的贡献 |
| A4 | 去掉 speaker-conditioned（普通 LoGo）| 验证 speaker-conditioned 扩展的贡献 |
| A5 | sequential vs joint training | 验证 CoMAM joint 训练的贡献（关键）|
| A6 | 5-layer vs flat memory | 验证层次化记忆的贡献 |
| A7 | with vs without privacy R_leak | 验证访问控制奖励的贡献 |

---

## 8. 论文 Frame 设计

### 8.1 统一概念：Speaker-Grounded Learnable Structured Memory

所有技术组件围绕一个统一问题：

> "如何让记忆操作理解 who-talked-to-whom-about-what，并通过强化学习提升这种理解？"

- **Grounded**：每个 memory entry 绑定说话人（grounded in speaker）
- **Learnable**：通过 RL 学习 memory policy，而非 heuristic 规则
- **Structured**：5 层层次化结构，不同类型信息分层存储

### 8.2 AAAI 写作结构

```
Title: SpeakerMem-R1: Reinforcement Learning for Speaker-Grounded Memory 
       Management in Multi-Party Conversations

Abstract（4 句话）：
1. 问题：多方群聊记忆面临 speaker attribution 失败和 dyadic 方法不可迁移
2. 方法：Speaker-Grounded RL Memory，5 层结构 + joint GRPO + speaker-aware Levenshtein
3. 实验：GroupMemBench/EverMemBench/SocialMemBench 上超越所有 baseline
4. 贡献：首篇多方 RL memory paper，开源 + 数据集

Introduction（5 段）：
1. 多方群聊 AI 的重要性（工业应用动机）
2. 现有工作的 gap：dyadic-only + benchmark 已有但方法空白
3. 我们的方案概述
4. 三大技术贡献（明确 delta vs Memory-R1/AgeMem/CoMAM/DeltaMem/Memory-R2）
5. 实验结果预告

Method（5 小节）：
1. 5-layer memory 结构
2. action space（带 speaker 元数据）
3. speaker-aware Levenshtein reward（核心贡献）
4. Speaker-conditioned LoGo-GRPO（核心贡献）
5. 3-stage training pipeline

Experiments（5 小节）：
1. Setup（三 benchmark + baseline 清单）
2. 主实验结果
3. 消融实验（7 项）
4. 分析：attribution 失败率、privacy 泄漏率
5. Case study（2-3 个具体群聊例子）

Related Work（4 段）：
1. Memory-augmented LLM agents
2. RL for memory（Memory-R1 线）
3. Multi-party dialogue understanding
4. Memory benchmarks
```

### 8.3 差异化陈述（应对 "incremental" 质疑）

核心论点：**setting 的差异不是 incremental，而是产生了真正新的技术挑战**

| 技术挑战 | dyadic 中不存在 | 多方中存在 |
|---------|---------------|-----------|
| Speaker attribution | ✗ | ✓（GroupMemBench 失败率高） |
| Audience adaptation | ✗ | ✓（谁问谁的信息） |
| Cross-speaker leakage | ✗ | ✓（隐私层设计） |
| State diff divergence | 1 维度 | K 维度（K 个 speaker） |
| LoGo branching factor | 1 | K × session_count |

---

## 9. 风险缓解与 Plan B（V3 更新）

| 风险 | V2 概率 | V3 概率 | V3 缓解方案 |
|------|---------|---------|------------|
| 三大 benchmark 无 train split | 高 | **已确认为高** | ✅ 合成训练数据（§5.4）|
| RL 不收敛（多方更难） | 中 | 中 | dense state reward + SFT warm-start + K=3 简化版 |
| Memory-R2/CoMAM 出多方扩展 | 低 | **仍然低** | V3 确认截至 2026/6/2 仍无多方 RL 论文 |
| AAAI 2027 截止太早 | 高 | 高 | Plan B: EMNLP 2027 |
| "incremental"质疑 | 中 | 中 | §8.3 论证 + 5 类失败模式 hook |
| 三篇竞品代码无法复现 | 低 | **已确认为中** | 三篇均无代码，需自实现；但也意味着 reviewer 更难 reproduce baseline |

---

## 10. 训练数据合成方案（V3 新增）

### 10.1 数据合成 Pipeline

```python
# 多方对话训练数据合成
SYNTHESIS_SYSTEM_PROMPT = """
你是一个专业的多方对话数据标注专家。
生成一段多方群聊对话，同时提供记忆管理的标注数据。
"""

SYNTHESIS_USER_PROMPT = """
生成一段{K}人群聊对话：
- 说话人：{speaker_list}（各有 persona 描述）
- 对话场景：{scene_type}
- 对话轮次：{T}轮
- 必须包含：
  * 每个说话人的 2-3 个核心 facts（工作/爱好/状态/关系）
  * 至少 1 个时态变化（如"之前...，现在..."）
  * 至少 1 个跨说话人引用（如"Alice 说 Bob 喜欢..."）
  * 至少 1 个隐私场景（某人不想被某人知道某事）

输出格式：
{dialogue}  # 对话内容，带说话人标签
{memory_gt}  # Ground truth memory，按 speaker 分桶
{qa_pairs}   # 3 个测试 QA，含答案和来源记忆片段
"""

# 场景类型（对应三大 benchmark 场景）
SCENE_TYPES = {
    'close_friends': "朋友圈群聊，话题随意，关系亲密",
    'workplace_team': "工作项目群，话题专业，有层级关系",
    'interest_community': "兴趣社群，话题集中，成员来源多样",
    'family_group': "家庭群，长辈/晚辈混合，信息跨代",
}

# 目标数据分布
TARGET_DISTRIBUTION = {
    'close_friends': 50,    # 对应 SocialMemBench
    'workplace_team': 50,   # 对应 EverMemBench
    'interest_community': 50,  # 对应 GroupMemBench
    'locomo_augmented': 50,  # LoCoMo dyadic → triadic
}
```

### 10.2 数据质量验证

合成后的数据需要通过以下验证：

| 验证项 | 标准 | 工具 |
|-------|------|------|
| 每条 GT memory 至少 3 个 facts/speaker | 计数 | 规则检查 |
| Attribution 歧义率（某 fact 被多人讨论）| 人工抽样 10% | 人工 |
| QA 答案必须依赖 memory 而非 commonsense | GPT-4 judge | LLM-judge |
| Speaker 标签一致性 | 自动检查 | 规则 |

---

## 11. 近期 Next Action 计划（V3 版本）

### 优先级 1（本周完成）
- [ ] 确认 EverMemBench GitHub 能否下载评测集（https://github.com/EverMind-AI/EverMemBench）
- [x] **已确认**：GroupMemBench/SocialMemBench 无训练集 → 转合成方案
- [ ] 实现 speaker_aware_levenshtein_F1 函数（§4.2）
- [ ] 跑 BM25 baseline on GroupMemBench 验证基准数字

### 优先级 2（两周内完成）
- [ ] 合成 50 条 close_friends 场景对话（测试 pipeline）
- [ ] SFT stage 1 with 50 条（早期验证 speaker-attributed extraction 是否 work）
- [ ] 跑 Mem0/Memory-R1（复现 dyadic）on GroupMemBench

### 优先级 3（一个月内完成）
- [ ] 扩展到 200 条合成数据
- [ ] Stage 2 joint RL（验证 joint > sequential）
- [ ] 比较 Qwen3-8B vs Qwen-2.5-7B 作为 base model 的效果

---

## 12. 论文核心贡献重定位（V3 更新）

基于 Memory-R2 消融发现（fact extraction 是命脉），重定位我们的核心贡献：

### 旧 framing（V2）
> "我们把 dyadic RL memory 扩展到多方对话"

### 新 framing（V3）
> "多方对话记忆管理的根本挑战是 speaker-attributed fact extraction——谁说的、说给谁听的、在什么语境下说的。我们是**第一个用 RL 训练这一核心能力**的工作，并将整个 pipeline（extraction → management → retrieval）在说话人感知的联合框架下统一训练。"

**为什么这个 framing 更强**：
1. 有 Memory-R2 消融作为 backing（extraction 是 pipeline 命脉）
2. 有 GroupMemBench/SocialMemBench 数字作为动机（attribution 类失败率最高）
3. 明确的技术 delta（speaker grounding 是新的第一公民，不只是"扩展"）
4. 更难被 reviewer 质疑"incremental"（因为我们在最关键的组件上做了质的改变）

---

*文档版本 v2.1 | 2026-06-02 | V3 迭代更新（训练数据方案 + 核心贡献重定位）*
