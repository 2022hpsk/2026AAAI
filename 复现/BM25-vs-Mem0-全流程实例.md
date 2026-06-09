# BM25 与 Mem0 全流程实例 + 指标详解（用真实数据贯穿）

本文件用 **GroupMemBench / Finance 里的一条真实消息 + 一道真实题**，把 BM25 和 Mem0 两条
完整链路一步步走一遍，并讲清每个指标怎么算。所有数值都来自实跑结果。

---

## 0. 贯穿用的数据（真实）

**一条对话消息**（`data/final/Finance/...json` 里某频道的一条）：
```json
{ "msg_node": "Msg_4", "author": "User_5", "role": "Compliance Officer",
  "timestamp": "2025-07-09T00:10:23",
  "content": "Small milestone — we've officially kicked off the Incomplete Regulatory
              Coverage phase. Since we're at 0%, I'm treating this as our start point ..." }
```
一个领域有 ~3 万条这样的消息，分布在 6 个频道、12 个用户(User_1..User_12)。

**一道题**（`questions/Finance/multi_hop.jsonl` 第 1 条）：
```json
{ "id": "multi_hop_1",
  "question": "What is the deadline for Reporting to validate fit against the
               enterprise-wide ESG policy standard? (YYYY-MM-DD)",
  "answer": "2025-07-18",          // ← 标准答案(gold)
  "asking_user_id": "User_7" }     // ← 谁问的(per-asker)
```
答这道题需要：在 3 万条里找到"Reporting 验证 ESG 政策标准"相关的消息，读出其中的 deadline。

---

## 1. BM25 全流程（7 步，带真实结果）

```
第1步 读对话：3万条消息读成列表，按 频道→时间→msg_node 排序。
第2步 建索引：对每条消息的【正文】切词(小写、保留数字/日期/UserID)，喂给 BM25Okapi。
              —— 注意：只索引正文，元数据(author/role/timestamp…)不进索引。
第3步 检索：把"谁问的+问题"拼成 query = "User_7 What is the deadline for Reporting to
            validate fit against the enterprise-wide ESG policy standard?"，
            切词后 BM25 打分，取分数最高的 top-k=10 条消息(下标)。
第4步 拼段落：把这 10 条消息连同元数据格式化成 10 段。每段形如：
            [user=User_3 / speaker_role=Product Owner / channel=Sustainable Finance Strategy /
             phase_name=… / timestamp=2025-07-10T04:.. / msg_node=Msg_..]
            <正文>
            —— 元数据在这一步才拼回来给 LLM 看(检索时不算分)。
第5步 QA-agent(1次 DeepSeek 调用)：
       system = "你是严谨的QA助手，只用检索到的段落回答；先思考，最后一行 Final: <答案>"
       user   = "Asking user: User_7\n\nQuestion: …\n\nRetrieved passages: [1]… [2]… …\n\n
                 Answer using the retrieved passages."
       模型输出： …(推理)… → Final: 2025-07-18
       → 取 Final 行 = agent_answer = "2025-07-18"
第6步 judge(1次 DeepSeek 调用)：
       user = "Question: …\nGold Answer: 2025-07-18\nAgent Answer: 2025-07-18\n"
       模型输出： …(简评)… → Final: Correct   → verdict = correct
第7步 记指标：判 correct；并算 EM/F1(见 §4)。
```

**这道题 BM25 的真实结果**（来自 `results/groupmem/Finance/bm25__multi_hop.jsonl`）：
```json
{ "id":"multi_hop_1", "verdict":"correct", "em":true, "f1":1.0,
  "agent_answer":"2025-07-18", "gold":"2025-07-18", "t_retrieve":0.02, "t_agent":~2, "t_judge":~2.5 }
```
✅ BM25 把含 deadline 的原始消息检索回来，agent 直接读出 `2025-07-18`，judge 判对，EM=F1=1.0。

---

## 2. Mem0 全流程（入库 + 问答，带真实结果）

Mem0 和 BM25 的区别**只在"检索什么"**：BM25 检索原始消息；Mem0 先把对话用 LLM "抽取成事实记忆"
存起来，检索时返回的是**被概括过的记忆文本**。第 5~7 步(QA-agent / judge / 指标)两者完全一致。

```
【入库阶段】(每个域只做一次，可持久化复用)
 第A步 分批：消息按 batch(默认50)分组。
 第B步 抽取(每批1次 DeepSeek 调用)：用 mem0 的 ADDITIVE_EXTRACTION_PROMPT，
        把这批消息抽成一条条"自包含事实"。例如这批抽出：
          - "User_1 requested Ops to lock the remediation queue SLA to 48 hours for July 17, 2026"
          - "User_5 kicked off the Incomplete Regulatory Coverage phase at 0% progress"
          - …(一批~50条)
        ★ 推理模型(deepseek-v4-flash)输出 JSON，需 max_tokens≈10万 否则被截断丢事实。
 第C步 嵌入+落库：每条事实用本地 MiniLM 算 384维向量，存进 chroma(持久化到 .mem0_chroma)。
 第D步 (串行版)还会跟已有记忆做"增量合并/去重/覆盖"；并行版(--parallel-extract)跳过合并换提速。

【问答阶段】(与 BM25 第 3~7 步对应，区别只在"检索")
 检索：query 用本地 MiniLM 嵌入 → 在 chroma 里向量检索 top-k=10 条【记忆文本】(不是原始消息)。
 之后 QA-agent / judge / 指标 与 BM25 完全相同。
```

