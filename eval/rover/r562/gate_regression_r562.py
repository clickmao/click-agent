#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R562 · 起手闸「联合回归」驱动器 (复用既有闸/既有控制, 零新夹具).

被测器具: `eval/rover/r483/preflight_gate.py` (R483 起手闸; 三态 rc 0 PASS / 2 GATE_BLOCKED / 3 MISS)
本轮回归面 (与 R557 同形, 逐条声明):
  · mem 面成对控制: 默认门槛 (PASS) vs `--nc-block` (门槛抬到不可达 ⇒ 须 rc=2)
  · shell 自匹配面成对控制: 同环境只翻 `--nc-selfmatch` —— 前提由**无害诱饵 shell** 实现
    (argv0=bash, cmdline 含监视字串; 诱饵只 sleep, 不占 CPU/不写盘) ⇒ 修后 (跳过 shell 包装) PASS ∧ 修前 GATE_BLOCKED
  · 多因并列: `--nc-both` (mem 不可达 ∧ shell 不排除) ⇒ 须**并列**报 ≥2 条因 (禁二选一)
诱饵由本驱动器 Popen 起、finally 按 pid 杀 (禁 `pkill -f` 自杀死法);
用法: python3 eval/rover/r562/gate_regression_r562.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
GATE = os.path.join(REPO, "eval/rover/r483/preflight_gate.py")
OUT = os.path.join(REPO, "eval/rover/r562")
DECOY_WORD = "llama-server"


def run_gate(tag, extra):
    p = os.path.join(OUT, "gate-%s.json" % tag)
    env = dict(os.environ, DOTNET_ROOT=os.path.expanduser("~/.dotnet"))
    env["PATH"] = env["DOTNET_ROOT"] + ":" + env.get("PATH", "")
    r = subprocess.run([sys.executable, GATE, "--round", "r562", "--out", p] + extra,
                       capture_output=True, text=True, cwd=REPO, env=env, timeout=300)
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"tag": tag, "rc": r.returncode, "error": "%s: %s" % (type(e).__name__, e)}
    return {"tag": tag, "rc": r.returncode, "verdict": d["verdict"], "mem_mb": d["mem_available_mb"],
            "gate_mb": d["gate_mb"], "shells_skipped_n": d["shells_skipped_n"],
            "legacy_self_only": d["legacy_self_only"], "blocker_causes": d["blocker_causes"],
            "blocker_watch": [b["watch"] for b in d["blockers"]],
            "own_tool_reaped": len(d.get("own_tool_reap", {}).get("reaped", []) or []),
            "out": p}


def main():
    os.makedirs(OUT, exist_ok=True)
    # 前置: 无并发重负载写者 (共享机闸红先查残留)
    ps = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    busy = [l for l in ps.splitlines() if ("dotnet" in l or "codex" in l) and "ps -eo" not in l]
    rec = {"round": "R562", "instrument": "gate_regression_r562.py",
           "gate": GATE, "precondition_busy": busy, "runs": []}
    if busy:
        rec["rc"] = 3
        rec["note"] = "fail-closed: 检出并发重负载进程, 拒跑"
        json.dump(rec, open(os.path.join(OUT, "gate-regression-r562.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(json.dumps({"rc": 3, "busy": busy[:3]}, ensure_ascii=False))
        return 3
    # ① mem 面成对控制 (无诱饵)
    rec["runs"].append(run_gate("pc", []))
    rec["runs"].append(run_gate("nc-block", ["--nc-block"]))
    # ② shell 自匹配面成对控制 (诱饵在场: argv0=bash ∧ cmdline 含监视字串)
    decoy = subprocess.Popen(["bash", "-c", "while true; do sleep 1; done", DECOY_WORD],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # 前提成对断言: 诱饵进程 **argv0=bash ∧ cmdline 含监视字串** (禁 `bash -c 'sleep 200' word` 形态:
        # bash 会 exec 替换自身 ⇒ 字面量随 -c 串一起消失, 前提静默不成立 —— R562 首跑即此因被抓)
        import time
        time.sleep(0.6)
        raw = open("/proc/%d/cmdline" % decoy.pid, "rb").read().decode("utf-8", "replace")
        argv0 = os.path.basename(raw.split("\x00")[0].strip())
        premise = {"pid": decoy.pid, "argv0": argv0, "cmd_has_word": DECOY_WORD in raw.replace("\x00", " "),
                   "alive": decoy.poll() is None}
        rec["decoy"] = premise
        if not (premise["argv0"] in ("bash", "sh", "dash", "zsh") and premise["cmd_has_word"] and premise["alive"]):
            raise RuntimeError("decoy premise not realized: %s" % premise)
        rec["runs"].append(run_gate("decoy-fixon", []))
        rec["runs"].append(run_gate("decoy-legacy", ["--nc-selfmatch"]))
        rec["runs"].append(run_gate("decoy-both", ["--nc-both"]))
    finally:
        decoy.terminate()
        try:
            decoy.wait(timeout=10)
        except Exception:  # noqa: BLE001
            decoy.kill()
    rec["decoy"]["reaped"] = decoy.poll() is not None
    # 期望 (fail-closed 断言): 机检——不合预期即 rc=2, 不改写读数
    exp = {"pc": (0, "PASS"), "nc-block": (2, "GATE_BLOCKED"), "decoy-fixon": (0, "PASS"),
           "decoy-legacy": (2, "GATE_BLOCKED"), "decoy-both": (2, "GATE_BLOCKED")}
    bad = []
    for r in rec["runs"]:
        if "verdict" not in r:
            bad.append((r["tag"], "missing_verdict", r.get("error")))
            continue
        e_rc, e_v = exp[r["tag"]]
        if r["rc"] != e_rc or r["verdict"] != e_v:
            bad.append((r["tag"], "rc/verdict", "%s/%s != %s/%s" % (r["rc"], r["verdict"], e_rc, e_v)))
        if r["tag"] == "decoy-fixon" and r["shells_skipped_n"] < 1:
            bad.append((r["tag"], "premise", "诱饵未被计数 (shells_skipped_n=%d)" % r["shells_skipped_n"]))
    both = [r for r in rec["runs"] if r["tag"] == "decoy-both"][0]
    if len(both.get("blocker_causes", [])) < 2:
        bad.append(("decoy-both", "multi_cause", "多因未并列: %s" % both.get("blocker_causes")))
    rec["expectations_violated"] = bad
    rec["rc"] = 2 if bad else 0
    json.dump(rec, open(os.path.join(OUT, "gate-regression-r562.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rec["rc"], "violated": bad,
                      "runs": [{k: v for k, v in r.items() if k != "out"} for r in rec["runs"]],
                      "decoy": rec["decoy"]}, ensure_ascii=False))
    return rec["rc"]


if __name__ == "__main__":
    sys.exit(main())
