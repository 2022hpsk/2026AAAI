"""GroupMemBench 复现用的 LLM 客户端适配器。

上游 UCSB-NLP-Chang/GroupMemBench 的所有 LLM 调用都走 OpenAI 那套接口形态：

    client.chat.completions.create(model=, messages=[...], max_tokens=/
        max_completion_tokens=, temperature=) -> resp.choices[0].message.content

它默认的 agent + judge 模型是 ``gpt-5``（走 OpenAI / Azure OpenAI）。但本机
**没有 OpenAI key**；唯一的 LLM 端点是 Anthropic
（``ANTHROPIC_BASE_URL=https://api.anthropic.com``），用的是原生 Messages API，
不是 chat.completions。

本模块提供 ``make_client(...)``，返回一个同样暴露 ``.chat.completions.create``
接口的客户端，底层可切换三种 provider，且**完全不改动克隆的上游仓库**
（保证以后能干净地 git pull）：

  * ``anthropic``       -> Anthropic Messages API（需要 ANTHROPIC_API_KEY）。
  * ``openai``/``local`` -> 任意 OpenAI 兼容端点，例如 GPU 到位后的本地 vLLM
                          服务（``vllm serve Qwen/Qwen2.5-7B-Instruct``）。设置
                          OPENAI_BASE_URL + OPENAI_API_KEY（本地服务 key 随便填）。

在 runner 里这样用：

    from llm_clients import make_client
    client = make_client(provider="anthropic")
    # 然后把 client 交给上游 baselines.rag_common.eval_lib.run_qa(...)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


# --------------------------------------------------------------------------- #
# 最小化的、仿 OpenAI 形态的响应对象
# --------------------------------------------------------------------------- #
@dataclass
class _Message:
    content: str
    role: str = "assistant"


@dataclass
class _Choice:
    message: _Message
    finish_reason: str = "stop"
    index: int = 0


@dataclass
class _Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class _Response:
    choices: List[_Choice]
    usage: _Usage


# --------------------------------------------------------------------------- #
# 模拟 `client.chat.completions.create` 的 Anthropic 适配器
# --------------------------------------------------------------------------- #
def _split_system(messages: Sequence[Dict[str, Any]]):
    """OpenAI 把 system 提示放在 messages 列表里；Anthropic 要求它作为顶层 `system`
    参数。这里把 system 抽出来，其余消息原样传递。"""
    system_parts: List[str] = []
    convo: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "system":
            if content:
                system_parts.append(content if isinstance(content, str) else str(content))
        else:
            convo.append({"role": role, "content": content})
    # Anthropic 要求第一条消息必须是 user 角色
    if not convo or convo[0]["role"] != "user":
        convo.insert(0, {"role": "user", "content": "."})
    return "\n\n".join(system_parts), convo


class _AnthropicCompletions:
    def __init__(self, sdk_client: Any):
        self._c = sdk_client

    def create(
        self,
        *,
        model: str,
        messages: Sequence[Dict[str, Any]],
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **_ignored: Any,
    ) -> _Response:
        system, convo = _split_system(messages)
        budget = max_tokens or max_completion_tokens or 1024
        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": int(budget),
            "messages": convo,
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = float(temperature)
        resp = self._c.messages.create(**kwargs)
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        usage = _Usage(
            prompt_tokens=getattr(resp.usage, "input_tokens", 0),
            completion_tokens=getattr(resp.usage, "output_tokens", 0),
            total_tokens=getattr(resp.usage, "input_tokens", 0)
            + getattr(resp.usage, "output_tokens", 0),
        )
        return _Response(choices=[_Choice(message=_Message(content=text))], usage=usage)


class _Chat:
    def __init__(self, completions: Any):
        self.completions = completions


class AnthropicOpenAIClient:
    """对外暴露 `.chat.completions.create(...)`，底层调用 Anthropic SDK。"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 max_retries: int = 5):
        import anthropic  # 局部 import，缺依赖时本模块仍可被导入

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "没有可用的 ANTHROPIC_API_KEY。环境里的 ANTHROPIC_BASE_URL 端点是用 "
                "Claude Code 的 OAuth token 鉴权的，不能拿来做批量 API 调用。请在 "
                "复现/.env 里填入 ANTHROPIC_API_KEY（或改用 --llm-provider local 接本地 "
                "vLLM 服务）才能跑 QA-agent / judge。"
            )
        client_kwargs: Dict[str, Any] = {"api_key": key, "max_retries": max_retries}
        if base_url or os.environ.get("ANTHROPIC_BASE_URL"):
            client_kwargs["base_url"] = base_url or os.environ["ANTHROPIC_BASE_URL"]
        self._sdk = anthropic.Anthropic(**client_kwargs)
        self.chat = _Chat(_AnthropicCompletions(self._sdk))


# --------------------------------------------------------------------------- #
# 工厂函数
# --------------------------------------------------------------------------- #
def make_client(provider: str, *, api_key: Optional[str] = None,
                base_url: Optional[str] = None) -> Any:
    """按 provider 返回一个暴露 `.chat.completions.create` 接口的客户端。

    provider：
      - "anthropic"：Anthropic Messages API（需要 ANTHROPIC_API_KEY）。
      - "deepseek"：DeepSeek（OpenAI 兼容，base_url=https://api.deepseek.com，
        需要 DEEPSEEK_API_KEY，默认模型 deepseek-v4-flash）。
      - "openai" | "local"：OpenAI 兼容端点（OPENAI_API_KEY + 可选 OPENAI_BASE_URL；
        本地 vLLM 服务的 key 随便填一个非空值即可）。
    """
    p = (provider or "").strip().lower()
    if p == "anthropic":
        return AnthropicOpenAIClient(api_key=api_key, base_url=base_url)
    if p == "deepseek":
        # DeepSeek 是 OpenAI 兼容接口：base_url=https://api.deepseek.com，Bearer 鉴权
        from openai import OpenAI

        key = api_key or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "没有可用的 DEEPSEEK_API_KEY。请在 复现/.env 里填 DEEPSEEK_API_KEY 才能跑 "
                "QA-agent / judge（默认模型 deepseek-v4-flash）。"
            )
        url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com")
        return OpenAI(api_key=key, base_url=url, max_retries=5)
    if p in ("openai", "local", "vllm"):
        from openai import OpenAI

        key = api_key or os.environ.get("OPENAI_API_KEY") or "EMPTY"
        url = base_url or os.environ.get("OPENAI_BASE_URL")
        kwargs: Dict[str, Any] = {"api_key": key, "max_retries": 5}
        if url:
            kwargs["base_url"] = url
        return OpenAI(**kwargs)
    raise ValueError(f"未知 provider: {provider!r}。可用：anthropic | deepseek | openai | local。")
