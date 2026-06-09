#!/usr/bin/env python3
"""下载 SocialMemBench 匿名代码库（anonymous.4open.science/r/SocialMemBench）。

4open.science 的网页是 SPA、raw 文件 403、逐目录 API 又会 401/not_connected，
最可靠的是**整库 ZIP** 端点：/api/repo/<name>/zip。本脚本下载并解压。

用法：./venv/bin/python get_socialmembench_code.py
输出：复现/SocialMemBench-code/（含 eval/ socialmembench/ scripts/ skills/ viewer/ 等官方代码）
"""
from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

ZIP_URL = "https://anonymous.4open.science/api/repo/SocialMemBench/zip"
OUT = Path(__file__).resolve().parent / "SocialMemBench-code"
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def main() -> int:
    print(f"下载整库 ZIP：{ZIP_URL}")
    req = urllib.request.Request(ZIP_URL, headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        blob = r.read()
    print(f"  下载 {len(blob)} 字节，解压到 {OUT} ...")
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        z.extractall(OUT)
        print(f"  共 {len(z.namelist())} 个条目")
    print("[完成]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
