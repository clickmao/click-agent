#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""随机能力自检编排器 (R398 长期任务)

作用: 题集(tasks.py) → 解法适配器 → 判定(grade.py) → 结构化摘要(JSON) + 归因表。

解法适配器契约 (与语言/实现无关, 只认文本进文本出):
    oracle              参考解: 程序题走内置参考实现, 数学题回填已知答案 ⇒ 必须 100%
                        (用途: 验证流水线本身, **不是**能力读数, 摘要里标 oracle=true)
    mutation:<kind>     缺陷注入: offbyone / loop / syntax / nocode / hardcode
                        (用途: 负控 —— 流水线必须能把它们判红)
    agent               本 agent 真机自检: 调 AOT agenthost -q <prompt> 取回复
                        (环境: AGENTFRAMEWORK_PY_RUN=1 打开 py 插件; .env.local 提供 keys)
    command:<shell>     外部解法: prompt 从 stdin 进, 回复从 stdout 出
    file:<dir>          从目录读 <tid>.txt 作为回复 (用途: 离线/人工收集)

输出: data/probe/probe-<solver>-<seed>.json
      含 per_task 明细 + 按 kind/family 的通过率 + 失败模式分布 taxonomy
      ⇒ 归因面必须能落到"题族 × 失败模式", 否则无法沉淀经验。

用法
----
    python3 eval/probe/run_probe.py --selftest
    python3 eval/probe/run_probe.py --kind program --n 4 --seed 7 --solver oracle|agent|rover|mutation:<kind>|file:<dir>|command:<cmd>
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grade  # noqa: E402
import tasks as taskgen  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(HERE)), "data", "probe")


# ---------------------------------------------------------------- 参考解 (oracle)

_REF_MAXSUB = """
import sys
d=sys.stdin.read().split(); n=int(d[0]); a=[int(x) for x in d[1:1+n]]
best=cur=a[0]
for x in a[1:]: cur=max(x,cur+x); best=max(best,cur)
print(best)"""

_REF_LONGEST = """
import sys
s=sys.stdin.read().strip(); last={}; st=0; best=0
for i,ch in enumerate(s):
    if ch in last and last[ch]>=st: st=last[ch]+1
    last[ch]=i; best=max(best,i-st+1)
print(best)"""

_REF_BRACKET = """
import sys
s=sys.stdin.read().strip(); no=nc=0
for ch in s:
    if ch=='(': no+=1
    elif no: no-=1
    else: nc+=1
print(no+nc)"""

_REF_INTERVAL = """
import sys
d=sys.stdin.read().split(); n=int(d[0]); q=int(d[1]); a=[int(x) for x in d[2:2+n]]
p=[0]
for x in a: p.append(p[-1]+x)
out=[]; idx=2+n
for _ in range(q):
    l=int(d[idx]); r=int(d[idx+1]); idx+=2; out.append(str(p[r+1]-p[l]))
print('\\n'.join(out))"""

_REF_SPIRAL = """
import sys
d=sys.stdin.read().split(); R=int(d[0]); C=int(d[1]); v=[int(x) for x in d[2:]]
m=[v[i*C:(i+1)*C] for i in range(R)]; out=[]
while m:
    out+=m.pop(0)
    if m and m[0]:
        for row in m: out.append(row.pop())
    if m: out+=reversed(m.pop())
    if m and m[0]:
        for row in reversed(m): out.append(row.pop(0))
print(' '.join(map(str,out)))"""

_REF_CSV = """
import sys
from itertools import groupby
pairs=sorted((ln.split(',')[0], int(ln.split(',')[1])) for ln in sys.stdin.read().strip().splitlines())
print(';'.join('%s=%d'%(k,sum(v for _,v in g)) for k,g in groupby(pairs,key=lambda t:t[0])))"""

