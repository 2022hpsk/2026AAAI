# 多方对话数据合成 Pipeline 设计
**版本**：v1（2026-06-01）  
**用途**：为 SpeakerMem-R1 SFT 热启动阶段提供训练数据  
**目标**：合成高质量多方对话 + speaker-attributed memory 操作标注，数量 >150 条（参考 Curriculum Study 拐点）

---

## 1. 为什么需要数据合成

### 1.1 现有 benchmark 的局限

- **GroupMemBench**：目前 benchmark-only，训练集未明确 → 需要确认
- **EverMemBench**：2,400 QA，但主要用于评测，训练集待确认
- **SocialMemBench**：CC BY 4.0，有 348 sessions，但 memory operation 标注未知

**关键问题**：即使有 benchmark 的训练集，这些数据中通常只有 QA pairs（问题+答案），**没有 memory 操作序列标注**（模型在每个 turn 应该执行哪个 WRITE/UPDATE/DELETE）。SFT 需要的是 (对话上下文, memory 操作) 对。

### 1.2 合成的目标格式

每个训练样本格式：
```json
{
  "session_id": "s001",
  "speakers": ["Alice", "Bob", "Charlie"],
  "conversation": [
    {"turn": 1, "speaker": "Alice", "utterance": "...", "audience": ["all"]},
    {"turn": 2, "speaker": "Bob", "utterance": "...", "audience": ["Alice", "Charlie"]},
    ...
  ],
  "memory_operations": [
    {"after_turn": 1, "action": "WRITE_EPISODIC", "content": "...", "speaker_id": "Alice", "audience_set": ["all"], "reason": "..."},
    {"after_turn": 2, "action": "WRITE_CORE", "content": "...", "speaker_id": "Bob", "audience_set": ["Alice", "Charlie"], "reason": "..."},
    ...
  ],
  "ground_truth_memory": {
    "Alice": {"core": [...], "episodic": [...], "semantic": [...], "insight": [...]},
    "Bob": {"core": [...], ...},
    ...
  },
  "evaluation_qa": [
    {"question": "What is Alice's current job?", "speaker_context": "Alice", "answer": "..."},
    ...
  ]
}
```

---

## 2. Pipeline 设计

### 2.1 总体架构

```
Step 1: Speaker Profile 生成
    ↓
Step 2: 场景设定生成（群组类型 + 话题）
    ↓
Step 3: 多轮对话合成（用 LLM 模拟多 speaker 对话）
    ↓
Step 4: Memory 操作标注（用 LLM 生成 expert memory actions）
    ↓
Step 5: Ground Truth Memory 构建
    ↓
Step 6: QA 对生成（用于 evaluation）
    ↓
Step 7: 质量过滤（自动 + 人工采样检查）
```

### 2.2 Step 1：Speaker Profile 生成

参考 SocialMemBench 的 5 种 archetype，为每个合成对话设定 3-6 个 speaker：

```python
SPEAKER_ARCHETYPES = {
    "professional_team": {
        "size": (3, 6),
        "roles": ["manager", "engineer", "designer", "analyst"],
        "typical_topics": ["project status", "deadlines", "technical decisions"],
        "relationship_patterns": ["hierarchical", "peer", "cross-functional"]
    },
    "friend_group": {
        "size": (3, 8),
        "roles": ["old_friend", "new_friend", "common_connector"],
        "typical_topics": ["weekend plans", "relationships", "personal news"],
        "relationship_patterns": ["close", "casual", "strained"]
    },
    "family": {
        "size": (3, 6),
        "roles": ["parent", "child", "sibling", "partner"],
        "typical_topics": ["family events", "decisions", "concerns"],
        "relationship_patterns": ["supportive", "tense", "absent"]
    },
    "online_community": {
        "size": (4, 12),
        "roles": ["frequent_poster", "lurker", "moderator", "newcomer"],
        "typical_topics": ["hobby", "recommendations", "events"],
        "relationship_patterns": ["acquaintance", "mentor-student", "antagonistic"]
    }
}

def generate_speaker_profiles(archetype, n_speakers, llm):
    """
    用 LLM 为每个 speaker 生成：
    - 姓名（多样化）
    - 背景（职业/年龄/关系）
    - 核心性格特征（3-5 条）
    - 已知事实（5-10 条 core memory seed）
    - 与其他 speaker 的关系（显性/隐性）
    """
    prompt = f"""
    Generate {n_speakers} realistic speaker profiles for a {archetype} group.
    Each profile should include:
    - name, age, occupation
    - personality traits (3 traits)
    - background facts (5 facts that may come up in conversation)
    - relationships to other speakers
    
    Make the profiles realistic and diverse. Include some tension/conflict for interest.
    Return as JSON.
    """
    return llm(prompt)
```

### 2.3 Step 2：场景设定生成

每个场景需要：
- 群组类型（来自 archetype）
- 初始 context（为什么大家在一起聊天？）
- 话题流（3-5 个话题，允许跨话题引用）
- 关键 memory challenge（要触发某个 memory 失败模式）

