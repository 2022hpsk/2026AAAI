# SocialMemBench 结果口径审查：HippoRAG/A-MEM 的高分是真高还是口径问题？

> 起因：我们跑出 HippoRAG 59.0 / A-MEM 48.1（judge acc），疑似超过原论文里所有方法。
> 本文逐项核对原论文（arXiv 2605.17789）评分口径 + 原始评测代码（`SocialMemBench-code/`），
> 用两个受控实验把"真高"和"口径虚高"拆开。结论：**大部分是口径/预算造成的虚高，不能说我们超过了论文方法。**
> 生成 2026-06-10。

## 0. 一句话结论
- ✅ **数据是全量**（43 网络 / 1031 题，与 `qa.jsonl` 完全一致，非子集）。
- ✅ **三个论文检索预算都是 top-10 单条**（GroupMem BM25 top-10 消息；SocialMem naive_rag/mem0/subject_rag top-10 turn/记忆；EverMem 各 adapter top-10）→ **统一到 top-10 才公平**。
- ❌ **我们的 0.59/0.48 ≠ 论文 metric**：我们用**二值 judge（对/错）→ acc%**，论文用 **0–1 浮点 rubric（部分给分，错归属≤0.3）→ MeanQ/MeanN**。
- ❌ **HippoRAG 的"反超 BM25"全是检索预算假象**：HippoRAG@10passage = 每题喂 80 条原文（≈半篇对话）。**压到公平预算(1 passage≈8 条)后 HippoRAG 暴跌 59.0→22.9，反而低于 BM25@10(28.6)**；反向把 BM25 提到 80 条也跳到 57.3≈59。图谱/PPR 在小预算下不如 BM25 散点检索。
- ✅ **公平预算 top-10 真实排序：A-MEM(48.1) > BM25(28.6) > HippoRAG(22.9) > Mem0(13.7)**。**A-MEM 同预算大幅超 BM25 = 结构化记忆有效的真证据**；Mem0 全口径垫底（核心 motivation）。
- ⚠️ **不能声称"超过论文方法"**：论文没测 HippoRAG/A-MEM；judge 不同（DeepSeek vs gemini/gpt-4o-mini）；metric 不同。

---

## 1. 原论文到底怎么算分（读 `eval/core/evaluator.py` + `eval/config/prompts.yaml`）

**评分（每题 0.0–1.0）**：
- **多选**：二值 1.0/0.0（选对字母）。
- **开放题**：**LLM judge 给 0–1 浮点**（部分给分），judge 默认 `gemini-2.5-flash`（论文正文 GPT-4o-mini）。rubric 关键：
  - 错归属（attribution）**一律 ≤0.3**，不管其它内容多对；
  - Q3 多人聚合 = 正确召回成员的**比例**（3/5=0.6）；
  - Q5 ToM = 两部分各 0.5；Q8 时间漂移 = 旧值/新值/触发各 0.33；
  - "NOT ENOUGH INFORMATION"/"无记忆" = 0.0。
- **MeanQ** = 所有题浮点分的平均（按题加权）；**MeanN** = 43 个网络各自均分再平均（按网络加权）+ bootstrap 95% CI。
- 论文测的 condition：`llm_mini`(mini-oracle,喂全文) / `naive_rag` / `subject_rag` / `smg`(他们自家 Social Memory Graph) / `graphiti` / `langmem` / `mem0_local` / `cognee`，外加 `llm_gemini`(Gemini 全文 oracle,上界)。**没有 HippoRAG、没有 A-MEM。**

**我们的口径**：DeepSeek 做二值 judge（correct/incorrect/unclear）→ acc = correct 占比。**这是两套不同的数轴，绝对值不可直接比。**

---

## 2. 受控实验 A：换论文浮点 rubric 重评（隔离 metric/judge 轴）
`rejudge_paper_rubric.py`：用论文原版 judge prompt（system+user 原文，含错归属≤0.3 等）对**我们已有的答案**重新打 0–1 分（judge 仍 DeepSeek，故仍非论文 gemini，但**部分给分口径对齐**）。

| 基线 | 我们二值 acc | **论文式 MeanQ** | MeanN | ≥0.7占比 |
|---|---|---|---|---|
| BM25(@10) | 28.6 | **0.221** | 0.234 | 22.0% |
| Mem0(@10) | 13.7 | **0.093** | 0.091 | 9.3% |
| A-MEM(@10) | 48.1 | **0.345** | 0.339 | 35.4% |
| HippoRAG(@80,超预算) | 59.0 | **0.452** | 0.440 | 46.8% |
| HippoRAG(@8,公平) | 22.9 | **0.184** | 0.171 | 18.7% |

（HippoRAG 两行：@80=10 passage 超预算；@8=1 passage 公平预算。下 §3 详解。）

**论文参照**（gemini/gpt judge）：Mem0 0.143、Uncompressed 0.345、最强非oracle LLM-MINI 0.369、Gemini 全文 oracle 上界 0.721。
- 换 rubric 后 **HippoRAG 0.59→0.452**、A-MEM 0.48→0.345：缩水一大截，落到论文 oracle/最强方法附近。
- 我们二值 judge 的 acc（59/48）**普遍高于** 同答案在论文 rubric 下的 ≥0.7 占比（47/35）→ **DeepSeek 二值 judge 偏宽松**，是绝对值虚高的来源之一。
- Mem0 我们 0.093 略低于论文 0.143（我们是 `--parallel-extract` 无在线合并变体 + DeepSeek judge）。