_REF_PAIRCLOSE = """
import sys
d = sys.stdin.read().split()
n = int(d[0])
a = [int(x) for x in d[1:1 + n]]
best = None
for i in range(n):
    for j in range(i + 1, n):
        s = a[i] + a[j]
        k = (abs(s), s)
        if best is None or k < best[0]:
            best = (k, s)
print(best[1])
"""

REF_SRC = {
    "pair_closest_abs_sum": _REF_PAIRCLOSE.strip(),
    "max_subarray": _REF_MAXSUB.strip(),
    "longest_unique": _REF_LONGEST.strip(),
    "bracket_fix": _REF_BRACKET.strip(),
    "interval_sum": _REF_INTERVAL.strip(),
    "matrix_spiral": _REF_SPIRAL.strip(),
    "csv_agg": _REF_CSV.strip(),
}

PROG_MUTATIONS = ("extra", "loop", "syntax", "nocode", "hardcode")   # 程序题缺陷注入族


def oracle_reply(task: dict, mutation: str = "") -> str:
    """参考解回复; mutation 非空时注入指定缺陷 (负控用)。

    注入的缺陷都必须是**可判定**的: 多余输出 / 不终止 / 语法错 / 无代码 / 硬编码公开样例。
    """
    if task["kind"] == "math":
        if mutation == "wrongfinal":
            num = task["answer"].split("/")[0].lstrip("-")
            rep = "FINAL: %d" % (int(num) + 1)
        elif mutation == "nofinal":
            rep = "答案是 %s" % task["answer"]
        else:
            rep = "推理: 由题设直接计算。\nFINAL: %s" % task["answer"]
        return rep

    src = REF_SRC[task["family"]]
    if not mutation:
        return "思路: 直接实现。\n```python\n%s\n```\n" % src
    if mutation == "extra":
        return "```python\n%s\nprint(0)\n```" % src
    if mutation == "loop":
        return "```python\nwhile True:\n    pass\n```"
    if mutation == "syntax":
        return "```python\ndef broken(:\n    pass\n```"
    if mutation == "nocode":
        return "这题我直接口述答案, 不给代码。"
    if mutation == "hardcode":
        pub = task["public"][0]["expected_stdout"] if task["public"] else "0"
        return "```python\nprint(%r)\n```" % pub
    raise SystemExit("未知 mutation: %s" % mutation)


# ---------------------------------------------------------------- 适配器

ROOT = os.path.dirname(os.path.dirname(HERE))
AGENT_BIN = os.environ.get("PROBE_AGENT_BIN",
                           os.path.join(ROOT, "src/agent.host/bin/Release/net10.0/linux-x64/native/agenthost"))
ENV_LOCAL = os.path.join(ROOT, ".env.local")


def load_env_local(path: str = ENV_LOCAL) -> dict:
    """读 .env.local 成 env dict (值不落盘/不打印; 只用于子进程环境)。"""
    env = dict(os.environ)
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def solve_agent(task: dict, solve_timeout: float):
    """真机自检: 用 AOT agenthost 跑一题 (一次性 prompt, 独立会话 Id 便于追溯)。"""
    if not os.path.exists(AGENT_BIN):
        raise SystemExit("agenthost 不存在: %s (先构建/发布或设 PROBE_AGENT_BIN)" % AGENT_BIN)
    env = load_env_local()
    env["AGENTFRAMEWORK_PY_RUN"] = "1"          # 打开 py 插件 (被测能力)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    sid = "probe-%s-%s" % (time.strftime("%m%d%H%M%S"), task["tid"])
    cmd = [AGENT_BIN, "-q", task["prompt"], "--output-mode", "text", "--session-id", sid]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=solve_timeout,
                           cwd=ROOT, env=env)
        return p.stdout, {"exit": p.returncode, "elapsed_s": round(time.time() - t0, 2),
                          "session": sid, "stderr_tail": (p.stderr or "")[-300:]}
    except subprocess.TimeoutExpired:
        return "", {"exit": -9, "elapsed_s": round(time.time() - t0, 2),
                    "session": sid, "stderr_tail": "solve timeout"}


