# 迭代 V3：Benchmark 数据规模调研 + 训练数据方案

**迭代日期**：2026-06-02（第 3 轮）  
**结论先行**：**三大多方 benchmark（GroupMemBench/EverMemBench/SocialMemBench）均无训练集，均为纯评测设计**——这是我们 RL 训练方案的核心障碍。必须改变训练数据策略。

---

## Part 1：三大 Benchmark 数据规模（最终确认）

### 1.1 GroupMemBench（arXiv: 2605.14498，2026/5）

**数据规模**：
- 6 类问题（多跳推理/知识更新/术语歧义/用户隐式推理/时序推理/弃答）
- 最强系统准确率仅 **46.0%**（知识更新 27.1%，术语歧义 37.7%）
- BM25 baseline 匹配或超越大多数 agent memory 系统

**训练集情况**：❌ **纯评测集，无训练 split**

**构建方式**：图驱动合成流水线（graph-grounded synthesis），对抗性问题生成，每个问题绑定特定提问者

### 1.2 EverMemBench（arXiv: 2602.01313，2026/2）

**数据规模**：
| 统计项 | 数值 |
|-------|------|
| 员工人数（personas） | 170 |
| 对话轮次 | 51,023 turns |
| 总 token 数 | ~4.2M tokens（~1M/项目） |
| QA pairs | **2,400**（细粒度回忆/记忆感知/用户画像各 800） |
| 项目数 | 5 个职场场景 |

**训练集情况**：❌ **纯评测集，无训练 split**

**关键发现**：即使 oracle 模型（完整上下文），多跳归因准确率仅约 **26%**

GitHub：https://github.com/EverMind-AI/EverMemBench

### 1.3 SocialMemBench（arXiv: 2605.17789，2026/5）

**数据规模**：
| 统计项 | 数值 |
|-------|------|
| Personas | 430 |
| Sessions | 348 |
| 对话轮次 | 7,355 turns |
| QA pairs | **1,031**（9 类社交记忆问题，全人工验证） |
| 群组规模 | 4–30 人 |

**5 类失败模式（核心发现）**：
1. **Single-stream conflation**：单流混用——把 "Sarah 说 X 关于 Mike" 压成关于 Sarah 的群体事实
2. **Temporal-state overwrite**：时态覆写——新信息覆盖了用户偏好/状态的历史版本
3. **Entity merging at scale**：实体合并错误——不同 persona 合并为同一节点，大群组中尤重
4. **Missing cross-persona knowledge**：跨人物知识缺失——需要同时追踪多用户的归因槽
5. **Norm-individual conflation**：规范-个体混淆——群体规范 ≠ 个人特征

**训练集情况**：❌ **纯评测集，无训练 split**

**关键发现**：Gemini 2.5 Flash（全上下文）仅 0.721；开源记忆框架 Mem0/LangMem/Graphiti/Cognee 仅 0.12–0.18

---

## Part 2：关键发现——训练数据空白

### 2.1 问题确认

**三大 benchmark 均无训练集**——这意味着：

- 我们的 RL 训练**不能直接在这些 benchmark 上**做 RL warm-up
- 只能把这三个 benchmark 用作**纯评测集**，用来验证我们的方法
- **训练数据需要另外来源**

### 2.2 BM25 在 GroupMemBench 强的原因（分析）

从调研结果综合分析：

1. **合成数据词汇一致性**：GroupMemBench 用图驱动流水线合成，问题和对话片段有词汇直接对应，BM25 的 IDF 加权天然占优
2. **Agent 系统引入额外噪音**：Mem0/Graphiti 的实体合并/摘要操作在多方场景中容易出错（正是 SocialMemBench 失败模式 3 和 1）
3. **现有系统 dyadic 偏差**：所有 agent memory 系统针对单用户优化，多方场景下不适应
4. **关键洞察**：BM25 的 "强" 是相对的——绝对最高才 46%，BM25 强 = 大家都弱，不是 BM25 很强

