#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 预注册 (机取数字必机检; 被证伪的宣称须收窄并单列)。

自检 fail-closed: 题集 sha / 每题隐藏用例数(由用例脚本反解) / 参考解 oracle 全过 / NC 证据在位。
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
TASKSET = os.path.join(HERE, "taskset-r508.json")
CASE_DEF = re.compile(r"^def (c_[a-z0-9_]+)\(", re.M)


def sha8(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def count_cases(path):
    src = open(path, encoding="utf-8").read()
    return sorted(set(CASE_DEF.findall(src)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "prereg-r508.json"))
    ap.add_argument("--skip-oracle", action="store_true")
    a = ap.parse_args()
    ts = json.load(open(TASKSET, encoding="utf-8"))
    checks, tasks = [], []
    for t in ts["tasks"]:
        cp = os.path.join(HERE, t["cases"])
        names = count_cases(cp)
        checks.append(["用例脚本存在:%s" % t["tid"], os.path.exists(cp)])
        checks.append(["隐藏用例数>0:%s" % t["tid"], len(names) > 0])
        checks.append(["声明题量==反解题量:%s" % t["tid"], len(names) == int(t["hidden_cases"])])
        if not a.skip_oracle:
            ev = os.path.join(HERE, "evidence", "prereg-oracle-%s.json" % t["tid"])
            subprocess.run([sys.executable, os.path.join(HERE, "proj_grade.py"), "--task", t["tid"],
                            "--oracle", "--isolate", "--json", ev],
                           capture_output=True, text=True, timeout=420)
            try:
                g = json.load(open(ev, encoding="utf-8"))
            except Exception:
                g = {}
            checks.append(["参考解 oracle 全过:%s" % t["tid"], bool(g.get("all_pass"))])
        tasks.append({"tid": t["tid"], "family": t["family"], "entry": t["entry"],
                      "hidden_cases": names, "n_hidden": len(names),
                      "prompt_sha8": hashlib.sha256(t["prompt"].encode("utf-8")).hexdigest()[:12]})
    checks.append(["NC 自检证据在位(判别力)", os.path.exists(os.path.join(HERE, "evidence", "nc-selftest.json"))])
    nc_ok = False
    try:
        nc = json.load(open(os.path.join(HERE, "evidence", "nc-selftest.json"), encoding="utf-8"))
        nc_ok = (nc.get("verdict") == "SELFTEST=OK")
    except Exception:
        pass
    checks.append(["NC verdict=SELFTEST=OK", nc_ok])
    ok = all(c[1] for c in checks)
    rec = {
        "round": "R508", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "kind": "项目级对照(规模更大): 多步/多文件/需自测",
        "taskset": os.path.relpath(TASKSET, "/home/agentuser/AgentFramework"),
        "taskset_sha8": sha8(TASKSET),
        "arms": [{"tag": "A", "side": "agent", "desc": "本侧默认 (ActionLoop 默认 6 步)"},
                 {"tag": "B", "side": "agent", "desc": "本侧单变量: AGENTFRAMEWORK_ACTION_MAX_STEPS=24"},
                 {"tag": "C", "side": "codex", "desc": "codex-cli 外部真值 (codex exec --json)"}],
        "tasks": tasks,
        "model": "deepseek-flash (adapter MAP_MODEL → deepseek-chat, 两侧同上游)",
        "criteria": {
            "H0_可验收前置": "两侧产物独立物化 + python3 -I -B 实跑 + 逐条隐藏用例机械判对; 全题全对才算可验收",
            "H1_仪器判别力": "参考解 oracle 全过(正控) + 7 个指名缺陷全被抓(负控)",
            "H2_外部真值": "codex exec --json (自带循环/沙箱), 非模型裁判",
            "H3_同输入": "两侧逐字同 prompt (taskset sha8=%s)" % sha8(TASKSET),
            "H4_同模型": "adapter 落盘 request.upstream_request.model 两侧取值集合须唯一",
            "H5_对照分列": "token/调用/墙钟 只按题分列, 禁按总量断言优劣",
            "主读数": "整题全对(题) / 逐题用例通过数 / prompt+total tokens / 调用数 / 墙钟 / 产物件数",
        },
        "budget": {"per_arm_total_tokens_cap": 600000, "per_task_wall_s": 900, "run_wall_s_cap": 3600},
        "excluded": ["n=2 题, 小样本, 不作统计显著性宣称", "两侧静态面不同源(本侧 AOT host vs codex 自带循环)",
                     "本侧 data/ 会话态与 codex 沙箱内存态不可比", "单轮读数, 跨轮禁相减"],
        "checks_selfvalidation": checks,
        "verdict": "PREREG_OK" if ok else "PREREG_FAIL",
    }
    if a.write:
        json.dump(rec, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for n, v in checks:
        print("%-34s %s" % (n, "OK" if v else "FAIL"))
    print("verdict=%s taskset_sha8=%s" % (rec["verdict"], rec["taskset_sha8"]))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
