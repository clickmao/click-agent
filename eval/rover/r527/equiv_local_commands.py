#!/usr/bin/env python3
"""R527 等价性夹具 — 确定性本地命令族的黄金摘要采集/比对。

用途: 铁律 13「方法内部逻辑抽取属语义变换, 必须有等价性夹具才算数」。
本夹具只喂**确定性本地命令**(`-q <cmd>` 在进入 LLM 之前被本地路由/早退分支处理),
故前后两次运行的输出应当逐字节相同 —— 是「外部可见行为不变」的机械证据。

口径:
  * 每条命令在**独立 cwd 沙箱**内跑 (与轮次无关的临时目录), 环境 = env -i 净化 + 必需变量;
  * 归一化: 抹掉 cwd 路径、ISO 时间戳、耗时/心跳等易变字段 (抹掉的字段名与正则均落盘);
  * 输出 = {cmd: {rc, sha256, text}}; 比对即逐字段等值, 任一不等 ⇒ 夹具判红。

负控: `--selfcheck` 会注入一条**人造差异**(把某命令 text 尾部加一个字符)并跑同一比对器,
       必须判红 ⇒ 证明比对器有判别力 (非恒绿)。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

CMDS = [
    "/plan",
    "/forecast",
    "/rag",
    "/status",
    "/skills",
    "/staged",
    "/activity",
    "/recall",
    "/llm-service",
    "/model",
]

# 易变字段归一化 (只抹"环境噪声", 不抹被测语义)
NORM = [
    (re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?"), "<TS>"),
    (re.compile(r"[0-9a-f]{32}"), "<HEX32>"),          # guid/拼接 id
    (re.compile(r"\b\d+(\.\d+)?\s*(ms|s)\b"), "<DUR>"),  # 耗时
    (re.compile(r"~?\d[\d,]*\s*tokens?"), "<TOKENS>"),
    (re.compile(r"pid[= ]\d+", re.IGNORECASE), "pid=<N>"),
]


def normalize(text: str, sandbox: str) -> str:
    t = text.replace(sandbox, "<WS>")
    t = t.replace(sandbox.replace("/", "\\"), "<WS>")
    for rx, rep in NORM:
        t = rx.sub(rep, t)
    # 尾随空白/CR 归一 (跨平台无意义差异)
    lines = [ln.rstrip() for ln in t.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip() + "\n"


def run_arm(binary: str, sandbox: str, out_path: str, extra_cmds=()) -> dict:
    if os.path.isdir(sandbox):
        shutil.rmtree(sandbox)
    os.makedirs(sandbox, exist_ok=True)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": sandbox,
        "LANG": "C.UTF-8",
        "TMPDIR": sandbox,
        "DOTNET_ROOT": os.environ.get("DOTNET_ROOT", "/home/agentuser/.dotnet"),
    }
    res = {}
    for cmd in list(CMDS) + list(extra_cmds):
        try:
            p = subprocess.run(
                [binary, "-q", cmd, "--session-id", "r527eq"],
                cwd=sandbox, env=env, capture_output=True, timeout=120,
            )
            # 两流分存 (stdout/stderr 交织顺序由宿主调度决定 ⇒ 合并会造成假差异)
            out_txt = normalize(p.stdout.decode("utf-8", "replace"), sandbox)
            err_txt = normalize(p.stderr.decode("utf-8", "replace"), sandbox)
            res[cmd] = {
                "rc": p.returncode,
                "out_sha256": hashlib.sha256(out_txt.encode()).hexdigest(),
                "err_sha256": hashlib.sha256(err_txt.encode()).hexdigest(),
                "out_text": out_txt,
                "err_text": err_txt,
            }
        except subprocess.TimeoutExpired:
            res[cmd] = {"rc": -9, "out_sha256": "", "err_sha256": "", "out_text": "<TIMEOUT>", "err_text": ""}
    doc = {"binary": binary, "sandbox": sandbox, "cmd_count": len(res), "arms": res}
    with io.open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return doc


def compare(pre: dict, post: dict) -> tuple[bool, list[str]]:
    diffs = []
    for cmd in sorted(set(pre["arms"]) | set(post["arms"])):
        a, b = pre["arms"].get(cmd), post["arms"].get(cmd)
        if a is None or b is None:
            diffs.append(f"{cmd}: 臂缺失 pre={a is not None} post={b is not None}")
            continue
        if a["rc"] != b["rc"]:
            diffs.append(f"{cmd}: rc {a['rc']} -> {b['rc']}")
        for stream in ("out", "err"):
            ka, kb = f"{stream}_sha256", f"{stream}_sha256"
            if a[ka] != b[kb]:
                diffs.append(f"{cmd}: {stream} 文本不等 pre={a[ka][:12]} post={b[kb][:12]}")
    return (len(diffs) == 0), diffs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary")
    ap.add_argument("--sandbox")
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2, metavar=("PRE", "POST"))
    ap.add_argument("--selfcheck", nargs=2, metavar=("PRE", "POST"), help="负控: 注入人造差异后必须判红")
    a = ap.parse_args()

    if a.compare:
        pre = json.load(io.open(a.compare[0], encoding="utf-8"))
        post = json.load(io.open(a.compare[1], encoding="utf-8"))
        ok, diffs = compare(pre, post)
        print(f"COMPARE ok={ok} cmds={len(pre['arms'])} diffs={len(diffs)}")
        for d in diffs:
            print("  ", d)
        return 0 if ok else 1

    if a.selfcheck:
        pre = json.load(io.open(a.selfcheck[0], encoding="utf-8"))
        post = json.load(io.open(a.selfcheck[1], encoding="utf-8"))
        corrupted = json.loads(json.dumps(post))
        k = sorted(corrupted["arms"])[0]
        corrupted["arms"][k]["out_text"] += "X"
        corrupted["arms"][k]["out_sha256"] = hashlib.sha256(corrupted["arms"][k]["out_text"].encode()).hexdigest()
        ok, diffs = compare(pre, corrupted)
        print(f"NC_SELFCHECK ok={ok} (期望 False) diffs={len(diffs)} 注入={k}")
        for d in diffs:
            print("  ", d)
        return 0 if not ok else 1

    doc = run_arm(a.binary, a.sandbox, a.out)
    print(f"ARM binary={a.binary} cmds={doc['cmd_count']} out={a.out}")
    for cmd in sorted(doc["arms"]):
        r = doc["arms"][cmd]
        print(f"  {cmd:14s} rc={r['rc']:3d} out={r['out_sha256'][:12]} err={r['err_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
