#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 单侧跑器: 按题集逐题在**独立工作区**跑一侧, 落全部读数。

side=agent : 本侧 AOT agenthost (工作区=AGENTFRAMEWORK_WORKSPACE; cwd=仓库, 与 R502-R505 同夹具)
side=codex : 外部真值 codex-cli (复用 r504 已验 run_one: codex exec --json -C work)
读数: tokens 一律由 adapter 落盘 (usage_from_dumps) 汇总 + codex 自带 usage 交叉核对;
      产物 = 工作区文件清单 (判分只吃这些文件的**真实行为**)。
"""
from __future__ import annotations
import argparse, importlib.util, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, HERE)
import usage_from_dumps as ufd  # noqa: E402


def load_env_local(path=None):
    env = {}
    p = path or os.path.join(REPO, ".env.local")
    if not os.path.exists(p):
        return env
    for ln in open(p, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        v = v.strip().strip('"').strip("'")
        env[k.strip()] = v
    return env


def load_codex_engine():
    p = os.path.join(REPO, "eval/rover/r504/codex_solver_r504.py")
    spec = importlib.util.spec_from_file_location("codex_solver_r504", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dump_index(d, side):
    n = 0
    for fn in os.listdir(d):
        if fn.startswith("side-%s-" % side) and fn.endswith(".json"):
            try:
                n = max(n, int(fn[:-5].rsplit("-", 1)[1]))
            except Exception:
                pass
    return n


def artifacts(work):
    out = []
    for root, dirs, files in os.walk(work):
        dirs[:] = [x for x in dirs if x not in ("__pycache__", ".git")]
        for f in files:
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, work)
            try:
                out.append({"path": rel, "bytes": os.path.getsize(fp)})
            except OSError:
                pass
    return sorted(out, key=lambda r: r["path"])


def run_agent(task, out_dir, args, env_local):
    work = os.path.join(out_dir, task["tid"], "work")
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ)
    env.update(env_local)
    env["AGENTFRAMEWORK_WORKSPACE"] = work
    env["AGENTFRAMEWORK_PY_RUN"] = "1"
    env["AGENTFRAMEWORK_ACTION_AUDIT"] = os.path.join(out_dir, task["tid"], "audit")
    if args.max_steps:
        env["AGENTFRAMEWORK_ACTION_MAX_STEPS"] = str(args.max_steps)
    argv = [args.agent_bin, "-q", task["prompt"], "--output-mode", "text",
            "--session-id", "r511-%s-%s" % (args.arm, task["tid"])]
    t0 = time.time()
    rc, out, err = None, "", ""
    try:
        p = subprocess.run(argv, cwd=args.cwd, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=args.timeout)
        rc, out, err = p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired as e:
        rc = 124
        out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = "TIMEOUT"
    except Exception as e:
        rc, err = 127, str(e)
    el = round(time.time() - t0, 2)
    with open(os.path.join(out_dir, task["tid"], "agent.stdout.txt"), "w", encoding="utf-8") as fh:
        fh.write(out)
    with open(os.path.join(out_dir, task["tid"], "agent.stderr.txt"), "w", encoding="utf-8") as fh:
        fh.write(err)
    led = []
    ap = os.path.join(out_dir, task["tid"], "audit", "action_loop.jsonl")
    if os.path.exists(ap):
        for ln in open(ap, encoding="utf-8"):
            try:
                led.append(json.loads(ln))
            except Exception:
                pass
    return {"rc": rc, "elapsed_s": el, "reply": out, "stderr_head": err[:300],
            "ledger": led, "ledger_calls": len(led),
            "ledger_steps": max([int(r.get("step") or 0) for r in led] or [0]),
            "usage_local": None}


def run_codex(task, out_dir, args, eng):
    work = os.path.join(out_dir, task["tid"], "work")
    os.makedirs(work, exist_ok=True)
    d = {"bin": args.codex_bin, "port": str(args.adapter_port), "model": args.model,
         "work": work, "raw": os.path.join(out_dir, task["tid"], "raw"),
         "audit": os.path.join(out_dir, task["tid"], "codex-audit.jsonl"),
         "timeout": float(args.timeout)}
    reply, usage, meta = eng.run_one(task["prompt"], d)
    return {"rc": meta.get("rc"), "elapsed_s": meta.get("elapsed_s"), "reply": reply,
            "stderr_head": "", "ledger": [], "ledger_calls": 0, "ledger_steps": 0,
            "usage_self": usage}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["agent", "codex"], required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--taskset", default=os.path.join(HERE, "taskset-r511.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--adapter-dir", required=True)
    ap.add_argument("--adapter-port", default=os.environ.get("R511_ADAPTER_PORT", "48660"))
    ap.add_argument("--agent-bin", default=os.environ.get("R511_AGENT_BIN", "/tmp/pub_r504/agenthost/agenthost"))
    ap.add_argument("--codex-bin", default=os.path.expanduser("~/.agentframework/tools/codex-env/node_modules/.bin/codex"))
    ap.add_argument("--model", default="deepseek-flash")
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--tasks", default="")
    ap.add_argument("--cwd", default=REPO)
    args = ap.parse_args()

    ts = json.load(open(args.taskset, encoding="utf-8"))
    want = [t for t in ts["tasks"] if (not args.tasks or t["tid"] in args.tasks.split(","))]
    env_local = load_env_local()
    eng = load_codex_engine() if args.side == "codex" else None
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.adapter_dir, exist_ok=True)

    res = []
    for task in want:
        n0 = dump_index(args.adapter_dir, args.side)
        if args.side == "agent":
            meta = run_agent(task, args.out, args, env_local)
        else:
            meta = run_codex(task, args.out, args, eng)
        n1 = dump_index(args.adapter_dir, args.side)
        # 只在两侧都跑完后由汇总器按【本臂本侧】区段取值; 此处仅记录区段
        row = {"tid": task["tid"], "side": args.side, "arm": args.arm, "adapter_range": [n0 + 1, n1],
               "artifacts": artifacts(os.path.join(args.out, task["tid"], "work")),
               "reply_chars": len(meta.get("reply") or ""),
               "reply_head": (meta.get("reply") or "")[:600]}
        for k in ("rc", "elapsed_s", "ledger_calls", "ledger_steps", "usage_self", "stderr_head"):
            row[k] = meta.get(k)
        res.append(row)
        print(json.dumps({k: row[k] for k in ("tid", "side", "arm", "rc", "elapsed_s",
                                              "ledger_calls", "ledger_steps", "reply_chars",
                                              "adapter_range")}, ensure_ascii=False), flush=True)
    json.dump({"side": args.side, "arm": args.arm, "out": args.out, "tasks": res},
              open(os.path.join(args.out, "side-run.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
