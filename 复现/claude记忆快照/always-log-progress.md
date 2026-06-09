---
name: always-log-progress
description: 硬规则——每次操作结束都要把进展写进 CLAUDE.md 和 复现/README.md
metadata: 
  node_type: memory
  type: workflow
  originSessionId: ebb81088-a7be-49ea-a3f5-b3aa3a90992c
---

**硬性工作规则（用户明确要求）**：每完成一步操作/实验，都必须把进展写进**两个地方**：
1. 项目根 `CLAUDE.md`（项目圣经/记忆引导，记总体进度、P 阶段状态）
2. `复现/README.md`（复现目录的实验进展、跑出的数字、踩的坑）

**Why:** 用户要求进度始终可追溯、随时能"继承记忆"。
**How:** 不要等用户提醒；每轮实验/重要代码改动后主动更新这两份文件（中文）。包括：跑了什么、
出了什么数字、发现/修了什么 bug、下一步。见 [[aaai-repro-env]]。
