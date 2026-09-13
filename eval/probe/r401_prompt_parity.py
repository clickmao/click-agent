#!/usr/bin/env python3
"""R401 prompt 对等: **跨实现**字节级对账 (探针 python 渲染 vs 引擎 C# 模板渲染)。

为什么必须有这一层 (缺陷取证, R401 步2, 2026-09-14)
--------------------------------------------------
只做「送达对账」是有盲区的: A4 比的是「我方渲染 sha256」与「引擎回显 sha256」——
两者对**同一串错误字节恒等**, 属**自证型断言**: 渲染本身错了它照样全绿。

实测缺陷: 探针把特殊符号 **id (int)** 传给模板变量 (`bos_token=151646`), 模板里
`{{bos_token}}` 于是渲染成**字面 6 字符 "151646"**, 而不是 BOS 特殊符号
`<｜begin▁of▁sentence｜>` ⇒ 送进引擎的 prompt 首位是垃圾前缀, 而 A4 全绿。

唯一能发现它的证据是**独立实现对同一模板的渲染结果**。引擎侧有现成的独立实现:
`agent.rover generate --chat` 读的是同一个 GGUF `tokenizer.chat_template`, 但由 **C#
Jinja 子集解释器** (src/agent.rover/token/ChatTemplate.cs) 执行 —— 两条实现链
(python jinja2 / C# 子集) 对同一 (模板, 消息) 必须给出**逐字节相同**的 prompt。

用法
----
    python3 eval/probe/r401_prompt_parity.py            # 对 taskset 全量任务对账
    python3 eval/probe/r401_prompt_parity.py --limit 1

退出码: 0 = 全部逐字节相等; 1 = 存在不一致 (测量无效, 不许给分); 2 = 环境缺失。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "eval", "probe"))

CST = timezone(timedelta(hours=8))
DEFAULT_MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
DEFAULT_CLI = os.path.join(ROOT, "src", "agent.rover", "bin", "Release", "net10.0", "agent.rover")
DEFAULT_SYSTEM = "你是严谨的编程与数学助手。请直接给出完整可运行的答案。"
TASKSET = os.path.join(ROOT, "data", "probe", "r401", "taskset-r401.json")
OUT = os.path.join(ROOT, "eval", "rover", "r401", "prompt-parity-crossimpl.json")


def _engine_env() -> dict:
    """引擎是 apphost: 缺共享运行时 ⇒ exit 131 (app-launch-failed)。显式给 env, 不依赖调用方 shell。"""
    env = dict(os.environ)
    dr = os.environ.get("DOTNET_ROOT") or os.path.expanduser("~/.dotnet")
    if os.path.isdir(dr):
        env["DOTNET_ROOT"] = dr
        env["PATH"] = dr + os.pathsep + env.get("PATH", "")
    return env


def engine_chat_sha(model: str, system: str, user: str, *, cli=None,
                    fallback: bool = False, timeout: int = 600) -> dict:
    """跑真引擎的 chat 路径 (max_tokens=1, 只要 render 不关心生成), 取它落盘的 prompt_sha256。

    fallback=True 时加 `--chat-fallback-deepseek` ⇒ 走引擎**硬编码版式**渲染器
    (即模板缺失时的兜底路径), 用于回答「本模型的模板与硬编码版式是否等价」这个事实问题。
    """
    cli = cli or DEFAULT_CLI
    jf = os.path.join("/tmp", "r401-parity-%s-%s.json" % ("fallback" if fallback else "tmpl",
                                                          abs(hash((model, system, user))) % 10**8))
    cmd = [cli, "generate", model, "--chat", "--system", system, "--prompt", user,
           "--max-tokens", "1", "--temperature", "0", "--seed", "0", "--json", jf]
    if fallback:
        cmd.append("--chat-fallback-deepseek")
    if os.path.exists(jf):
        os.remove(jf)                       # 清残留: 否则崩溃时旧产物会被读成本轮结果
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=_engine_env())
    except subprocess.TimeoutExpired:
        return {"rc": -9, "error": "timeout"}
    rec = {"rc": p.returncode, "stderr_tail": (p.stderr or "")[-300:]}
    if p.returncode != 0 and not os.path.exists(jf):
        rec["error"] = ("app-launch-failed(missing-runtime)" if "app-launch-failed" in (p.stderr or "")
                        else "exit=%d" % p.returncode)
    if os.path.exists(jf):
        try:
            with open(jf, encoding="utf-8-sig", errors="replace") as fh:
                j = json.load(fh)
            rec.update({"prompt_sha256": j.get("prompt_sha256"), "prompt_tokens": j.get("prompt_tokens"),
                        "stop": j.get("stop"), "fallback_used": j.get("chat_fallback_used")})
        except Exception as e:  # 解析失败必须出声, 不静默
            rec["error"] = "json-parse: %s" % e
    else:
        rec["error"] = "no-json-artifact"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("AGENTFRAMEWORK_ROVER_MODEL", DEFAULT_MODEL))
    ap.add_argument("--taskset", default=TASKSET)
    ap.add_argument("--system", default=DEFAULT_SYSTEM)
    ap.add_argument("--cli", default=DEFAULT_CLI)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    if not os.path.exists(a.model):
        print("缺模型: %s (前置存在检查失败, 立即退出)" % a.model)
        return 2
    if not os.path.exists(a.cli):
        print("缺 CLI: %s (先 build)" % a.cli)
        return 2

    from rover_prompt import render_prompt  # noqa: E402  (同目录探针模块)

    with open(a.taskset, encoding="utf-8-sig", errors="replace") as fh:
        tasks = json.load(fh)
    if a.limit:
        tasks = tasks[:a.limit]

    rows, all_equal = [], True
    for t in tasks:
        text, att = render_prompt(a.model, a.system, t["prompt"])
        eng = engine_chat_sha(a.model, a.system, t["prompt"], cli=a.cli)
        same = bool(att["prompt_sha256"]) and eng.get("prompt_sha256") == att["prompt_sha256"]
        all_equal = all_equal and same
        rows.append({
            "tid": t["tid"], "family": t.get("family"),
            "python_sha256": att["prompt_sha256"], "engine_sha256": eng.get("prompt_sha256"),
            "byte_equal": same, "engine_rc": eng.get("rc"), "engine_prompt_tokens": eng.get("prompt_tokens"),
            "python_chars": att["prompt_chars"], "bos_token": att.get("bos_token"),
            "special_tokens_resolved": att.get("special_tokens_resolved"),
            "literal_id_prefix": bool(_literal_id_prefix(text)),
            "engine_error": eng.get("error"),
        })
        print("%-6s byte_equal=%-5s py=%s eng=%s" % (t["tid"], same, att["prompt_sha256"][:16],
                                                     (eng.get("prompt_sha256") or "n/a")[:16]))

    # 事实 (非断言): 本模型的模板渲染 vs 引擎硬编码兜底版式 —— 等价/不等价都如实记录
    fb = engine_chat_sha(a.model, a.system, tasks[0]["prompt"], cli=a.cli, fallback=True) if tasks else {}
    tpl0 = rows[0]["python_sha256"] if rows else None
    artifact = {
        "schema": "r401-prompt-parity-crossimpl/1",
        "ts": datetime.now(CST).isoformat(timespec="seconds"),
        "line": "rover.prompt_parity_crossimpl",
        "model": a.model,
        "task": "跨实现渲染对照: python(jinja2) vs 引擎(C# Jinja 子集) 对同一 GGUF chat_template",
        "verdict": "all-byte-equal" if all_equal else "MISMATCH",
        "n": len(rows), "byte_equal": sum(1 for r in rows if r["byte_equal"]),
        "rows": rows,
        "facts": {
            "engine_hardcoded_fallback_sha256": fb.get("prompt_sha256"),
            "engine_fallback_equals_template_for_this_model": bool(fb.get("prompt_sha256") == tpl0),
            "note": ("本模型 (DeepSeek 风格模板) 硬编码兜底与模板渲染相同 ⇒ 'prompt != 硬编码版式' "
                     "**不能**作为通用有效性断言 (它是模型相关事实, 非缺陷指示)"),
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, ensure_ascii=False, indent=2)
    print("→ %s  verdict=%s (%d/%d byte-equal)" % (OUT, artifact["verdict"], artifact["byte_equal"], len(rows)))
    return 0 if all_equal else 1


def _literal_id_prefix(text: str) -> str:
    """渲染结果是否以「字面数字 id」开头 (缺陷回归哨兵: 曾出现 '151646你是…')。"""
    i = 0
    while i < len(text) and text[i].isdigit():
        i += 1
    return text[:i] if i >= 4 else ""


if __name__ == "__main__":
    raise SystemExit(main())