**对 SpeakerMem-R1 设计含义**：
- Retrieval 本身不是瓶颈——BM25 已经是 retrieval 上限附近
- 真正瓶颈是 **memory writing/organization**（写入质量、归属准确性）
- → 我们的 RL 重点应该放在 **memory construction agent（写入策略）**，而非 retrieval

---

## Part 3：2026 年 4-6 月最新进展

### 3.1 多方 RL Memory 新论文

**调研结论：仍然为零**

| 论文 | arXiv | 与多方 RL Memory 相关性 |
|-----|-------|----------------------|
| Curriculum Study (2605.23067) | 2026/5 | 间接相关（RL 训练数据 curriculum），dyadic |
| CoMAM (2603.12631) | 2026/3 | 相关但 dyadic |
| MemFail (2605.26667) | 2026/5 | 诊断性，非 RL 训练 |

**结论**：GroupMemBench/SocialMemBench 于 2026/5 刚发布，尚无基于这些 benchmark 的 RL 训练工作。**多方 RL memory niche 仍然完全空白**。

### 3.2 MemFail 新发现（值得关注）

**MemFail** (2605.26667, 2026/5)：系统性诊断记忆系统三类操作（摘要/存储/检索）的失败模式，构建 5 个对抗数据集。

**对我们的含义**：
- 与 SocialMemBench 的失败模式分析相互印证
- 可以作为 SpeakerMem-R1 的 "challenge" setting 额外评测
- MemFail 的 5 个对抗数据集可能可以用于训练数据合成

---

## Part 4：训练数据方案（关键决策）

### 4.1 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|-----|------|------|--------|
| A: 联系作者获取原始数据 | 质量最高 | 时间不确定，可能被拒 | ⭐⭐⭐ |
| B: GPT-4 合成多方对话 | 完全可控，规模灵活 | 合成数据偏差，成本 | ⭐⭐⭐⭐ |
| C: Dyadic 数据 speaker 扩增 | 快速，有现成数据 | 不够接近真实多方场景 | ⭐⭐⭐ |
| D: 从 EverMemBench 对话日志抽取 | 真实数据 | 无 GT memory labels | ⭐⭐ |
| E: 混合 B+C | 平衡质量和效率 | 需要更多实现工作 | ⭐⭐⭐⭐⭐ |

**推荐方案 E（混合合成策略）**：

### 4.2 推荐训练数据合成方案（详细）

#### 来源 1：GPT-4 合成多方对话（~200 条）

```python
# 合成 prompt 模板

SYNTHESIS_PROMPT = """
生成一段多方群聊对话，满足以下要求：
- 说话人数：{K} 人（{speaker_list}）
- 对话轮次：{T} 轮
- 场景：{scene_type}（家庭/职场/兴趣社群/朋友圈）
- 包含以下信息类型：
  * 每个说话人的 2-3 个核心 fact（工作/爱好/状态）
  * 1-2 个时态变化（如"之前做X，现在做Y"）
  * 1-2 个跨说话人引用（如"Alice 提到 Bob 喜欢..."）
  * 1 个潜在信息隐私场景（某人不想让某人知道某事）

同时生成：
- Ground truth memory（按 speaker 分桶的 fact 集合）
- 3 个测试问题（含答案和必要记忆片段标注）
"""

# 场景类型
SCENE_TYPES = [
    "close_friends_chat",    # 对应 SocialMemBench
    "workplace_team",        # 对应 EverMemBench
    "interest_community",    # 对应 GroupMemBench
    "family_group",
    "mixed_social",
]
```

#### 来源 2：Dyadic 数据 Speaker 扩增（基于 LoCoMo，~100 条）

```python
# 把 LoCoMo 的双人对话扩增为三方对话
# 方法：引入第三个人，让他"转述"或"参与"部分信息

def augment_dyadic_to_triadic(dyadic_conv):
    """
    1. 选取 dyadic 对话的某段片段
    2. 用 GPT-4 插入第三方说话人的发言（基于已有信息）
    3. 修改 GT memory 为 3-speaker 版本
    """
    pass
```

#### 数据规模目标

根据 Curriculum Study 的经验（150 条是"specialization"拐点）：

