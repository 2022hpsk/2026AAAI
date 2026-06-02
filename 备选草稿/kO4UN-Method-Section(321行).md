# SpeakerMem-R1: Method Section 草稿

**版本**：v1（2026-06-01）  
**状态**：草稿，部分结果用 X.X 占位  
**对应 Abstract**：见「迭代V3-新竞品深挖与方案精化.md」Part 6

---

## 3. Problem Formulation

### 3.1 Task Definition

我们考虑多方长期对话记忆管理（Multi-Party Long-Term Conversational Memory Management）任务。

**形式化定义**：
设群聊由 N 个说话人组成 $\mathcal{S} = \{s_1, s_2, \ldots, s_N\}$，对话由 T 个轮次 $\mathcal{D} = \{(t_1, u_1, c_1), \ldots, (t_T, u_T, c_T)\}$ 构成，其中 $t_i$ 为时间戳，$u_i \in \mathcal{S}$ 为说话人，$c_i$ 为内容。

**Memory Agent 的目标**：
在处理对话的同时，维护记忆库 $\mathcal{M}$，使得在任意时刻 $\tau$ 回答关于任意说话人 $s$ 的问题时，能够给出准确答案：

$$\text{argmax}_a \; \mathbb{P}(a = a^* \mid q, s, \mathcal{M}_\tau)$$

其中 $q$ 是问题，$a^*$ 是 ground truth 答案，$\mathcal{M}_\tau$ 是时刻 $\tau$ 的记忆库。

### 3.2 MDP 形式化

我们把多方对话记忆管理建模为 Markov Decision Process（MDP）$(\mathcal{S}_{state}, \mathcal{A}, \mathcal{R}, \mathcal{T}, \gamma)$：

**状态空间** $\mathcal{S}_{state}$：
$$s_t = (\mathcal{D}_{:t}, \mathcal{M}_{t-1}, q)$$
- $\mathcal{D}_{:t}$：到时刻 $t$ 为止的对话历史
- $\mathcal{M}_{t-1}$：上一时刻的记忆库
- $q$：可选的查询问题（在 answer 阶段）

**动作空间** $\mathcal{A}$：
$$\mathcal{A} = \{\text{WRITE}, \text{UPDATE}, \text{DELETE}, \text{SUMMARY}, \text{PROMOTE}, \text{SUPPRESS}, \text{READ\_CROSS}, \text{NOOP}\}$$

关键特性：每个动作携带 `speaker_id`（信息来源）和 `audience_set`（预期受众），反映了多方对话的说话人感知特性：
$$a_t = (action\_type, \text{content}, s_\text{source} \in \mathcal{S}, \mathcal{A}_{target} \subseteq \mathcal{S}, \ell)$$
其中 $\ell \in \mathcal{L}$ 是目标记忆层级（见 §4.1）。

**奖励函数** $\mathcal{R}$：见 §4.3。

### 3.3 多方场景的核心挑战

与 dyadic（两人对话）设定相比，多方场景引入了三个额外挑战：

1. **说话人归属（Speaker Attribution）**：每条信息来自不同说话人，错误归属会导致"张冠李戴"——把 Alice 的偏好记成 Bob 的偏好。

2. **受众适配（Audience Adaptation）**：同一问题对 Alice（直接相关方）和 Bob（旁观者）的回答应不同，AI 助手需要知道"当前在和谁说话"。

3. **信用分配不公平（Unfair Credit Assignment）**：在 N 人群聊中，不同说话人的信息对最终答案的贡献迥异，传统 GRPO 无法精确归因到 speaker 级别。

---

## 4. SpeakerMem-R1

### 4.1 五层说话人感知记忆结构

受 Mem-α（三组件架构）、Collaborative Memory（共享/私有划分）和 G-Memory（三层图层级）启发，我们设计了专门针对多方对话的五层记忆结构：

$$\mathcal{M} = (\mathcal{M}^{core}, \mathcal{M}^{epis}, \mathcal{M}^{prof}, \mathcal{M}^{inter}, \mathcal{M}^{ins})$$