```python
MEMORY_CHALLENGES = [
    "speaker_attribution_ambiguity",    # 让两个 speaker 说类似的事
    "belief_revision",                   # 某 speaker 的信念在对话中改变
    "audience_sensitive_info",          # 某信息只对部分 speaker 可见
    "cross_reference_fact",             # 需要关联多 speaker 的信息才能回答
    "coexisting_similar_facts",         # 多人有类似但不同的偏好/事实
    "conditional_group_fact",           # 群体共识有条件约束
    "speaker_trust_violation",          # 某 speaker 说了不可信的信息
]

def generate_scenario(archetype, speaker_profiles, target_challenge, llm):
    prompt = f"""
    Create a realistic {archetype} group chat scenario for {len(speaker_profiles)} people.
    
    Speaker profiles:
    {json.dumps(speaker_profiles, indent=2)}
    
    Target memory challenge: {target_challenge}
    
    Generate:
    1. Context (why are they chatting?)
    2. 3-5 conversation topics in sequence
    3. A subtle challenge of type {target_challenge} that should occur naturally
    
    Return as JSON with fields: context, topics, challenge_description
    """
    return llm(prompt)
```

### 2.4 Step 3：多轮对话合成

使用多 Agent 模拟对话：

```python
def simulate_multi_party_conversation(speaker_profiles, scenario, n_turns, llm):
    """
    每个 turn：
    1. 随机选择（或按 scenario 安排）一个 speaker
    2. 给该 speaker 的 LLM 实例发送 [system_prompt + speaker_profile + conversation_history]
    3. 生成该 turn 的 utterance
    4. 有时添加 audience restriction（"private" to subset）
    """
    conversation = []
    
    for turn_idx in range(n_turns):
        # 选择当前发言的 speaker（可以按照 scenario 的 topic 顺序）
        current_speaker = select_next_speaker(scenario, turn_idx, conversation)
        audience = determine_audience(scenario, turn_idx, current_speaker)
        
        # 生成发言
        utterance = llm(
            system=f"You are {current_speaker['name']}. {current_speaker['personality']}",
            context=format_conversation_history(conversation, current_speaker, audience),
            instruction="Say your next message naturally. Keep it realistic."
        )
        
        conversation.append({
            "turn": turn_idx + 1,
            "speaker": current_speaker['name'],
            "utterance": utterance,
            "audience": audience
        })
    
    return conversation
```

### 2.5 Step 4：Memory 操作标注（关键步骤）

这是最复杂的步骤。使用 GPT-4 / Claude 作为"expert memory annotator"：

```python
MEMORY_ANNOTATION_PROMPT = """
You are an expert memory management system for multi-party conversations.

TASK: After reading the conversation so far, generate the memory operations that a 
perfect memory agent would perform to maintain speaker-grounded structured memory.

CURRENT MEMORY STATE:
{current_memory}

NEW CONVERSATION TURNS:
{new_turns}

SPEAKER PROFILES:
{speaker_profiles}

Generate memory operations in JSON format. For each operation, specify:
- action: one of [WRITE_CORE, WRITE_EPISODIC, WRITE_SEMANTIC, WRITE_INSIGHT, UPDATE, DELETE, SUMMARY, PROMOTE, QUARANTINE, NOOP]
- content: the memory content (specific, not vague)
- speaker_id: which speaker this information is ABOUT (not who said it, but who the fact is about)
- audience_set: which speakers can see this memory (use "all" or list specific speaker names)
- reason: brief explanation of why this operation is needed
- priority: 1 (high) / 2 (medium) / 3 (low)

IMPORTANT RULES:
1. Always attribute facts to the correct speaker (be speaker-specific)
2. Respect audience restrictions when speaker said "just between us"
3. Write CORE for stable identity facts, EPISODIC for specific events, SEMANTIC for general preferences
4. QUARANTINE any information that seems unreliable or contradicts prior knowledge
5. Do NOT over-write—only record what's actually new or changed
6. If two speakers made contradictory claims, record both with speaker attribution

Return a JSON array of operations.
"""

def annotate_memory_operations(conversation, speaker_profiles, llm='gpt-4o'):
    """
    分段标注：每 3-5 turns 做一次标注
    保持 rolling memory state（用于条件化后续标注）
    """
    current_memory = initialize_empty_memory(speaker_profiles)
    all_operations = []
    
    for batch_start in range(0, len(conversation), BATCH_SIZE):
        batch = conversation[batch_start:batch_start + BATCH_SIZE]
        
        ops = llm(MEMORY_ANNOTATION_PROMPT.format(
            current_memory=format_memory(current_memory),
            new_turns=format_turns(batch),
            speaker_profiles=json.dumps(speaker_profiles)
        ))
        
        # 更新 rolling memory state
        current_memory = apply_operations(current_memory, ops)
        all_operations.extend(ops)
    
    return all_operations, current_memory  # current_memory = ground truth
```