> 仍不等于论文数字：judge 模型不同（DeepSeek≠gemini/gpt-4o-mini）。但已把"二值 vs 部分给分"这一轴对齐。

---

## 3. 受控实验 B：把 BM25 预算提到 80 条（隔离检索预算轴）★ 最决定性
**嫌疑**：HippoRAG 检索单位是 passage(=8 条消息)，top-k=10 → 每题喂 **最多 80 条原文**；而 BM25/Mem0/A-MEM 都是 top-k=10 个**单条**单位。
- SocialMem 每网络消息数：中位 178 / 均值 171 / max 302。**80 条 ≈ 平均覆盖整网络 44%**；21% 的网络(≤80条) HippoRAG 直接拿到近乎全文。
- 即 HippoRAG 更接近论文的 `llm_mini`/Uncompressed "喂原文" condition，而非"压缩记忆"。

**实验**：BM25 把 `--top-k` 从 10 提到 80（喂同量原文），同一二值 judge：

| | 检索预算 | 二值 acc |
|---|---|---|
| BM25 @top-k=10（10 条原文） | 10 条 | 28.6 |
| **BM25 @top-k=80（80 条原文）** | **80 条** | **57.3** |
| HippoRAG @top-k=10 passage（80 条原文） | 80 条 | 59.0 |

→ **BM25 在同样 80 条预算下从 28.6 暴涨到 57.3，与 HippoRAG 59.0 基本打平**；按类别 BM25@80 甚至在 Q4(77.5)、Q7(64.6)、Q9(90) 反超 HippoRAG@80。
→ **反向验证**：把 HippoRAG 压到公平预算(1 passage≈8 条)，**HippoRAG 暴跌 59.0→22.9 / MeanQ 0.452→0.184，反而低于 BM25@10(28.6)**——图谱/PPR 在小预算下不如 BM25 的"10 条散点最相关消息"。
→ **结论：HippoRAG 的高分 100% 是检索预算效应，知识图谱本身没加分（甚至小预算下减分）。**

### ★ 公平预算 top-10 终表（这才是该报的）
| 基线 | 检索预算 | acc | MeanQ | MeanN |
|---|---|---|---|---|
| **A-MEM** | ~10 note | **48.1%** | **0.345** | **0.339** |
| BM25 | 10 turn | 28.6% | 0.221 | 0.234 |
| HippoRAG | 1 passage≈8 条 | 22.9% | 0.184 | 0.171 |
| Mem0 | 10 记忆 | 13.7% | 0.093 | 0.091 |

→ **真实排序 A-MEM > BM25 > HippoRAG > Mem0**。**A-MEM top-10 note（≈10 条内容+LLM 富化）拿到 48 vs BM25@10 的 29 → 同预算下真实的结构化记忆增益**（语义 note + 关键词/上下文），不是预算堆的。

---

## 4. 对结论与论文的修正
| 之前的说法 | 审查后修正 |
|---|---|
| "SocialMem 上图记忆(HippoRAG 59)反超 BM25(29)" | **纯预算假象**。BM25@80=57.3≈HippoRAG@80 59；HippoRAG 压到公平预算 22.9<BM25@10 28.6。图谱没加分。 |
| "HippoRAG/A-MEM 超过论文所有方法" | **不能说**。论文没测这俩；judge/metric/预算都不同。 |
| "Mem0 三场全垫底" | ✅ **稳健**。acc 0.137 / MeanQ 0.093，所有口径最差。 |
| 真正能立的 | **A-MEM 公平预算下 48 vs BM25 29 = 结构化记忆有效的真证据**。 |

**对外/写论文的正确口径**：
1. 跨 baseline 比较**必须统一检索预算 = top-10 单条**（三个论文都用这个），否则就是变相喂全文。
2. 报 SocialMem 应**采用论文 MeanQ/MeanN（0–1 部分给分 rubric）**，而非二值 acc；理想用论文同款 judge（gemini/gpt-4o-mini）。
3. **A-MEM 的同预算优势 = "结构化记忆有效"的真证据**（支撑 SpeakerMem-R1）；HippoRAG 的高分**不能**用。
4. **Mem0 的失败稳健、可作核心 motivation**（见 `Mem0失效分析.md`）。

## 5. 复现命令
```bash
# 预算对照(实验B)
PYTHONPATH=. ./venv/bin/python run_baseline.py --baseline bm25 --benchmark socialmem \
    --domain all --top-k 80 --workers 16 --results-dir results_budget80
PYTHONPATH=. ./venv/bin/python compute_metrics.py --benchmark socialmem --baseline bm25 --results-dir results_budget80
# 论文 rubric 重评(实验A)
for b in bm25 mem0 amem hipporag; do
  PYTHONPATH=. ./venv/bin/python rejudge_paper_rubric.py --baseline $b; done
```
