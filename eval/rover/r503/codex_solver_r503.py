#!/usr/bin/env python3
"""R503 外部真值解法器 —— codex-cli 作为 probe 的 `command:` 外部解法 (主线=外部对照自检)。

协议（probe 契约, 见 eval/probe/run_probe.py:718）:
    stdin  = 题面 task["prompt"]（两侧逐字节同, 由冻结题集 sha 保证）
    stdout = 最终回复文本（与 agent 侧同一判分面 = eval/probe/grade.py, 隐藏用例）

铁律
----
E1 同环境: 工作目录由 R503_WORK 指定, 首次调用前须为空/逐字节同夹具。
E3 同模型: 经同一 adapter (adapter_tools.py) 打同一真实模型 deepseek-flash。
E4 零重试: adapter 注入 usage; turn.completed 必带 usage（缺 ⇒ 审计留痕, 不静默）。
E6 机械判分: 本器只负责「拿真值回复」, 不做任何判分/清洗（禁把 stdout 修饰成判分友好）。

fail-closed: rc!=0 / 无 agent_message / 空文本 ⇒ stdout 为空（判分侧记 no_code，不得算绿），
             审计 jsonl 落 rc/errs/耗时，绝不退回「本地伪造回复」。

用法:
    python3 codex_solver_r503.py < 题面.txt            # 单题（probe command: 适配器）
    python3 codex_solver_r503.py --selftest           # 无网络: 抽取/空回/fail-closed 自检
环境:
    R503_CODEX_BIN  codex 可执行 (默认 ~/.agentframework/tools/codex-env/node_modules/.bin/codex)
    R503_ADAPTER_PORT  适配器端口 (默认 48625)
    R503_MODEL       模型名 (默认 deepseek-flash)
    R503_WORK        codex 工作目录 (默认 /tmp/r503_env/codex/work)
    R503_RAW         原始 --json jsonl 落盘目录 (默认 $R503_WORK/../raw)
    R503_AUDIT       审计 jsonl (默认 $R503_WORK/../audit.jsonl)
    R503_TIMEOUT     单题超时秒 (默认 600)
    DSKEY            adapter 鉴权键的环境变量名须为 DSKEY（值取自 AGENTFRAMEWORK_KEYS_DEEPSEEK）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _defaults():
    home = os.path.expanduser("~")
    return {
        "bin": os.environ.get("R503_CODEX_BIN",
                              os.path.join(home, ".agentframework/tools/codex-env/node_modules/.bin/codex")),
        "port": os.environ.get("R503_ADAPTER_PORT", "48625"),
        "model": os.environ.get("R503_MODEL", "deepseek-flash"),
        "work": os.environ.get("R503_WORK", "/tmp/r503_env/codex/work"),
        "raw": os.environ.get("R503_RAW", ""),
        "audit": os.environ.get("R503_AUDIT", ""),
        "timeout": float(os.environ.get("R503_TIMEOUT", "600")),
    }


def codex_cfg(port: str, model: str) -> list:
    """同一真实模型: adapter 作 OpenAI 兼容网关 ⇒ 两侧同上游。"""
    return ["-c", "model_providers.ds.name=ds",
            "-c", "model_providers.ds.base_url=http://127.0.0.1:%s/v1" % port,
            "-c", "model_providers.ds.env_key=DSKEY",
            "-c", "model_provider=ds",
            "-m", model]


def extract_events(text: str):
    """codex --json → (reply, usage, errs, thread_id)。reply = 最后一个 agent_message。"""
    reply, usage, errs, tid = None, None, [], None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        t = e.get("type")
        it = e.get("item") or {}
        if t == "thread.started":
            tid = e.get("thread_id")
        elif t == "item.completed" and it.get("type") == "agent_message":
            reply = it.get("text")
        elif t == "turn.completed":
            usage = e.get("usage")
        elif t == "error":
            errs.append(str(e.get("message"))[:200])
    return reply, usage, errs, tid


def _audit(path: str, row: dict) -> None:
    """审计必落盘; IO 异常留告警不吞（AOT 仪器铁律: 异常必留痕）。"""
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:  # pragma: no cover
        sys.stderr.write("[R503 审计写失败] %s\n" % e)


def run_one(prompt: str, d: dict) -> tuple:
    work = d["work"]
    os.makedirs(work, exist_ok=True)
    raw_dir = d["raw"] or os.path.join(os.path.dirname(work.rstrip("/")), "raw")
    os.makedirs(raw_dir, exist_ok=True)
    n = len([x for x in os.listdir(raw_dir) if x.endswith(".jsonl")]) + 1
    raw_path = os.path.join(raw_dir, "codex-%03d.jsonl" % n)

    env = dict(os.environ)
    env.setdefault("DSKEY", os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK", ""))
    argv = [d["bin"], "exec", "--skip-git-repo-check", "--json", "-C", work,
            "--dangerously-bypass-approvals-and-sandbox"] + codex_cfg(d["port"], d["model"]) + [prompt]
    t0 = time.time()
    rc, out, err = None, "", ""
    try:
        p = subprocess.run(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=d["timeout"])
        rc, out, err = p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired as e:
        out_s = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        rc, out, err = 124, out_s, "TIMEOUT"
    except Exception as e:  # 可执行缺失等
        rc, out, err = 127, "", str(e)
    el = round(time.time() - t0, 2)
    with open(raw_path, "w", encoding="utf-8") as fh:
        fh.write(out + ("\n--- stderr ---\n" + err if err.strip() else ""))

    reply, usage, errs, tid = extract_events(out)
    ok = (rc == 0) and bool((reply or "").strip())
    _audit(d["audit"] or os.path.join(os.path.dirname(work.rstrip("/")), "audit.jsonl"),
           {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "raw": raw_path, "rc": rc, "ok": ok,
            "elapsed_s": el, "thread_id": tid, "usage": usage, "errs": errs,
            "prompt_chars": len(prompt), "reply_chars": len(reply or ""), "stderr_head": err[:200]})
    if not ok:
        sys.stderr.write("[R503 fail-closed] rc=%s errs=%s (stdout 置空 ⇒ 判分侧记 no_code)\n" % (rc, errs[:2]))
        return "", usage, {"rc": rc, "elapsed_s": el, "ok": False}
    return reply, usage, {"rc": rc, "elapsed_s": el, "ok": True}


def selftest() -> int:
    fx = os.path.join(HERE, "codex_fixture_r503.jsonl")
    text = open(fx, encoding="utf-8").read()
    reply, usage, errs, tid = extract_events(text)
    cases = []
    cases.append(("正常抽取 agent_message", reply is not None and "def " in reply and tid == "th_fixture"))
    cases.append(("usage 抽取", (usage or {}).get("input_tokens") == 1234))
    cases.append(("错误事件留痕", any("boom" in e for e in errs)))
    bad_reply, bad_usage, _, _ = extract_events('{"type":"turn.failed","message":"x"}\n')
    cases.append(("无 agent_message ⇒ None(空回)",
                  bad_reply is None and bad_usage is None))
    # fail-closed 分支: 引擎不可达 ⇒ 空 stdout（不伪造回复）
    d = _defaults()
    d.update({"bin": "/nonexistent/codex-r503", "work": "/tmp/r503_selftest/work",
              "raw": "/tmp/r503_selftest/raw", "audit": "/tmp/r503_selftest/audit.jsonl"})
    r, u, meta = run_one("hi", d)
    cases.append(("引擎缺失 ⇒ 空回 + rc!=0 + 审计留痕", r == "" and meta["ok"] is False and meta["rc"] == 127))
    audit_ok = os.path.exists(d["audit"]) and json.loads(open(d["audit"], encoding="utf-8").read().splitlines()[-1])["ok"] is False
    cases.append(("审计 jsonl 落盘可读", audit_ok))
    bad = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(("  PASS " if ok else "  FAIL ") + n)
    print("codex_solver_r503 selftest: %d/%d" % (len(cases) - len(bad), len(cases)))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="只打印将执行的 argv（校验端口/模型/二进制定位）")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    d = _defaults()
    if a.dry_run:
        print(json.dumps({"bin": d["bin"], "exists": os.path.exists(d["bin"]),
                          "argv_prefix": [d["bin"], "exec", "--json", "-C", d["work"]] + codex_cfg(d["port"], d["model"]),
                          "work": d["work"], "audit": d["audit"]}, ensure_ascii=False, indent=1))
        return 0 if os.path.exists(d["bin"]) else 3
    prompt = sys.stdin.read()
    reply, _usage, _meta = run_one(prompt, d)
    sys.stdout.write(reply)          # 判分面: 原样交回, 不做任何修饰
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