def _resolve_rover_model() -> str:
    """前置资产检查 (缺则带候选清单秒退, 不进入重试/等待)。"""
    env = os.environ.get("AGENTFRAMEWORK_ROVER_MODEL")
    if env:
        if not os.path.exists(env):
            raise SystemExit("rover 模型不存在 (AGENTFRAMEWORK_ROVER_MODEL): %s" % env)
        return env
    default = "/tmp/models/prover7b-q4km.gguf"
    if os.path.exists(default):
        return default
    cands = sorted(glob.glob("/tmp/models/*.gguf")) if os.path.isdir("/tmp/models") else []
    raise SystemExit("rover 模型不存在: 默认 %s 已不可用 (清理/删除); 现有候选 %s ⇒ 显式设 "
                     "AGENTFRAMEWORK_ROVER_MODEL (不自动换模型, 换模型会改变被测对象)" % (default, cands or "无"))


def solve_rover(task: dict, solve_timeout: float) -> tuple:
    """真机自检: 用本机 agent.rover 引擎 (GGUF + 字节级 BPE + 采样 + 解码环) 跑一题。

    prompt 对等 (R401): 引擎内建 `--chat` 是硬编码 DeepSeek 版式, 对非 DeepSeek 族模型实测
    4/4 标签不在其词表 (eval/rover/r401/prompt-parity.json) ⇒ 默认走 PROBE_ROVER_PROMPT_MODE=template:
    模板取自目标 GGUF 自身 (jinja2 渲染) 并经 `--prompt` 原样送入, 引擎回报 prompt_sha256 做原样送达对账。
    需要复现旧行为 (引擎自带 chat 渲染) 时显式设 PROBE_ROVER_PROMPT_MODE=engine-chat。

    诚实边界: CPU 上每 token 需流式扫全模型, 实测 2.2 s/token (1.5B) ~ 25 s/token (7B) ⇒ meta 中
    budget_limited/max_tokens 明确标注, 避免把「预算截断」读成「能力为零」。
    """
    cli = os.environ.get("AGENTFRAMEWORK_ROVER_CLI", os.path.join(ROOT, "src/agent.rover/bin/Release/net10.0/agent.rover"))
    model = _resolve_rover_model()
    max_tokens = int(os.environ.get("PROBE_ROVER_MAX_TOKENS", "8"))
    temp = os.environ.get("PROBE_ROVER_TEMPERATURE", "0.7")
    seed = os.environ.get("PROBE_ROVER_SEED", "12345")
    mode = os.environ.get("PROBE_ROVER_PROMPT_MODE", "template")
    system = os.environ.get("PROBE_ROVER_SYSTEM", "你是严谨的编程与数学助手。请直接给出完整可运行的答案。")
    if not os.path.exists(cli):
        raise SystemExit("rover CLI 不存在: %s (先 dotnet build -c Release, 或设 AGENTFRAMEWORK_ROVER_CLI)" % cli)
    jdir = os.environ.get("PROBE_ROVER_JSON_DIR", DATA)
    os.makedirs(jdir, exist_ok=True)
    jf = os.path.join(jdir, "rover-gen-%s.json" % task["tid"])
    # 跑前清残留: 引擎崩溃时会话残留旧 json 会被误读成本轮答案 (实测踩过)
    if os.path.exists(jf):
        os.remove(jf)
    # 前置: 引擎是 apphost, 找不到共享运行时会 exit 131 (app-launch-failed) ——
    # 那是「臂不可用」, 不是「能力为零」。显式给 env, 不依赖调用方 shell 是否 export 过。
    env = dict(os.environ)
    dotnet_root = os.environ.get("DOTNET_ROOT") or os.path.expanduser("~/.dotnet")
    if os.path.isdir(dotnet_root):
        env["DOTNET_ROOT"] = dotnet_root
        env["PATH"] = dotnet_root + os.pathsep + env.get("PATH", "")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rover_prompt import render_prompt, attest_verbatim

    attest = {}
    if mode == "engine-chat":
        cmd = [cli, "generate", model, "--chat", "--system", system, "--prompt", task["prompt"]]
        attest = {"prompt_source": "engine-chat(硬编码版式)", "parity_risk": "非 DeepSeek 族模型 prompt 不对等"}
    else:
        text_in, attest = render_prompt(model, system, task["prompt"])
        attest["prompt_head"] = text_in[:64]      # 缺陷哨兵证据: 实际送入的首 64 字符
        cmd = [cli, "generate", model, "--prompt", text_in]
    cmd += ["--max-tokens", str(max_tokens), "--temperature", temp, "--seed", seed, "--json", jf]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=solve_timeout, cwd=ROOT, env=env)
    except subprocess.TimeoutExpired:
        return "", False, {"exit": -9, "elapsed_s": round(time.time() - t0, 2), "budget_limited": True,
                           "max_tokens": max_tokens, "prompt_mode": mode, "stderr_tail": "solve timeout", **attest}
    meta = {"exit": p.returncode, "elapsed_s": round(time.time() - t0, 2),
            "budget_limited": None, "max_tokens": max_tokens, "prompt_mode": mode,
            "model": os.path.basename(model), "stderr_tail": (p.stderr or "")[-300:], **attest}
    if p.returncode != 0 and not os.path.exists(jf):
        meta["arm_status"] = "unavailable"
        meta["arm_reason"] = ("app-launch-failed(missing-runtime)" if "app-launch-failed" in (p.stderr or "")
                              else "exit=%d" % p.returncode)
    text = ""
    if os.path.exists(jf):
        try:
            j = json.load(open(jf, encoding="utf-8"))
            text = j.get("text", "")
            meta.update({"steps": j.get("steps"), "ms_per_token": j.get("ms_per_token"),
                         "tokens_per_s": j.get("tokens_per_s"), "stop": j.get("stop"),
                         "prompt_tokens": j.get("prompt_tokens"), "ws_delta_bytes": j.get("ws_delta_bytes")})
            meta["budget_limited"] = (j.get("stop") == "max_tokens")
            if mode != "engine-chat":
                meta["prompt_attested"] = attest_verbatim(attest, j.get("prompt_sha256"))
        except Exception as e:  # noqa: BLE001
            meta["json_error"] = str(e)
    return text, False, meta