**这道题 Mem0 的真实结果**（来自 `results/Finance/mem0__multi_hop.jsonl`，入库 1000 条时）：
```json
{ "query":"What is the deadline for Reporting to validate fit ... ESG policy standard?",
  "agent_answer":"The answer is not supported by the retrieved passages.",
  "judge_answer":"Incorrect" }
```
❌ Mem0 答错。原因：检索回来的"记忆文本"里**没有这道题要的那个具体 deadline**——要么该事实
没被入库(覆盖只 3.3%)，要么抽取/合并时把这条具体日期丢了/概括掉了。

---

## 3. 同一道题，为什么 BM25 对、Mem0 错？

| | BM25 | Mem0 |
|---|---|---|
| 检索单位 | 原始消息(逐字保留 deadline) | LLM 概括后的记忆文本 |
| 这道题 | 检到含 `2025-07-18` 的原句 → 答对 | 记忆里没这条具体日期 → 答"不支持" → 错 |
| 本质 | 关键词命中、不丢细节 | 抽取/合并会丢精确事实 + 入库成本高 |

这正是 GroupMemBench 论文"**BM25 追平甚至超过 Mem0**"的微观写照，也是我们 SpeakerMem-R1
要打的点：现有记忆系统在"精确归属/精确事实"上结构性吃亏。

---

## 4. 指标详解（公式 + 这道题的计算）

记号：`pred` = agent 的最终答案；`gold` = 标准答案。文本先归一化：小写、去首尾空格、去末尾句点、压缩空白。

### 4.1 judge 准确率（主指标，benchmark 官方口径）
- 由 LLM judge 判 `Correct / Incorrect`（允许同义改写算对）；解析不出判定记 `unclear`。
- 某类准确率 = 该类判 correct 的题数 / 该类总题数。
- **微平均**(汇总时)：所有类的 correct 总数 / 总题数（比"各类准确率再平均"更准，避免小类被放大）。
- 本题：judge=Correct → 计入 correct。

### 4.2 EM（Exact Match，精确匹配）—— 像填空题，一字不差才给分
- `EM = 1` 当且仅当 归一化(pred) == 归一化(gold)（归一化=小写/去首尾空格/去末尾句点/压空白），否则 0。
- 本题：pred="2025-07-18"，gold="2025-07-18" → **EM=1**。

### 4.3 token-F1（词级 F1）—— 像改作文，按"重合的词"给部分分
设 **gold = "Bob works at Tencent"**（4 个词：bob/works/at/tencent），看不同 pred：

| pred | EM | 共同词 | 精确率=共同/pred词数 | 召回率=共同/gold词数 | F1=2PR/(P+R) | 直觉 |
|---|---|---|---|---|---|---|
| `Bob works at Tencent` | 1 | 4 | 4/4=1.0 | 4/4=1.0 | **1.0** | 全对 |
| `Tencent` | 0 | 1 | 1/1=1.0 | 1/4=0.25 | **0.4** | 只说中公司名(部分对) |
| `Bob works at Google` | 0 | 3 | 3/4=0.75 | 3/4=0.75 | **0.75** | 词大量重合但关键词错→F1虚高(局限) |
| `I guess Bob now works at the Tencent company` | 0 | ~4 | 低(废话多) | 高 | **≈0.6** | 啰嗦被精确率惩罚 |

公式：精确率 P=|pred∩gold|/|pred|（罚废话），召回率 R=|pred∩gold|/|gold|（奖说全），`F1=2·P·R/(P+R)`（任一为0则0）。
- 本题：pred=gold={"2025-07-18"} → P=R=1 → **F1=1.0**。
- 一句话：**EM 严格(全对才1)，F1 宽松(按词重合给部分分)**；都只是辅助，**judge 准确率才是主指标**。

### 4.4 不明率（unclear rate）
- = judge 输出解析不出 Correct/Incorrect 的题数 / 总题数。
- 我们用 `eval_patches` 把 judge 的 token 预算抬高 + temperature=0，把不明率压到 <1%
  （否则 DeepSeek 的长 reasoning 会把 `Final:` 行截断 → 误判 unclear，人为压低准确率）。

### 4.5 仅检索 recall@k（不调 LLM 的代理指标）
- 不做 QA，只看"标准答案文本是否作为子串出现在 top-k 段落里"。
- 用于零成本验证检索链路；但对"需要 LLM 算/答"的题(日期推算等)会低估，**不是正式指标**。

### 4.6 计时（各阶段）
- 建索引时间(每单元) / 检索累计 / agent 累计 / judge 累计 / **QA 墙钟**(并发后的真实耗时)。
- 例：SocialMemBench 510 题，agent+judge 调用累计 ~5360s，但 16 并发 → 墙钟仅 345s。

---

## 5. 当前 Mem0 三数据集支持现状（2026-06-09，已全部接通）

| 数据集 | BM25 (run_baseline.py) | Mem0 (run_mem0.py) |
|---|---|---|
| GroupMemBench | ✅ 全流程跑通 | ✅ 全流程跑通 |
| SocialMemBench | ✅ | ✅ 已接 bench_loaders + 单 batch 冒烟跑通 |
| EverMemBench | ✅ | ✅ 已接 bench_loaders + 单 batch 冒烟跑通 |

`run_mem0.py` 已改用 `bench_loaders.iter_units(--benchmark, ...)`：逐单元(域/网络/话题)各建独立记忆库
→ 入库该单元消息 → 答该单元的题（user_id=unit）。冒烟(各入 1 批 50 条 + 几题)均端到端跑通
（准确率 0% 是覆盖仅 0.5% 所致，非管线问题）。用法示例：
```
run_mem0.py --benchmark evermem  --domain 01           --parallel-extract 16 ...
run_mem0.py --benchmark socialmem --domain grp_xxx     --parallel-extract 16 ...
```