| 来源 | 目标数量 | 说话人数 |
|-----|---------|---------|
| GPT-4 合成（close_friends） | 50 条 | 3-5 人 |
| GPT-4 合成（workplace_team） | 50 条 | 4-8 人 |
| GPT-4 合成（interest_community） | 50 条 | 3-6 人 |
| LoCoMo 扩增（triadic） | 50 条 | 3 人 |
| **总计** | **200 条** | 3-8 人 |

---

## Part 5：更新版实验设计

### 5.1 修订后的数据流

```
训练数据（200条合成）
    ↓
Stage 1 SFT（speaker-conditioned）
    ↓
Stage 2 Joint RL（200条合成 + 50条LoCoMo 强化）
    ↓
Stage 3 E2E（混合 curriculum，全合成数据）
    ↓
评测（GroupMemBench dev/test + EverMemBench + SocialMemBench）
```

### 5.2 修订后的消融实验（增加数据相关消融）

| 实验 | 消融内容 | 验证目的 |
|-----|---------|---------|
| A1-A7 | 见方法 spec §7.4 | 原消融设计 |
| **D1** | 合成数据 vs LoCoMo 扩增数据 | 验证数据质量的影响 |
| **D2** | 混合 curriculum vs 单一来源 | 验证 Curriculum Study 结论在多方场景是否成立 |
| **D3** | 100条 vs 200条训练 | 验证数据量的影响（是否有 150 条拐点）|

---

## Part 6：方案修订总结

### 6.1 本轮主要发现

1. ✅ **三大 benchmark 已确认**：GroupMemBench/EverMemBench/SocialMemBench 均为 2026 年新出
2. ❌ **关键障碍**：三大 benchmark 无训练集，必须合成训练数据
3. ✅ **niche 确认**：2026/6/2 仍然无多方 RL memory 方法论文
4. ✅ **BM25 强的原因理解**：agent memory 系统的多方场景系统性崩溃，不是 BM25 真的强
5. ✅ **5 类失败模式**（SocialMemBench）：与我们的设计高度对应
6. ✅ **EverMemBench 数据规模**：51,023 轮次，2,400 QA，GitHub 开放

### 6.2 对 SpeakerMem-R1 方法设计的含义

| 发现 | 对方法的含义 |
|-----|------------|
| 无训练集 | 必须合成训练数据（方案 E） |
| BM25 强 = 写入质量是瓶颈 | RL 重点放在 construction agent，而非 retrieval |
| SocialMemBench 5 类失败模式 | 与我们的 5 层记忆结构高度对应，可以用来 frame contribution |
| EverMemBench oracle 才 26% | 问题极难，即使方法不完美也有发表价值 |
| MemFail 存在 | 额外的对抗评测场景，可作为 bonus 实验 |

### 6.3 Writing Frame 更新

5 类失败模式是很好的写作 hook：

```
Introduction hook:
"Recent work has identified five fundamental failure modes 
in social memory (SocialMemBench): single-stream conflation, 
temporal-state overwrite, entity merging, cross-persona knowledge 
gaps, and norm-individual conflation. These failures share a 
common root cause: existing memory systems lack speaker grounding—
they cannot track WHO said WHAT to WHOM. 
SpeakerMem-R1 directly addresses this root cause..."
```

---

## 附：关键调研数字摘要（供写作备用）

| 指标 | 数值 | 来源 |
|-----|------|------|
| GroupMemBench 最强系统准确率 | 46.0% | GroupMemBench |
| GroupMemBench 知识更新类 | 27.1% | GroupMemBench |
| EverMemBench Oracle 多跳归因 | ~26% | EverMemBench |
| SocialMemBench Gemini 2.5 全上下文 | 0.721 | SocialMemBench |
| SocialMemBench 开源框架分数 | 0.12-0.18 | SocialMemBench |
| EverMemBench QA pairs | 2,400 | EverMemBench |
| SocialMemBench QA pairs | 1,031 | SocialMemBench |
| EverMemBench 对话轮次 | 51,023 | EverMemBench |

---

*文档版本 v1.0 | 2026-06-02 | V3 调研结果*
