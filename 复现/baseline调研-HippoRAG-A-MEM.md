# HippoRAG / A-MEM 复现可行性 + 集成方案

GroupMemBench 论文里除了 BM25/Mem0，还比较了 **A-MEM** 和 **HippoRAG**。本文结论：
**两者都开源、都可复现**；A-MEM 与 Mem0 同构、接入成本低（已给 `run_amem.py`）；
HippoRAG 更重（知识图谱 + PageRank + OpenIE），接入成本中等偏高，给出方案。

> 共同前提：和 BM25/Mem0 一样，问答(QA-agent)+判分(judge)统一走我们的 DeepSeek 客户端
> （`llm_clients.make_client("deepseek")`），保证四个 baseline 的 QA/judge 完全可比；
> 各系统只贡献"检索"那一段。⚠️ 未经用户允许不真实调 API。

---

## 1. A-MEM（Agentic Memory，NeurIPS'25）

- **开源**：`github.com/agiresearch/A-mem`（官方）；PyPI 有 `a-mem` / `agentic-memory`。可复现。✅
- **架构**：开源框架，本地运行。embedding 用本地 `all-MiniLM-L6-v2`（不调 API）；
  "笔记构建/链接"(Zettelkasten 风格)那步调商用 LLM（`llm_backend="openai"` 或 `ollama`）。
  与 **Mem0 同构**：框架本地 + 调 LLM 做记忆构建 + 检索回"记忆文本"。
- **API**（已核对官方 README）：
  ```python
  from agentic_memory.memory_system import AgenticMemorySystem
  ms = AgenticMemorySystem(model_name='all-MiniLM-L6-v2', llm_backend='openai', llm_model='deepseek-v4-flash')
  ms.add_note(content=..., tags=[...], category=..., timestamp='YYYYMMDDHHmm')
  results = ms.search_agentic(query, k=10)
  ```
- **接 DeepSeek**：A-MEM 用 OpenAI SDK，设 `OPENAI_API_KEY=<DeepSeek key>` +
  `OPENAI_BASE_URL=https://api.deepseek.com` + `llm_model="deepseek-v4-flash"`。
  ⚠️ **唯一风险点**：要确认 A-MEM 是否透传 `OPENAI_BASE_URL`（部分实现写死了官方端点）。
  若不透传：① 改用 `llm_backend="ollama"` 本地模型；② 或打个几行小补丁把 base_url 传进去。
- **接入状态**：`run_amem.py` 已写好（复用统一 QA 循环）。**待办**：`git clone + pip install .` 装上、
  验证 base_url 透传、然后（经允许后）小规模试跑。
- **成本提醒**：A-MEM 入库时每条消息都会调 LLM 做笔记构建 → 一个领域 3 万条很贵，
  用 `--max-messages` 截断先验证。

---

## 2. HippoRAG（NeurIPS'24）

- **开源**：`github.com/OSU-NLP-Group/HippoRAG`；PyPI 有 `hipporag`。可复现。✅（成本中高）
- **架构**：RAG + 知识图谱 + Personalized PageRank。两步走：
  **① 索引**：对语料做 **OpenIE**（用 LLM 抽三元组）建知识图谱 + 存 embedding；
  **② 检索**：把 query 实体映射到图节点，跑 Personalized PageRank 排序段落。
- **依赖更重**：torch / transformers / **vllm** / openai / igraph 等；Python>=3.10。
  LLM 通过 LangChain 调（支持 OpenAI 兼容端点 → 可指 DeepSeek）；OpenIE 索引阶段 LLM 调用量大。
- **与我们流程的差异**：HippoRAG 检索单位是"段落/passage"，不是单条消息——
  需要先把多方对话切成 passage（可按 session/频道分块），再喂它索引。
- **接入方案（建议，未写代码以免不可验证）**：
  1. `pip install hipporag`（注意 vllm 在无 GPU 时可改用 OpenAI 兼容后端，避免装 vllm）。
  2. 写 `hipporag_index(messages)`：把每个单元的消息按"频道/session 分块"成 passage 列表，
     调 HippoRAG 的 index API 建图（LLM 走 DeepSeek）。
  3. 写 `retrieve(query, k)`：调 HippoRAG 检索，返回 top-k passage 文本。
  4. QA/judge 复用统一 DeepSeek 客户端（同 BM25/Mem0/A-MEM）。
- **成本/工期提醒**：OpenIE 索引 = 大量 LLM 调用（比 A-MEM 还重）；建议先在**单个领域、
  截断消息**上跑通，再考虑全量。无 GPU 时务必用 API 后端而非 vllm。

---

## 3. 优先级建议（不盲目全做）

| 系统 | 可复现 | 接入成本 | LLM 用量 | 建议 |
|---|---|---|---|---|
| BM25 | ✅ 已就绪 | 极低 | 仅 QA+judge | 先出数字（motivation 核武器） |
| Mem0 | ✅ 已就绪 | 低 | 入库抽取 + QA | 第二个出（training-free 对照） |
| A-MEM | ✅ `run_amem.py` | 低-中 | 入库构建 + QA | 第三个；先验证 base_url 透传 |
| HippoRAG | ✅ 方案 | 中-高 | OpenIE 索引(重) + QA | 最后；先小规模、用 API 后端 |

四个 baseline 的 QA-agent + judge 全部统一走 DeepSeek `deepseek-v4-flash`，
这样跨系统的相对比较（"BM25 ≈ Mem0/A-MEM"这个 motivation）才严格成立。
