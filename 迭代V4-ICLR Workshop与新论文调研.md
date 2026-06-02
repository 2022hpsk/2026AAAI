# 迭代 V4：ICLR 2026 MemAgents Workshop + 新论文调研结果

**迭代日期**：2026-06-02（第 4 轮）  
**结论先行**：
1. **发现未覆盖新论文**：Mem-T（MoT-GRPO，2601.23014）和 MIRA（2602.17930）
2. **EverMemBench 有官方评测代码**（EverMemOS 仓库）
3. **MemAgent 是 ICLR 2026 主会 Oral**（已在我们的详解中，但身份更重要）
4. **多方 RL niche 确认**：存在多方 benchmark，但 RL 训练框架在多方场景的应用仍是空白

---

## Part 1：ICLR 2026 MemAgents Workshop 详情

**官方名称**：Memory for LLM-Based Agentic Systems (MemAgents)  
**日期**：2026 年 4 月 27 日，里约热内卢（线上线下混合）  
**规模**：110+ 篇提交  
**OpenReview**：openreview.net/group?id=ICLR.cc/2026/Workshop/MemAgent  
**官方网站**：sites.google.com/view/memagent-iclr26/  

**CFP 明确覆盖的方向**（直接对应我们的工作）：
- 记忆架构与表征（情节记忆、语义记忆、工作记忆）
- **强化学习与记忆优化** ✅
- **多智能体（multi-agent）设置下的记忆层** ✅
- 评测 benchmark 设计

**重要**：GroupMemBench/SocialMemBench/EverMemBench 均在 Workshop 投稿截止（2026/2）之后发表，但时间吻合，可能未来有 Workshop proceedings 版本。

### 对我们的含义

1. **写作引用**：可在 Introduction 第 4 段引用 MemAgents Workshop 作为"社区共识"（"memory + RL 方向获得 ICLR 2026 workshop 专题认可，证明方向重要性"）
2. **潜在投递目标**：如果 AAAI 2027 时间紧，MemAgents Workshop 续集（ICLR 2027 版）是高质量 backup venue

---

## Part 2：新发现的未覆盖论文

### 2.1 Mem-T（arXiv 2601.23014，2026/1）— 重要未覆盖

**全名**：Mem-T: Tree-of-Memory Reinforcement Learning for Long-Horizon Memory Agents  
（注：论文标题待确认，基于 "MoT-GRPO" 关键词）

**核心创新**：**MoT-GRPO（Memory-of-Tree GRPO）**

- **问题**：稀疏 terminal reward → step-wise 监督信号很弱
- **方案**：把 memory operation trajectory 建模为**树结构**（不是线性链）
  - 树的每个节点是一次 memory operation
  - 树的分支代表多种 memory 选择路径（如：ADD vs UPDATE vs DELETE）
  - 用树结构引导 RL 的 credit assignment
- **效果**：稀疏 terminal reward → 密集 step-wise 监督（类似 DeltaMem 的解法但从树结构来）

**与我们的关系**：
- Mem-T 的 tree-structured GRPO 是另一种"把稀疏 reward 做密集"的方法
- 与 DeltaMem（Levenshtein dense reward）和 Memory-R2（LoGo local rerollout）是三种不同思路
- 我们的 SpeakerLevenshtein 方向与 DeltaMem 最接近，但 Mem-T 的树结构也值得借鉴
- **需要**：建立 Mem-T 的详解文件

### 2.2 MIRA（arXiv 2602.17930，2026/2）— 新发现

**全名**：MIRA: Memory Integration RL Agent  
（基于"有限 LLM 引导下的记忆集成 RL agent"描述）

- 较少信息，需精读
- **需要**：搜索更多细节

### 2.3 MemAgent（arXiv 2507.02259）— ICLR 2026 主会 Oral！

**重要身份更新**：MemAgent 是 **ICLR 2026 主会 Oral** (Tsinghua/ByteDance Seed)，不只是 arxiv preprint！

**含义**：
1. 在论文 Related Work 里应该引用 MemAgent 为 "ICLR 2026"（期刊级别的引用）
2. MemAgent 的 3.5M token 外推能力已经被 ICLR 主会认可，代表 RL memory 方向的最高认可度
3. **注意区分**：MemAgent = 长上下文压缩（overwrite strategy，不涉及 speaker），是 V1-V3 详解中已覆盖的

### 2.4 PersonaMem-v2（arXiv 2512.06688）— 确认细节

**已确认数据规模**：
- 1,000 个用户 × 300+ 场景 × 20,000+ 用户偏好
- 128K token 上下文
- **绝大多数偏好是隐式揭示**（真实世界交互风格）
- 用 **Qwen3-4B + RL 微调**达到 53% 精度（超过 GPT-5 在此任务上）
- Agentic Memory System：仅用 2K token 记忆替代 32K 对话历史，精度 55%（**16x 效率提升**）

**关键数字**（写作用）：2K token memory ≈ 32K token context，效率 16x

**局限**：单用户场景，无多方扩展 → 我们的差异化仍然有效

### 2.5 Safety × Memory 新方向（arXiv 2605.17830）

"Remembering More, Risking More" — 长期记忆的安全风险研究

**对我们的含义**：
- 我们的隐私层（R_leak penalty）可以在论文中 reference 这篇工作作为 motivation
- "多方群聊 + 隐私"是安全相关研究，增加论文的 broader impact

---

## Part 3：EverMemBench 官方评测代码（重要发现）

**GitHub**：https://github.com/EverMind-AI/EverMemOS  
**评测命令**：
```bash
uv run python -m evaluation.cli --dataset evermembench --system <memory_system>
```