| 层级 | 含义 | 说话人维度 | 类比 |
|------|------|----------|------|
| $\mathcal{M}^{core}[s]$ | 核心事实 | per-speaker | Mem-α 的 core memory |
| $\mathcal{M}^{epis}[s]$ | 情节记忆 | per-speaker | Mem-α 的 episodic memory |
| $\mathcal{M}^{prof}[s]$ | 个人画像 | per-speaker | PersonaMem-v2 的 user profile |
| $\mathcal{M}^{inter}$ | 群组互动 | group-level | G-Memory 的 interaction graph |
| $\mathcal{M}^{ins}$ | 群组洞察 | group-level | G-Memory 的 insight graph |

每个记忆片段 $f$ 包含：
$$f = (\text{content}, s_\text{source}, \mathcal{A}_{audience}, t, \ell, \text{access})$$
其中 $\text{access} \in \{\text{private}, \text{group}, \text{public}\}$ 控制访问权限（参考 Collaborative Memory）。

**与 dyadic 方法的关键区别**：在 Memory-R1 / AgeMem 等 dyadic 方法中，记忆库是 flat list，没有说话人维度。我们的结构**显式建模了每个说话人的独立记忆空间**，使说话人归属成为一等公民。

### 4.2 说话人感知动作空间

标准 memory RL 方法（Memory-R1 / AgeMem）的动作只有 `{ADD, UPDATE, DELETE, NOOP}`，对所有说话人使用相同动作。

我们扩展为：

```
WRITE(content, speaker_id, audience_set, layer)
  → 在指定层写入新记忆片段，明确标记来源说话人和目标受众

UPDATE(fragment_id, new_content)
  → 更新已有片段内容

DELETE(fragment_id)
  → 删除片段（遗忘 / 隐私保护）

SUMMARY(fragment_ids, target_layer)
  → 把多个 episodic 片段摘要为 profile/insight

PROMOTE(fragment_id, from_layer, to_layer)
  → 提升记忆层级（episodic → insight）

SUPPRESS(fragment_id, strength)
  → 弱化记忆强度（受 MOOM 遗忘机制启发）

READ_CROSS(asker_id, target_speaker_id, query)
  → 跨说话人访问受控记忆（受 access 权限约束）

NOOP  → 不执行任何操作
```

**系统提示（System Prompt）格式**：

```
你是多方对话记忆助手，当前群聊有 {N} 位成员：
{speaker_list_with_roles}

对每条新消息，请以 JSON 格式输出记忆操作，例如：
{"action": "WRITE", "content": "Alice 提到她明天有会议",
 "speaker_id": "alice", "audience_set": ["all"], "layer": "per_speaker_episodic"}
{"action": "NOOP"}

记忆管理原则：
1. 始终正确标注每条信息的来源说话人（speaker_id）
2. 避免不同说话人的信息混入同一条记忆片段
3. 群组决策 / 共同行动记录在 group_interaction
```

### 4.3 说话人感知 Levenshtein 奖励（SLR）

**动机**：Memory-R1 等使用稀疏二值奖励（答案对/错），在 G=4 的 GRPO 中 gradient 为 0 的概率高达 40%（Curriculum Study）。DeltaMem 提出用 memory state 与 GT 的 Levenshtein 距离作为 dense reward，但只考虑 dyadic 的整体 state。

我们提出 **Speaker-Aware Levenshtein Reward（SLR）**，把 memory state alignment 细化到每个说话人维度：

**Step 1**：对每个说话人 $s \in \mathcal{S}$，计算预测 memory 和 ground truth memory 的差异：
$$\Delta^{pred}_s = \mathcal{M}_s^{pred} \setminus \mathcal{M}_s^{GT,t-1}, \quad \Delta^{GT}_s = \mathcal{M}_s^{GT,t} \setminus \mathcal{M}_s^{GT,t-1}$$

**Step 2**：用 embedding 模型将 $\Delta^{pred}_s$ 和 $\Delta^{GT}_s$ 中的每个片段嵌入为向量，计算相似度矩阵：
$$\mathbf{C}_s[i,j] = \cos(\mathbf{e}_i^{pred}, \mathbf{e}_j^{GT})$$

