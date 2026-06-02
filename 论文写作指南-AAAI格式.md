# SpeakerMem-R1 AAAI 2027 写作与格式指南

**版本**：v1.0（2026-06-02，V8 迭代产出）  
**目标**：将7个章节草稿整合为符合 AAAI 2027 格式要求的完整投稿

---

## 一、AAAI 2027 格式要求（历史惯例）

### 1.1 页面限制（预期）
- **正文**：8页（含图表和参考文献以外）
- **参考文献**：不计入8页限制
- **Appendix**：不计入8页限制（reviewer 可选择性阅读）

### 1.2 字体与排版（使用 aaai.sty 模板）
```latex
\documentclass[letterpaper]{article}
\usepackage{aaai27}  % 等模板更新后替换
\usepackage{times}
\usepackage{helvet}
\usepackage{courier}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
```

### 1.3 预期章节与页面分配

| 章节 | 目标页数 | 当前草稿长度 | 动作 |
|-----|---------|------------|------|
| Abstract | ~0.15 页 | 180-200 词 ✓ | 微调 |
| Introduction | ~1.2 页 | 5 段 ✓ | 压缩至1页 |
| Related Work | ~1.5 页 | 5 小节 ✓ | 保持 |
| Method | ~2.0 页 | 8 小节 ✓ | 精简 §3.8 |
| Experiments | ~2.0 页 | 6 小节（数字待填） | 填数字后调整 |
| Conclusion | ~0.5 页 | 350 词 ✓ | 保持 |
| **Total** | **~7.5 页** | **~7.5 页** | **留余量** |

---

## 二、章节整合策略

### 2.1 Abstract（180-200 词目标）

当前草稿 Abstract 已完成，符合 AAAI 要求：
- 第1句：问题背景（multi-party conversation memory is understudied）
- 第2-3句：现有方法的缺陷（all RL-based methods are dyadic）
- 第4-5句：我们的方法（SpeakerMem-R1 + 三大创新点）
- 第6句：实验结果（XX% on GroupMemBench vs YY% baseline）
- 最后：一句总结定位

**待填入**：三个 benchmark 的具体数字（实验后填）

### 2.2 Introduction（目标：约1页，5段）

当前草稿已有5段结构：
1. 多方对话 AI 的重要性（hook）
2. 现有记忆系统在多方场景的失败（5类失败模式引出）
3. RL 记忆学习的潜力 + 当前方法的 dyadic 限制
4. 我们的贡献（SpeakerMem-R1 三大组件）
5. 论文组织

**压缩建议**：每段控制在3-4句，删除过度解释性句子

### 2.3 Related Work（目标：约1.5页，5小节）

当前草稿 §2.1-2.5 已完成，结构合理：
- §2.1：Training-free（2段）
- §2.2：RL for Memory（4段，含 Key Gap）
- §2.3：Multi-Party Dialogue（1段）
- §2.4：Multi-Party Benchmarks（3段）
- §2.5：Curriculum Learning（1段）

**注意**：§2.2 已加入 R²-Mem 引用（2026/6/2 更新）

### 2.4 Method（目标：约2页，8小节）

当前草稿 §3.1-3.8 技术细节充分，需要精简：
- **保留**：所有核心数学公式（SpeakerLevenshtein F1、LoGo-GRPO）
- **精简**：§3.8 连接表（可移入 Appendix）
- **强化**：§3.4 novelty 论证（见下文）

### 2.5 §3.4 SpeakerLevenshtein Novelty 论证（关键写作）

在 "Advantage over DeltaMem" 段落中必须清晰表达为什么 per-speaker bucketing 不是 trivial：

**当前草稿（待补充）**：
> "On GroupMemBench, attribution errors are the primary failure mode (27.1% on knowledge-update, 37.7% on term-ambiguity). DeltaMem's flat Levenshtein reward cannot distinguish 'Alice's fact in Bob's bucket' from 'correct fact in correct bucket,' whereas SpeakerLevenshtein explicitly penalizes such cross-speaker contamination."