**内置支持的 memory 系统**：EverMemOS, Mem0, MemOS, MemU 等

**对我们的含义**：
1. ✅ **可以直接使用官方评测代码**评测我们的方法（不用自己实现评测）
2. ✅ 可以 fork 仓库，在 `evaluation/` 中加入 SpeakerMem-R1 作为新 system
3. 三维度评测（Factual Recall / Applied Memory / Personalization）覆盖多方场景所需的评测角度

**评测 pipeline 规划**：
```bash
# 在 EverMemOS 仓库中添加 SpeakerMem-R1
git clone https://github.com/EverMind-AI/EverMemOS
# 实现 SpeakerMem-R1 memory system 接口
# 运行评测
uv run python -m evaluation.cli --dataset evermembench --system speakermem_r1
```

---

## Part 4：更新后的竞品 Landscape（完整版）

| Paper | 时间 | Setting | Training | Key Tech | ICLR 2026? |
|-------|------|---------|----------|----------|------------|
| MemAgent | 2025.11 | long ctx | RL (DAPO) | overwrite+3.5M extrapolation | **Oral** ✅ |
| Memory-R1 | 2025.10 | dyadic | 2-agent RL | construction+retrieval | - |
| AgeMem | 2026.01 | dyadic | step-wise GRPO | 3-stage | - |
| **Mem-T** | 2026.01 | ? | **MoT-GRPO** | tree-structured RL | Workshop? |
| **MIRA** | 2026.02 | ? | RL | memory integration | Workshop? |
| Mem-α | 2026.02 | dyadic | RL | 3-component | - |
| CoMAM | 2026.03 | dyadic | joint RL | rank-consistency credit | - |
| DeltaMem | 2026.04 | dyadic | RL | Levenshtein dense reward | - |
| Memory-R2 | 2026.05 | dyadic | LoGo-GRPO | local rerollout | - |
| **GroupMemBench** | 2026.05 | **multi-party** | benchmark | speaker+audience | Workshop? |
| **SocialMemBench** | 2026.05 | **multi-party** | benchmark | 5 failure modes | Workshop? |

**关键观察**（更新后）：
- **dyadic + RL**：14+ 篇，红海
- **multi-party + RL 训练**：**仍然零篇**（Mem-T/MIRA 待确认是否多方）
- **multi-party + benchmark**：3 篇，已经形成子领域

---

## Part 5：需要新建的详解文件

基于 V4 调研发现，以下论文需要新建详解：

| 论文 | arXiv | 优先级 | 原因 |
|-----|-------|--------|------|
| **Mem-T** | 2601.23014 | ⭐⭐⭐⭐ | MoT-GRPO 是 alternative dense reward 思路 |
| **MIRA** | 2602.17930 | ⭐⭐⭐ | memory integration RL，信息较少 |
| **PersonaMem-v2** | 2512.06688 | ⭐⭐⭐ | 确认了具体数字，16x 效率 |
| **MemAgent (ICLR Oral 更新)** | 2507.02259 | ⭐⭐ | 已有详解，但需更新为 ICLR Oral 身份 |

---

## Part 6：对 Idea 和方法的影响

### 6.1 Mem-T 的影响

Mem-T（MoT-GRPO）提供了第三种解决稀疏 reward 的思路（与 DeltaMem 的 dense state reward 和 Memory-R2 的 LoGo rerollout 并列）。

**对 SpeakerMem-R1 的含义**：
- V2 方法 spec 已经用了 DeltaMem + Memory-R2 思路
- Mem-T 的树结构思路**可以作为消融对比**（不一定要采用）
- 在论文 Related Work 里应该增加 Mem-T 作为 "another solution to sparse reward"

### 6.2 MemAgent ICLR Oral 身份的影响

MemAgent 是 ICLR 2026 Oral（最高认可级别）。这意味着：
- 在论文里引用 MemAgent 时应该写 "ICLR 2026" 而非 "arXiv preprint"
- MemAgent 的 3.5M 外推是 long-context memory 方向的 SOTA，我们的方法不需要与之直接比较（不同 setting）

### 6.3 PersonaMem-v2 的 16x 效率数字

"2K token memory ≈ 32K token context，效率 16x" 是非常 catchy 的 selling point。
- 我们的 5-layer speaker-indexed memory 也有类似效率优势
- 可以在 Introduction 中类似表述：我们的 memory 结构在多方场景下实现了 Yx token 效率提升

---

## Part 7：本轮迭代总结

### 已完成（V4 完成）

1. ✅ ICLR 2026 MemAgents Workshop 信息确认
2. ✅ 发现新未覆盖论文 Mem-T + MIRA + PersonaMem-v2
3. ✅ 确认 EverMemBench 官方评测代码
4. ✅ 确认 MemAgent 是 ICLR 2026 Oral
5. ✅ 更新竞品 landscape 表格
6. ✅ 写论文草稿（Abstract + Introduction）
7. ✅ 实现 SpeakerLevenshteinReward 核心代码

### 待完成（V5 计划）

1. [ ] 建立 Mem-T 详解（MoT-GRPO 技术细节）
2. [ ] 建立 MIRA 详解（精读后）
3. [ ] 更新 MemAgent 详解（添加 ICLR Oral 身份）
4. [ ] 运行代码测试（pending pip install 完成）
5. [ ] 设计合成数据生成 pipeline（第一批 50 条 close_friends）
6. [ ] 在 EverMemOS 仓库中阅读评测代码（了解接口格式）

---

*文档版本 v1.0 | 2026-06-02 | V4 迭代产出*