### 2.6 Step 5：QA 对生成

生成覆盖三类评估维度的 QA：

```python
QA_TYPES = {
    "speaker_attribution": [
        "What did {speaker} say about {topic}?",
        "Who mentioned {fact}?",
        "What is {speaker}'s position on {topic}?"
    ],
    "audience_adaptation": [
        "If you were responding to {speaker}, what information about {other_speaker} can you share?",
        "What can {speaker} know about {topic} based on what was discussed?"
    ],
    "group_dynamics": [
        "Do {speaker_a} and {speaker_b} agree on {topic}?",
        "What is the general group consensus on {topic}?",
        "Who has changed their opinion during this conversation?"
    ],
    "fact_retrieval": [
        "What is {speaker}'s {attribute}?",
        "Has {speaker} mentioned {specific_fact_seed}?"
    ]
}
```

---

## 3. 数据规模目标

参考 Curriculum Study 的建议（150 条是 specialization 拐点）：

| 类型 | 数量 | 用途 |
|------|------|------|
| 专业团队场景 | 50 sessions | professional domain |
| 朋友群组场景 | 50 sessions | casual domain |
| 家庭场景 | 30 sessions | family domain |
| 在线社群场景 | 30 sessions | online domain |
| **总计** | **160 sessions** | SFT 热启动 |

每个 session：
- 3-6 speakers
- 20-40 turns
- 10-30 memory operations
- 5-15 QA pairs

**合计**：约 160 × 25 = 4,000 training turns，160 × 20 = 3,200 memory op labels，160 × 10 = 1,600 QA pairs

---

## 4. 质量控制

### 4.1 自动过滤规则

```python
def quality_filter(sample):
    checks = [
        # Speaker attribution 一致性
        all(op['speaker_id'] in sample['speakers'] for op in sample['memory_operations']),
        # 不过度写入（每5轮最多5个操作）
        len(sample['memory_operations']) / len(sample['conversation']) < 0.5,
        # 对话长度合理
        15 <= len(sample['conversation']) <= 50,
        # 至少 3 种不同 action 类型
        len(set(op['action'] for op in sample['memory_operations'])) >= 3,
        # QA 答案能从 ground truth memory 中找到
        all(answer_in_memory(q, sample['ground_truth_memory']) for q in sample['evaluation_qa'])
    ]
    return all(checks)
```

### 4.2 人工采样验证（20%）

随机抽取 20% 的样本人工检查：
1. Speaker attribution 是否准确？
2. audience_set 是否合理？
3. 对话是否自然？（不要太 artificial）
4. memory 操作是否 complete（没有遗漏重要事实）？

---

## 5. Mixed Curriculum 策略

参考 Curriculum Study（2605.23067）的建议：

### 5.1 混合策略

```python
MIXED_CURRICULUM = {
    "GroupMemBench_train": 0.3,    # 使用 GroupMemBench 官方训练子集（如有）
    "EverMemBench_train": 0.2,     # 使用 EverMemBench 官方训练子集（如有）
    "SocialMemBench_train": 0.2,   # 使用 SocialMemBench CC BY 4.0 数据
    "synthetic_multiparty": 0.3,   # 我们合成的数据
}
```

### 5.2 Curriculum Schedule

```
Epoch 1-3:  30% GroupMemBench + 30% SocialMemBench + 40% synthetic（偏 attribution）
Epoch 4-6:  20% GroupMemBench + 20% EverMemBench + 20% SocialMemBench + 40% synthetic（均衡）
Epoch 7+:   10% 各 benchmark + 70% synthetic（偏 hard challenges）
```

**hard challenge 比例**随 epoch 增加（类似 DPO hard negative mining）。

---

## 6. 实现路线图

| 阶段 | 任务 | 估算时间 | 依赖 |
|------|------|---------|------|
| 1 | Speaker profile 生成脚本 | 2 天 | LLM API |
| 2 | 对话合成 + 质量过滤 | 3 天 | LLM API（~$50 GPT-4o）|
| 3 | Memory 操作标注 | 3 天 | LLM API（~$100 GPT-4o）|
| 4 | QA 对生成 + 验证 | 2 天 | - |
| 5 | 格式化 + Dataset 打包 | 1 天 | - |
| **总计** | | **约 11 天** | API 费用 ~$200 |

---

## 7. 已知风险与缓解

| 风险 | 概率 | 缓解方案 |
|------|------|----------|
| LLM 标注 speaker attribution 不准确 | 中 | 加入 self-consistency 检查（同一样本标注两遍）|
| 合成对话不自然 | 中 | 参考 SocialMemBench 的"review by human annotators"流程 |
| memory 操作遗漏 | 中 | 使用 chain-of-thought prompting 让 LLM 先 step-by-step 分析再标注 |
| QA 问题与 memory 脱节 | 低 | answer_in_memory 自动过滤 |
| 数量不足（<150）| 低 | 可以快速扩展（增加 scenario 模板）|