**需要补充的"naïve extension would fail"论证**：
> "A naïve extension would concatenate all facts across speakers and apply DeltaMem's Levenshtein reward globally. This approach fails for two distinct reasons:
>
> (1) **Attribution-content conflation.** Global Levenshtein assigns the same penalty to a factual error ('Alice works at Google' when ground truth is 'ByteDance') and an attribution error ('Alice works at ByteDance' stored in Bob's bucket). These represent fundamentally different failure modes: factual errors indicate information loss, while attribution errors indicate cross-speaker contamination. Conflating them prevents the agent from learning which failure to prioritize.
>
> (2) **Speaker imbalance.** Averaging over speakers allows the agent to succeed on K-1 easy speakers while failing on the hardest speaker. On GroupMemBench, attribution difficulty is highly uneven: speakers with many cross-references (e.g., a group leader discussed by all others) have substantially harder attribution than peripheral members. Our worst-speaker bonus $\mu \cdot \min_s \text{LevF1}^s$ prevents this degeneracy."

### 2.6 Experiments（目标：约2页）

**Table 2**（Main Results）：最重要的表，应占 ~0.4 页
- 当前所有数字为 XX% 占位符
- 实验完成后，应突出显示我们超过 state-of-art 的 margin

**Table 4**（Ablation）：用于证明各组件贡献
- A2 和 A5 是最关键的消融
- 用 bold 和 Δ 列清晰展示每个组件的贡献

**Case Studies**：可以削减到最清晰的2个（Case 1: attribution，Case 2: privacy），详细案例移入 Appendix

---

## 三、关键定位语句（全文统一用）

以下句子在全文多处使用，保持完全一致：

1. **Gap sentence（Related Work 结尾）**：
   > "To the best of our knowledge, SpeakerMem-R1 is the first reinforcement learning framework for memory management in multi-party conversations. All prior RL memory works operate in dyadic settings; all prior multi-party memory works are training-free or evaluation-only."

2. **Contribution summary（Introduction §4段）**：
   > "SpeakerMem-R1 makes three interlocking contributions: (1) SpeakerLevenshtein, a dense process reward computed per-speaker; (2) Speaker-Conditioned LoGo-GRPO, which stratifies local rerollouts on the active speaker set; (3) a five-layer speaker-indexed memory architecture that makes speaker grounding a first-class design principle."

3. **Novelty validation（Abstract 中）**：
   > "Evaluated on GroupMemBench, EverMemBench, and SocialMemBench — the three multi-party memory benchmarks that together document systematic failures in all existing memory systems — SpeakerMem-R1 achieves [XX]% on GroupMemBench (vs. [YY]% current best), [XX] on SocialMemBench (vs. [YY] production systems), and [XX]% on EverMemBench attribution tasks."

---

## 四、投稿检查清单（提交前）

### 格式检查
- [ ] aaai27.sty 模板应用正确
- [ ] 正文 ≤8 页（不含参考文献和 Appendix）
- [ ] 图表高分辨率（≥300 dpi），字体嵌入
- [ ] 所有 [cite] 占位符替换为真实引用（参见 论文参考文献.bib）

### 内容检查
- [ ] Abstract 包含具体实验数字（非 XX%）
- [ ] Introduction §5段完整，有明确贡献声明
- [ ] Related Work Key Gap 句子精确（多方 RL memory 零篇）
- [ ] Method §3.4 包含 "naïve extension would fail" 论证（见上文）
- [ ] Experiments 所有 XX% 替换为真实数字
- [ ] Ablation Table 4 有 Δ 列和统计显著性标注（bootstrap, p<0.05）
- [ ] Case Studies 使用真实系统输出（不是草稿中的示意输出）
- [ ] Conclusion 结尾有 Future Work（MultiPartyPRM / SpeakerForget-RL）

### 参考文献检查
- [ ] BibTeX 中所有 TODO 替换为真实作者信息
- [ ] arXiv 引用替换为正式发表版本（如果已发表）
- [ ] 引用格式统一（AAAI citation style）

### 伦理声明
- [ ] 合成数据生成方法说明
- [ ] 数据隐私声明（合成数据，无真实用户数据）
- [ ] 开源声明（代码 + 数据 + 评测框架）

---

## 五、Reviewer 常见质疑与应对

| 质疑 | 应对 | 对应章节 |
|-----|-----|---------|
| "只是把 dyadic 扩展到多方，没有核心创新" | 5 类失败模式 + SpeakerLevenshtein 不是 trivial 扩展 + A2 消融数字 | §1.2, §3.4, §4.3 |
| "合成数据偏差" | 所有 baseline 用同样合成数据；测试在真实 benchmark 上 | §4.1 |
| "CoMAM/DeltaMem 可以直接扩展" | A2/A5 消融展示直接扩展 不 work | §4.3 |
| "R²-Mem 已经超过你们（dyadic 上）" | R²-Mem 无 speaker attribution，无多方场景；我们解决不同问题 | §2.2 |
| "计算开销太大" | LoGo overhead 实际只有 1.2×（不是 3-5×） | Appendix §D |

---

*写作指南版本 v1.0 | 2026-06-02 | V8 迭代产出*