def solve(task: dict, solver: str, solve_timeout: float = 300.0) -> tuple:
    if solver == "oracle":
        return oracle_reply(task), True, {}
    if solver.startswith("mutation:"):
        return oracle_reply(task, solver.split(":", 1)[1]), True, {}
    if solver == "agent":
        rep, meta = solve_agent(task, solve_timeout)
        return rep, False, meta
    if solver == "rover":
        return solve_rover(task, solve_timeout)
    if solver.startswith("file:"):
        d = solver.split(":", 1)[1]
        p = os.path.join(d, "%s.txt" % task["tid"])
        return (open(p, encoding="utf-8").read() if os.path.exists(p) else ""), False, {}
    if solver.startswith("command:"):
        cmd = solver.split(":", 1)[1]
        t0 = time.time()
        p = subprocess.run(cmd, shell=True, input=task["prompt"], capture_output=True,
                           text=True, timeout=solve_timeout)
        return p.stdout, False, {"exit": p.returncode, "elapsed_s": round(time.time() - t0, 2)}
    raise SystemExit("未知 solver: %s" % solver)


def run(tasks_list, solver: str, timeout: float, solve_timeout: float = 300.0,
        limit: int = 0, tag: str = "") -> dict:
    per, tax_all, t0 = [], {}, time.time()
    if limit:
        tasks_list = tasks_list[:limit]
    rep_dir = os.path.join(DATA, "replies")
    os.makedirs(rep_dir, exist_ok=True)
    for t in tasks_list:
        reply, is_oracle, smeta = solve(t, solver, solve_timeout)
        safe = solver.replace(":", "_").replace("/", "_")
        rp = os.path.join(rep_dir, "%s%s-%s.txt" % (safe, tag, t["tid"]))
        with open(rp, "w", encoding="utf-8") as fh:      # 原始回复留档 (诊断/审计)
            fh.write(reply or "")
        smeta["reply_path"] = os.path.relpath(rp, ROOT)
        if not (reply or "").strip():
            smeta["reply_head"] = ""
        if smeta.get("arm_status") == "unavailable":
            tax_all["arm_unavailable"] = tax_all.get("arm_unavailable", 0) + 1
            per.append({"tid": t["tid"], "kind": t["kind"], "family": t["family"],
                        "mode": "arm_unavailable", "passed": 0, "total": 0,
                        "taxonomy": {"arm_unavailable": 1}, "reply_chars": 0, "reply_head": "",
                        "solve": smeta})
            print("  %-6s %-8s ARM-UNAVAILABLE (%s) — 不计分母, 不判能力" % (t["tid"], t["kind"], smeta.get("arm_reason")),
                  flush=True)
            continue
        r = grade.grade(t, reply, timeout)
        for k, v in r["taxonomy"].items():
            tax_all[k] = tax_all.get(k, 0) + v
        per.append({"tid": t["tid"], "kind": t["kind"], "family": t["family"],
                    "mode": r["mode"], "passed": r["passed"], "total": r["total"],
                    "taxonomy": r["taxonomy"], "reply_chars": len(reply or ""),
                    "reply_head": (reply or "")[:300].replace("\n", "\u23ce"),
                    "solve": smeta})
        print("  %-6s %-8s %-24s %-14s %d/%d  (%s)" % (t["tid"], t["kind"], t["family"],
                                                       r["mode"], r["passed"], r["total"],
                                                       "%.0fs" % smeta["elapsed_s"] if smeta.get("elapsed_s") else "instant"),
              flush=True)

    def agg(key):
        buckets = {}
        for p in per:
            b = buckets.setdefault(p[key], {"n": 0, "passed": 0, "total": 0, "modes": {}})
            b["n"] += 1; b["passed"] += p["passed"]; b["total"] += p["total"]
            b["modes"][p["mode"]] = b["modes"].get(p["mode"], 0) + 1
        for b in buckets.values():
            b["rate"] = round(b["passed"] / b["total"], 4) if b["total"] else 0.0
        return buckets

    return {
        "solver": solver,
        "oracle": solver == "oracle",
        "solver_id": _solver_id(solver),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_s": round(time.time() - t0, 2),
        "n_tasks": len(per),
        "passed": sum(p["passed"] for p in per),
        "total": sum(p["total"] for p in per),
        "rate": (None if per and all(p["mode"] == "arm_unavailable" for p in per)
                 else round(sum(p["passed"] for p in per) / max(1, sum(p["total"] for p in per)), 4)),
        "arm_unavailable": sum(1 for p in per if p["mode"] == "arm_unavailable"),
        "validity": ("arm-unavailable" if any(p["mode"] == "arm_unavailable" for p in per) else "ok"),
        "taxonomy": tax_all,
        "by_kind": agg("kind"),
        "by_family": agg("family"),
        "per_task": per,
    }