**Step 3**：用最优传输（Hungarian Algorithm）求最优一对一匹配，过滤相似度低于阈值 $\tau$ 的匹配对：
$$\mathcal{P}_s^* = \{(i,j) : \text{match}^*(i,j), \mathbf{C}_s[i,j] \geq \tau\}$$

其中 $\tau = 0.6$（参考 DeltaMem 的消融建议）。

**Step 4**：计算每个说话人的 soft F1：
$$\text{F1}_s = \frac{2 \cdot |\mathcal{P}_s^*| / |\Delta^{pred}_s| \cdot |\mathcal{P}_s^*| / |\Delta^{GT}_s|}{|\mathcal{P}_s^*| / |\Delta^{pred}_s| + |\mathcal{P}_s^*| / |\Delta^{GT}_s|}$$

**Step 5**：计算跨说话人信息泄露惩罚（Cross-Speaker Leakage Penalty）：
$$\mathcal{L}_{leak} = \frac{1}{N(N-1)} \sum_{s \neq s'} \max_{(f_s, f_{s'})} \mathbf{1}[\cos(f_s, f_{s'}) > 0.8]$$

**完整 SLR**：
$$R_{SLR} = \frac{1}{|\mathcal{S}|} \sum_{s \in \mathcal{S}} \text{F1}_s - 0.3 \cdot \mathcal{L}_{leak}$$

**与 DeltaMem 的关键区别**：DeltaMem 计算整体 memory state 的 Levenshtein distance，不区分说话人；SLR 在每个说话人维度上独立计算，额外引入跨说话人泄露惩罚。这使得 SLR 能够精确惩罚"张冠李戴"型错误——这是 GroupMemBench 中最常见的失败模式。

### 4.4 完整奖励函数

我们使用六分量奖励：

$$R = R_{task} + \alpha_1 R_{attr} + \alpha_2 R_{SLR} + \alpha_3 R_{aud} + \alpha_4 R_{compr}$$

其中：

- $R_{task}$：token-level F1，$R_{task} = \text{F1}(a_{pred}, a^*)$（不使用 binary EM，参考 Curriculum Study）
- $R_{attr}$：speaker attribution F1，验证每条记忆的说话人标注是否正确
- $R_{SLR}$：Speaker-Aware Levenshtein reward（§4.3）
- $R_{aud}$：受众适配得分，用 LLM-as-a-Judge 评估输出是否对当前受众适配
- $R_{compr}$：压缩奖励，$R_{compr} = \max(0, 1 - |\mathcal{M}| / M_{max})$

权重 $(\alpha_1, \alpha_2, \alpha_3, \alpha_4) = (0.5, 0.8, 0.3, 0.1)$（消融实验中验证）。

注：$R_{SLR}$ 权重最高（0.8），参考 DeltaMem 的发现——state-level dense reward 比 outcome reward 提供更强的训练信号。

### 4.5 说话人条件 LoGo-GRPO 训练

**动机**：Memory-R2 指出，在多 session 训练中，不同 rollout 因各自的 memory 操作不同而导致 intermediate state 发散，使 group-relative advantage 的比较失去公平性。Memory-R2 的 LoGo-GRPO 通过 local rerollout（从 shared intermediate state 分支）解决了这个问题。

然而，在多方场景中，存在更严重的不公平性：**不同 rollout 可能面对来自不同说话人组合的 turn**，即使从同一 intermediate state 出发，也无法保证 local rollout 的"可比性"——因为说话人组合不同。

我们提出 **Speaker-Conditioned LoGo-GRPO（SC-LoGo）**，在 Memory-R2 的 local rerollout 基础上，**额外按说话人子集分层**：

**全局目标（Global Objective）**：
$$\mathcal{L}_{global} = -\mathbb{E}_{\tau \sim \pi_\theta}\left[\hat{A}^\tau \log \pi_\theta(\tau)\right]$$

其中 $\hat{A}^\tau = \frac{R(\tau) - \mu_G}{\sigma_G}$ 是跨 $G_{global}=8$ 条轨迹的 group-relative advantage。

**局部目标（Local Objective）**：

1. 找到对话中间点 $t^* = T/2$
2. 对每个说话人子集 $\mathcal{S}' \subseteq \mathcal{S}$，从 shared intermediate state $\hat{s}_{t^*}$ 出发，重新 rollout $G_{local}=4$ 条轨迹：
   $$\{\tau^l_1, \ldots, \tau^l_{G_{local}}\} \sim \pi_\theta(\cdot | \hat{s}_{t^*}, \mathcal{S}')$$
3. 在 $\mathcal{S}'$ 子集内计算 local advantage：
   $$\hat{A}^l = \frac{R(\tau^l) - \mu_{local}}{\sigma_{local}}$$

$$\mathcal{L}_{local} = \frac{1}{|\{\mathcal{S}'\}|} \sum_{\mathcal{S}'} -\mathbb{E}_{\tau^l \sim \pi_\theta(\cdot|\hat{s}_{t^*}, \mathcal{S}')}\left[\hat{A}^l \log \pi_\theta(\tau^l)\right]$$

**总损失**：
$$\mathcal{L}_{SC-LoGo} = \mathcal{L}_{global} + \lambda \cdot \mathcal{L}_{local}, \quad \lambda = 0.5$$

**Speaker Subset 采样策略**：对 $N > 6$ 的大群聊，随机采样 3 个子集（每个包含 3-5 人），控制计算开销。

**与 Memory-R2 LoGo-GRPO 的区别**：Memory-R2 的 local rerollout 不区分说话人，所有 $G_{local}$ 条轨迹在相同 intermediate state 下但面对相同后续对话；我们进一步按说话人子集分层，确保 local 组内只有"面对相同 speaker 组合"的轨迹才参与比较。

### 4.6 联合多智能体训练 Pipeline

受 CoMAM 启发，我们对 Memory Construction Agent 和 Answer Agent 进行联合训练而非序贯训练：

**三阶段训练**：

**Stage 1：Role-Masked SFT**
- 目的：学会基础 memory 操作格式 + speaker-aware 输出
- 数据：EverMemBench + GroupMemBench（如可用）混合 curriculum
- Loss：$\mathcal{L}_{SFT} = -\sum_{t \in \text{agent tokens}} \log \pi_\theta(a_t | s_{:t})$
  （仅对 memory agent 生成的 token 计算 loss，mask 掉对话输入部分）

**Stage 2：Warm RL**
- 算法：Step-wise GRPO（AgeMem 风格）
- 奖励：$R = R_{task} + 0.5 R_{attr}$（只用稀疏 + attribution，不含 dense SLR）
- 目的：学习 speaker-aware action，建立 memory quality baseline
- Curriculum：8 → 16 → 32 sessions（Memory-R2 风格）

**Stage 3：Full SC-LoGo-GRPO**
- 算法：SC-LoGo-GRPO（§4.5）
- 奖励：完整六分量（§4.4）
- 目的：精细 credit assignment + dense reward 优化
- Joint 训练：Construction Agent 和 Answer Agent 共享参数，用 role-specific prompt 区分

**自适应 Credit 权重（借鉴 CoMAM）**：
$$w_\text{agent} = \text{softmax}(\text{RankCorr}(R_{local}^{agent}, R_{global}) / T)$$
其中 $\text{RankCorr}$ 是 agent 的局部 reward 和全局 reward 的 Spearman 排名相关性，$T$ 是温度参数。相关性高的 agent 获得更大的 credit 权重。

---

## 5. Experiments

### 5.1 实验设置

**Benchmarks**：
1. **EverMemBench**（2602.01313）：2,400 QA pairs，多方协作对话，1M+ token
2. **SocialMemBench**（2605.17789）：1,031 QA pairs，5 类社交网络
3. **GroupMemBench**（2605.14498）：多方群聊，speaker-grounded + audience-adapted

**Baselines**：

| 系统 | 类型 | 特点 |
|------|------|------|
| Mem0 | training-free | CRUD + heuristic |
| A-MEM | training-free | atomic notes + graph |
| Memory-R1* | RL dyadic adapted | 直接迁移到多方 |
| AgeMem* | RL dyadic adapted | 3-stage RL，LTM/STM |
| DeltaMem* | RL + Levenshtein adapted | state diff dense reward |
| Memory-R2* | RL + LoGo adapted | local rerollout |
| CoMAM* | RL + joint adapted | joint multi-agent |
| **SpeakerMem-R1（ours）** | RL multi-party | speaker-grounded |

（*表示将 dyadic 方法直接应用到多方 benchmark，不修改其多方相关设计）

**Metrics**：
- **QA F1**：token-level F1（主指标）
- **Speaker Attribution F1**：记忆片段的说话人标注正确率
- **Audience Adaptation Score**：LLM-judge 评估受众适配（0-1）
- **Memory Efficiency**：总 memory token 数 vs. 正确回答率

**Model**：Qwen2.5-7B-Instruct + LoRA（r=16）  
**Hardware**：4× NVIDIA A100 80GB

### 5.2 主要结果（占位）

**Table 1**：三个 benchmark 上的主要结果

| 方法 | EverMemBench QA F1 | SocialMemBench Score | GroupMemBench F1 | Avg. |
|------|-------------------|---------------------|-----------------|------|
| Mem0 | X.XX | 0.14 | X.XX | X.XX |
| A-MEM | X.XX | 0.15 | X.XX | X.XX |
| Memory-R1* | X.XX | X.XX | X.XX | X.XX |
| AgeMem* | X.XX | X.XX | X.XX | X.XX |
| DeltaMem* | X.XX | X.XX | X.XX | X.XX |
| Memory-R2* | X.XX | X.XX | X.XX | X.XX |
| CoMAM* | X.XX | X.XX | X.XX | X.XX |
| **SpeakerMem-R1** | **X.XX** | **X.XX** | **X.XX** | **X.XX** |

**注**：Mem0 在 SocialMemBench 上的分数来自原论文（0.12-0.18）。

### 5.3 消融实验（占位）

**Table 2**：组件消融

| 变体 | 去掉的组件 | EverMemBench F1 | SocialMemBench |
|------|-----------|----------------|----------------|
| Full（ours） | — | X.XX | X.XX |
| w/o SLR | Speaker-Levenshtein reward | X.XX | X.XX |
| w/o SA-Action | speaker_id/audience 参数 | X.XX | X.XX |
| w/o LoGo | speaker-conditioned rerollout | X.XX | X.XX |
| w/o Joint | sequential 训练 | X.XX | X.XX |
| w/o Curriculum | 只用 EverMemBench | X.XX | X.XX |
| Sparse only | 去掉所有 dense reward | X.XX | X.XX |

**预期关键消融结论**：
- `w/o SLR` 对 speaker attribution F1 下降最大（证明 SLR 的必要性）
- `w/o SA-Action` 导致整体 F1 明显下降（说话人归属是基础能力）
- `w/o LoGo` 对长程对话（EverMemBench）影响更大
- `Sparse only` ≈ Memory-R1*（证明 dense reward 的重要性）

---

## 参考文献占位（写作用）

```bibtex
@article{agemem2026, title={AgeMem}, ...}          % step-wise GRPO
@article{memoryr1_2025, title={Memory-R1}, ...}     % 2-agent RL baseline
@article{memoryr2_2026, title={Memory-R2}, ...}     % LoGo-GRPO
@article{deltamem2026, title={DeltaMem}, ...}       % Levenshtein reward
@article{comam2026, title={CoMAM}, ...}             % joint training
@article{memt2026, title={Mem-T}, ...}              % MoT-GRPO tree
@article{groupmembench2026, title={GroupMemBench}, ...}   % benchmark
@article{socialmembench2026, title={SocialMemBench}, ...} % benchmark
@article{evermembench2026, title={EverMemBench}, ...}     % benchmark
@article{collaborative2025, ...}                    % private/shared memory
@article{gmemory2025, ...}                          % 3-layer graph
@article{mema2025, ...}                             % 3-component arch
@article{hcapo2026, ...}                            % hindsight credit
@article{hiper2026, ...}                            % hierarchical RL
```
