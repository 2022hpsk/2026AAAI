#!/usr/bin/env python3
"""本地 Qwen 嵌入服务（OpenAI 兼容 /v1/embeddings）—— 给 HippoRAG 当 embedding 后端用。

为什么需要它：HippoRAG 要 embedder，但 DeepSeek 没有 embedding API；GritLM/NVEmbed 要 GPU。
方案：本地用开源 Qwen 嵌入模型(sentence-transformers)起一个 OpenAI 兼容端点，HippoRAG 的
embedding_base_url 指向它即可（CPU/GPU 自适应；有 GPU 自动用 GPU）。

启动（在装了 sentence-transformers + fastapi 的环境，如 hippo 或主 venv）：
  EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B PORT=8900 python embed_server.py
然后 HippoRAG: embedding_base_url=http://127.0.0.1:8900/v1, embedding_model_name=<同名>。

接口：POST /v1/embeddings  {"model": "...", "input": ["text1","text2"]}
返回：{"data":[{"embedding":[...], "index":0}, ...], "model": "...", "usage":{...}}
"""
from __future__ import annotations
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "8")
from typing import List, Union

from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch

MODEL_NAME = os.environ.get("EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[embed_server] 加载 {MODEL_NAME} 到 {DEVICE} ...", flush=True)
_model = SentenceTransformer(MODEL_NAME, device=DEVICE)
print(f"[embed_server] 就绪；维度={_model.get_sentence_embedding_dimension()}", flush=True)

app = FastAPI()


class EmbReq(BaseModel):
    input: Union[str, List[str]]
    model: str = MODEL_NAME


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "device": DEVICE,
            "dim": _model.get_sentence_embedding_dimension()}


@app.post("/v1/embeddings")
def embeddings(req: EmbReq):
    texts = [req.input] if isinstance(req.input, str) else req.input
    vecs = _model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=64)
    data = [{"object": "embedding", "index": i, "embedding": v.tolist()}
            for i, v in enumerate(vecs)]
    n = sum(len(t.split()) for t in texts)
    return {"object": "list", "data": data, "model": req.model,
            "usage": {"prompt_tokens": n, "total_tokens": n}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8900")), log_level="warning")