def _canon_sha(raw):
    """题集规范哈希: 与生成/复用无关, 同一批题必得同一 sha (对比可追溯的前提)。"""
    return hashlib.sha256("\n".join(json.dumps(t, sort_keys=True, ensure_ascii=False) for t in raw)
                          .encode()).hexdigest()[:16]


def _pools(kind, only):
    """族池: 程序族 / (数学族 ∪ 见证型族)。only=逗号白名单(定向覆盖)。

    见证型族若不入池 ⇒ 生成了也永不抽样(死代码), 故此处必须并集。
    """
    want = [x.strip() for x in (only or "").split(",") if x.strip()]
    prog = [f for f in sorted(taskgen.PROGRAM_FAMILIES) if not want or f in want]
    mathl = [f for f in sorted(taskgen.MATH_FAMILIES) + sorted(taskgen.WITNESS_FAMILIES)
             if not want or f in want]
    if want and not prog and not mathl:
        raise SystemExit("--families 无匹配族: %s" % only)
    return (prog if kind in ("program", "both") else []), (mathl if kind in ("math", "both") else [])


def _solver_id(solver: str) -> str:
    if solver.startswith("command:"):
        return "cmd:" + hashlib.sha256(solver.encode()).hexdigest()[:12]
    return solver


# ---------------------------------------------------------------- 自检

