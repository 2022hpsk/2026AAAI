"""对上游 GroupMemBench 评测库的非侵入式补丁（不改克隆代码，保证能干净 git pull）。

两个问题（都来自"上游为 gpt-5 调参"，换 DeepSeek 后不合适）：
1. **token 太小被截断**：run_qa 把 agent 写死 512、judge 写死 256。DeepSeek reasoning 啰嗦，
   常在写出 `Final: Correct/Incorrect` 之前就用光 token → 结论被截 → 判成 "Unclear"（按错算）。
2. **temperature=0.2 不可复现**：call_chat 写死 0.2，benchmark 数字会跑一次抖一次。

解法：运行时整体替换 `eval_lib.call_chat`——抬高 token 下限（judge≥512, agent≥1024）+ pin
temperature=0（判分确定性）。run_qa 按模块全局名调用 call_chat，替换模块属性即生效。
"""
from __future__ import annotations


def patch_token_budgets(min_judge: int = 512, min_agent: int = 1024,
                        temperature: float = 0.0) -> None:
    import baselines.rag_common.eval_lib as elib
    from llm_utils import chat_completion_text

    def patched(client, model, system_prompt, user_prompt, max_tokens):
        # 上游：judge 传 256、agent 传 512 → 据此区分该抬到哪个下限
        floor = min_judge if max_tokens <= 256 else min_agent
        return chat_completion_text(
            client, model=model,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            max_tokens=max(max_tokens, floor), temperature=temperature)

    elib.call_chat = patched
    print(f"[补丁] LLM token 预算 judge≥{min_judge}/agent≥{min_agent}，temperature={temperature}"
          f"（避免 DeepSeek 结论被截断 + 保证可复现）")
