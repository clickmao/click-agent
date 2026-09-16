#!/usr/bin/env python3
"""R505 判分器改版: 快照重判（不重跑 LLM）+ 影响面机检 + 预注册留痕。

被测对象与判分器分离 ⇒ 器具改版只需**重判仓内不可变快照**; 但必须机检「改版只动了应该动的判据」。
用法: python3 eval/rover/r505/rejudge_r505.py --tag v3 [--prev v2]
rc: 0 重判+影响面+留痕齐备; 1 影响面超预期（旧读数作废）; 3 缺产物
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
EV = os.path.join(HERE, "evidence")
PRE = os.path.join(HERE, "prereg_r505.json")
PY = sys.executable
FROZEN = ["H1", "H2", "H3", "H4", "H5", "H6", "H9", "H10", "H11"]
WATCH = {"judge_py": os.path.join(HERE, "judge_contrast_r505.py"),
         "attr_py": os.path.join(HERE, "attr_calls_r505.py")}


def load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def resolve_probe(b, side):
    """探针产物名不是猜出来的：按 glob 解析（`probe-<solver>-seed<n>-<tag>.json`），解析不到 ⇒ None。"""
    hits = sorted(glob.glob(os.path.join(REPO, "data/probe", "probe-*-%s-r505%s*.json" % (side, b))))
    return hits[-1] if hits else None


def judge_cmd(b):
    d = os.path.join(EV, b)
    cj, aj = resolve_probe(b, "codex"), resolve_probe(b, "agent")
    return [PY, os.path.join(HERE, "judge_contrast_r505.py"), "--batch", b,
            "--codex", cj, "--agent", aj,
            "--prereg", PRE,
            "--adapter-codex-dir", os.path.join(d, "adapter-codex"),
            "--adapter-agent-dir", os.path.join(d, "adapter-agent"),
            "--manifest-codex", os.path.join(d, "adapter-codex", "manifest-codex.json"),
            "--manifest-agent", os.path.join(d, "adapter-agent", "manifest-agent.json"),
            "--codex-raw-dir", os.path.join(d, "codex", "raw"),
            "--codex-audit", os.path.join(d, "codex", "codex-audit.jsonl"),
            "--out", os.path.join(d, "verdict-r505%s.json" % b)], (cj, aj)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v3")
    ap.add_argument("--prev", default="v2")
    ap.add_argument("--batches", nargs="+", default=["a", "b", "c"])
    a = ap.parse_args()

    impacts, allok = {}, True
    for b in a.batches:
        d = os.path.join(EV, b)
        cur = os.path.join(d, "verdict-r505%s.json" % b)
        if not os.path.exists(cur):
            print("[致命] 批 %s 缺判据产物 ⇒ rc=3" % b)
            return 3
        prev = os.path.join(d, "verdict-r505%s-judge%s.json" % (b, a.prev))
        if not os.path.exists(prev):
            with open(cur, "rb") as fi, open(prev, "wb") as fo:
                fo.write(fi.read())
        v1 = load(prev)
        cmd, probes = judge_cmd(b)
        if not all(probes):
            print("[致命] 批 %s 探针产物解析失败: codex=%s agent=%s ⇒ rc=3（禁拿旧 verdict 冒充新读数）"
                  % (b, probes[0], probes[1]))
            return 3
        # 判分器是确定性纯函数 ⇒ 产出可与旧件逐字节相同; 因此**不用**内容变化判新鲜度,
        # 而是让本次判分写到独立临时件, 并要求判分自报完成标记 ⇒ 证明这次真的执行了。
        tmp = os.path.join("/tmp", "r505-rejudge-%s-%s.json" % (b, a.tag))
        if os.path.exists(tmp):
            os.remove(tmp)
        cmd[cmd.index("--out") + 1] = tmp
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = (r.stdout or "")
        if (not os.path.exists(tmp)) or ("verdict ->" not in out):
            print("[致命] 批 %s 判分未真正产出（rc=%d）⇒ rc=3\n%s"
                  % (b, r.returncode, out.strip().splitlines()[-3:]))
            return 3
        with open(cur, "wb") as fo, open(tmp, "rb") as fi:
            fo.write(fi.read())
        v2 = load(cur)
        c1 = {c["id"]: bool(c.get("pass")) for c in v1["criteria"]}
        c2 = {c["id"]: bool(c.get("pass")) for c in v2["criteria"]}
        chk = {k: {"prev": c1.get(k), "new": c2.get(k)} for k in sorted(set(c1) | set(c2))}
        frozen_ok = all(chk.get(k, {}).get("prev") == chk.get(k, {}).get("new") for k in FROZEN)
        imp = {"batch": b, "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "prev": {"path": os.path.relpath(prev, REPO), "rc": v1["rc"], "sha256": sha(prev)},
               "new": {"path": os.path.relpath(cur, REPO), "rc": v2["rc"], "sha256": sha(cur)},
               "criteria": chk, "frozen_criteria_unchanged": frozen_ok,
               "totals_unchanged": v1["totals"] == v2["totals"],
               "table_unchanged": v1["table"] == v2["table"],
               "judge_tail": (r.stdout or "").strip().splitlines()[-4:]}
        outp = os.path.join(d, "judge-amendment-%s-to-%s-impact.json" % (a.prev, a.tag))
        with open(outp, "w", encoding="utf-8") as fh:
            json.dump(imp, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        impacts[b] = imp
        ok = frozen_ok and imp["totals_unchanged"] and imp["table_unchanged"]
        allok = allok and ok
        print("批 %s: rc %s→%s | 冻结判据不变=%s | 用量不变=%s | 质量表不变=%s | H8 %s→%s" % (
            b, v1["rc"], v2["rc"], frozen_ok, imp["totals_unchanged"], imp["table_unchanged"],
            chk.get("H8", {}).get("prev"), chk.get("H8", {}).get("new")))
    if not allok:
        print("[致命] 改版影响面超预期 ⇒ 旧读数作废, 必须重跑 (rc=1)")
        return 1

    pre = load(PRE)
    old = {k: pre["files_sha256"].get(k) for k in WATCH}
    new = {k: sha(p) for k, p in WATCH.items()}
    pre["files_sha256"].update(new)
    pre.setdefault("amendments", []).append({
        "round": "R505", "kind": "instrument_revision",
        "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "判分/归因器 %s（新增: 标记剥离 [微步骤隔离问询] + 题面片段命中）" % a.tag,
        "files": {k: {"old": old[k], "new": new[k]} for k in WATCH},
        "impact_checks": {b: os.path.relpath(os.path.join(EV, b,
                            "judge-amendment-%s-to-%s-impact.json" % (a.prev, a.tag)), REPO)
                          for b in a.batches},
        "evidence_reuse": "三批复用同一快照重判（LLM 流量未变; 影响面机检: 冻结判据/用量/质量表逐位不变）",
    })
    with open(PRE, "w", encoding="utf-8") as fh:
        json.dump(pre, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("预注册留痕已追加 (%s)" % a.tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())