def selftest() -> int:
    ok, fails = 0, []

    def chk(name, cond, detail=""):
        nonlocal ok
        if cond:
            ok += 1
            print("  [PASS] %s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %s %s" % (name, detail))

    print("selftest: 流水线正控 + 缺陷注入负控")
    rnd = random.Random(4242)
    prog = [json.loads(taskgen.gen_program_task(i, sorted(taskgen.PROGRAM_FAMILIES), rnd).to_json())
            for i in range(1, 4)]
    math_ = [json.loads(taskgen.gen_math_task(i, sorted(taskgen.MATH_FAMILIES), rnd).to_json())
             for i in range(1, 3)]
    allt = prog + math_

    # 反死代码: 见证型族必须真的可达 (曾因池子只取 MATH_FAMILIES 而永不抽样)
    _prog_pool, _math_pool = _pools("both", "")
    chk("见证型族在数学池内(非死代码)",
        bool(taskgen.WITNESS_FAMILIES) and all(f in _math_pool for f in taskgen.WITNESS_FAMILIES),
        "witness=%s" % sorted(taskgen.WITNESS_FAMILIES))
    _wp = _pools("math", ",".join(sorted(taskgen.WITNESS_FAMILIES)))
    chk("--families 白名单可定向且不混入程序族",
        _wp[0] == [] and sorted(_wp[1]) == sorted(taskgen.WITNESS_FAMILIES))
    wit = [json.loads(taskgen.gen_math_task(i, sorted(taskgen.WITNESS_FAMILIES), rnd).to_json())
           for i in range(1, 3)]
    chk("见证型题 meta.witness 就位且 answer 非空(仅供 oracle 正控)",
        all(w["meta"].get("witness") and (w["answer"] or "").strip() for w in wit))
    rw = run(wit, "oracle", 5.0)
    chk("正控: 见证型题 oracle 满分", rw["rate"] == 1.0, "rate=%.4f tax=%s" % (rw["rate"], rw["taxonomy"]))
    rw2 = run(wit, "mutation:wrongfinal", 5.0)
    chk("负控: 见证型题错见证被判红", rw2["rate"] < 1.0 and bool(rw2["taxonomy"].get("wrong_witness")),
        "rate=%.4f tax=%s" % (rw2["rate"], rw2["taxonomy"]))

    chk("oracle 参考解覆盖全部程序族(反覆盖缺口)",
        all(f in REF_SRC for f in sorted(taskgen.PROGRAM_FAMILIES)),
        "缺: %s" % [f for f in sorted(taskgen.PROGRAM_FAMILIES) if f not in REF_SRC])
    chk("规范题集哈希与复用路径一致",
        _canon_sha(allt) == _canon_sha(json.loads(json.dumps(allt))))

    r = run(allt, "oracle", 5.0)
    chk("正控: oracle 满分", r["rate"] == 1.0, "rate=%.4f tax=%s" % (r["rate"], r["taxonomy"]))

    for mut, expect_tax in (("extra", "wrong_output"), ("loop", "timeout"), ("syntax", "syntax_error"),
                            ("nocode", "no_code"), ("hardcode", "wrong_output")):
        rm = run(prog, "mutation:%s" % mut, 1.0 if mut == "loop" else 5.0)
        chk("负控: 程序题 %s 被判红" % mut,
            rm["rate"] < 1.0 and expect_tax in rm["taxonomy"],
            "rate=%.4f tax=%s" % (rm["rate"], rm["taxonomy"]))

    rm = run(math_, "mutation:wrongfinal", 5.0)
    chk("负控: 数学错答被判红", rm["rate"] == 0.0 and "wrong_final" in rm["taxonomy"], str(rm["taxonomy"]))
    rm = run(math_, "mutation:nofinal", 5.0)
    chk("负控: 数学无 FINAL 被判红", rm["rate"] == 0.0 and "no_final" in rm["taxonomy"], str(rm["taxonomy"]))

    r = run(prog[:1], "file:/nonexistent-dir-xyz", 5.0)
    chk("负控: 缺失回复判 no_code", r["rate"] == 0.0, str(r["taxonomy"]))

    r = run(prog[:1], "command:cat", 5.0)
    chk("适配器: command 通道可用(prompt 原样回灌 ⇒ 应判红)", r["rate"] == 0.0,
        "rate=%.4f" % r["rate"])

    r = run(allt, "oracle", 5.0)
    chk("可复现: 同输入同结果", r["rate"] == 1.0)

    print("selftest %d/%d" % (ok, ok + len(fails)))
    return 0 if not fails else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["program", "math", "both"], default="both")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--solver", default="oracle")
    ap.add_argument("--timeout", type=float, default=5.0)          # 候选程序执行超时
    ap.add_argument("--solve-timeout", type=float, default=300.0)  # 单题解法(LLM)超时
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag", default="")            # 回复留档后缀, 便于区分多轮探针
    ap.add_argument("--tasks", default="")     # 复用已生成题集 (保证题集哈希可追溯)
    ap.add_argument("--families", default="")  # 定向覆盖: 逗号分隔族白名单(含见证型族)
    ap.add_argument("--dump-tasks", default="", dest="dump_tasks")  # 落盘题集供多解法同批对比
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    if a.tasks:
        raw = json.load(open(a.tasks, encoding="utf-8"))
        sha = _canon_sha(raw)
    else:
        rnd = random.Random(a.seed)
        raw = []
        prog_pool, math_pool = _pools(a.kind, a.families)
        for i in range(1, a.n + 1):
            if prog_pool:
                raw.append(json.loads(taskgen.gen_program_task(i, prog_pool, rnd).to_json()))
        for i in range(1, a.n + 1):
            if math_pool:
                raw.append(json.loads(taskgen.gen_math_task(i, math_pool, rnd).to_json()))
        if a.dump_tasks:
            os.makedirs(os.path.dirname(a.dump_tasks) or ".", exist_ok=True)
            with open(a.dump_tasks, "w", encoding="utf-8") as fh:
                json.dump(raw, fh, ensure_ascii=False, indent=1)
            print("题集已落盘: %s" % a.dump_tasks)
        sha = _canon_sha(raw)

    print("题集: %d 题 (kind=%s seed=%s) sha=%s" % (len(raw), a.kind, a.seed, sha))
    print("解法: %s" % a.solver)
    summary = run(raw, a.solver, a.timeout, a.solve_timeout, a.limit, a.tag)
    summary["taskset_sha"] = sha
    summary["kind_arg"] = a.kind
    summary["seed"] = a.seed

    out = a.out or os.path.join(DATA, "probe-%s-seed%s.json" % (_solver_id(a.solver).replace("/", "_"), a.seed))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print("→ %s" % out)
    print("通过率: %d/%d = %.4f  (%.2fs)" % (summary["passed"], summary["total"], summary["rate"], summary["elapsed_s"]))
    print("失败模式: %s" % json.dumps(summary["taxonomy"], ensure_ascii=False))
    print("按族: %s" % json.dumps({k: v["rate"] for k, v in summary["by_family"].items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
