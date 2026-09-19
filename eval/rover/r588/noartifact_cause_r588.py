#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R588 · 候选③ + 候选⑤（只读，零产品改动 / 零新夹具 / 零远端）

候选③: 「臂级未交付产物」(`rc=4`) 的定因 —— 只读回放该跑次 reply/transcript,
        定位「计划未落盘」的**谓词落点**并把两侧解析位置做**逐字节对齐**。
候选⑤: 该类窗在**配对分母**里的口径 —— 显式两栏（计入 0/58 ∧ 单列点名），禁静默剔除。

机械判据（无人工口径）:
  1. 普查所有已冻结跑次目录: work 文件数 / reply 字节 / transcript 的 rc·stage·steps
     ⇒ 分类 {OK_RC0, CONTRACT_REJECT, EXHAUSTED, SELFTEST_UNMET, NO_ARTIFACT}。
  2. 对 NO_ARTIFACT 跑次: 从其 reply 里取契约块（`{"schema_version"` 起），用**独立解析器**
     (stdlib json) 解析，记录失败类与**字符位**; 与 transcript 的 `reason` 里
     `BytePositionInLine: N` 比对 ⇒ `byte_alignment_delta`（0 = 两侧同一文本同一位置）。
  3. 两侧成对控制(有牙):
       正控 = 取一份 rc=0 跑次的契约块, 独立解析器**必须** OK（证提取器/解析器非恒红）;
       负控 = 对同一份正控块注入一处结构破坏（删一个 `}`）**必须**解析失败。
     两向都过才 `has_teeth=true`; 任一向不过 ⇒ 器具缺陷, 不入被测结论。

用法: python3 eval/rover/r588/noartifact_cause_r588.py [--out <path>]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re

REPO = "/home/agentuser/AgentFramework"
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
ROUNDS = ("r585", "r586", "r587", "r588")


def contract_span(txt: str):
    """契约块 = 从 `{"schema_version"` 起的第一段**平衡** `{...}`。

    首跑口径过贪（一直取到 reply 末尾）⇒ rc=0 正控读成 `Extra data`（器具缺陷）。
    修法: 括号深度扫描（尊重 JSON 字符串与转义）切出平衡段;
    **扫不平衡** ⇒ 说明该块自身结构不闭合（这正是被查形态）⇒ 保留余文并置 `balanced=false`。
    """
    i = txt.find('{"schema_version"')
    if i < 0:
        return (False, -1, "")
    depth, instr, esc, j = 0, False, False, i
    while j < len(txt):
        c = txt[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
        else:
            if c == '"':
                instr = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return (True, i, txt[i:j + 1])
        j += 1
    return (False, i, txt[i:])


def classify(rc, stage, work_files, reply_bytes):
    if work_files == 0 and reply_bytes > 0:
        return "NO_ARTIFACT"
    if rc == 0:
        return "OK_RC0"
    if rc == 4 and stage == "contract":
        return "CONTRACT_REJECT"
    if rc == 5:
        return "EXHAUSTED"
    if rc == 8:
        return "SELFTEST_UNMET"
    return "OTHER"


def census(rounds=ROUNDS):
    rows = []
    for rk in rounds:
        base = os.path.join(RUNS, rk)
        if not os.path.isdir(base):
            continue
        for win in sorted(d for d in os.listdir(base) if re.fullmatch(r"w\d+", d)):
            wd = os.path.join(base, win)
            for sub in sorted(os.listdir(wd)):
                g1 = os.path.join(wd, sub, "g1")
                if not os.path.isdir(g1) or sub == "codex":
                    continue
                work = os.path.join(g1, "work")
                nf = sum(len(f) for _, _, f in os.walk(work)) if os.path.isdir(work) else 0
                rep = os.path.join(g1, "reply.txt")
                rb = os.path.getsize(rep) if os.path.isfile(rep) else 0
                d = {}
                tr = os.path.join(g1, "transcript.json")
                if os.path.isfile(tr):
                    try:
                        d = json.load(io.open(tr, encoding="utf-8"))
                    except Exception as e:  # noqa: BLE001
                        d = {"_err": str(e)[:60]}
                cls = classify(d.get("rc"), d.get("stage"), nf, rb)
                rows.append({"round": rk, "win": win, "sub": sub, "work_files": nf,
                             "reply_bytes": rb, "rc": d.get("rc"), "stage": d.get("stage"),
                             "steps": d.get("steps_executed"), "reason": (d.get("reason") or "")[:200],
                             "class": cls, "g1": g1})
    return rows


def replay(path_reply, reason):
    txt = io.open(path_reply, encoding="utf-8", errors="replace").read()
    balanced, off, blk = contract_span(txt)
    out = {"contract_start_char": off, "block_chars": len(blk), "balanced": balanced}
    if off < 0:
        out["parse"] = "NO_CONTRACT_BLOCK"
        return out
    try:
        json.loads(blk)
        out["parse"] = "OK"
    except Exception as e:  # noqa: BLE001
        out["parse"] = "FAIL"
        out["err"] = str(e)[:140]
        m = re.search(r"char (\d+)", str(e))
        if m:
            ch = int(m.group(1))
            out["fail_char"] = ch
            out["fail_byte"] = len(blk[:ch].encode())
    m2 = re.search(r"BytePositionInLine:\s*(\d+)", reason or "")
    if m2:
        out["reported_byte_by_product"] = int(m2.group(1))
        if out.get("fail_byte") is not None:
            out["byte_alignment_delta"] = out["fail_byte"] - out["reported_byte_by_product"]
        m3 = re.search(r"'(.{1,3})' is an invalid start of a property name", reason or "")
        if m3:
            out["product_reported_at"] = m3.group(1)
            if out.get("fail_char") is not None:
                out["char_at_fail"] = blk[out["fail_char"]:out["fail_char"] + 1]
    return out


def controls(rows):
    """两侧成对控制: 正控(rc=0 跑次的契约块必须可解析) + 负控(注入破坏必须失败)。"""
    ctl = {"positive": None, "negative": None, "fails": []}
    ok_rows = [r for r in rows if r["class"] == "OK_RC0"]
    if not ok_rows:
        ctl["fails"].append("无 rc=0 跑次可作正控")
        return ctl
    r = ok_rows[0]
    txt = io.open(os.path.join(r["g1"], "reply.txt"), encoding="utf-8", errors="replace").read()
    balanced, off, blk = contract_span(txt)
    try:
        json.loads(blk)
        ctl["positive"] = {"run": "%s/%s/%s" % (r["round"], r["win"], r["sub"]), "parse": "OK",
                           "balanced": balanced, "block_chars": len(blk)}
    except Exception as e:  # noqa: BLE001
        ctl["positive"] = {"run": "%s/%s/%s" % (r["round"], r["win"], r["sub"]), "parse": "FAIL",
                           "balanced": balanced, "err": str(e)[:100]}
        ctl["fails"].append("正控: rc=0 契约块不可解析 ⇒ 提取器/解析器口径与产品不一致")
    # 负控: 删除最后一个 '}' 之前的任一 '}'（结构破坏）
    k = blk.rfind("}")
    if k > 0:
        broken = blk[:k] + " " + blk[k + 1:]
        try:
            json.loads(broken)
            ctl["negative"] = {"mutation": "delete one '}'", "parse": "OK"}
            ctl["fails"].append("负控: 注入结构破坏仍未报错 ⇒ 解析器无牙")
        except Exception as e:  # noqa: BLE001
            ctl["negative"] = {"mutation": "delete one '}'", "parse": "FAIL", "err": str(e)[:100]}
    return ctl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r588/noartifact-cause-r588.json"))
    a = ap.parse_args()
    rows = census()
    noart = [r for r in rows if r["class"] == "NO_ARTIFACT"]
    replays = {}
    for r in noart:
        replays["%s/%s/%s" % (r["round"], r["win"], r["sub"])] = replay(
            os.path.join(r["g1"], "reply.txt"), r.get("reason"))
    ctl = controls(rows)
    # 候选⑤ 分母口径: 显式两栏（禁静默剔除）
    from collections import Counter
    dist = Counter(r["class"] for r in rows)
    denom = {
        "policy": "NO_ARTIFACT 窗的 cases_pass=0/58 **计入**配对（我方真实零分，剔除即抬高我方读数）；"
                  "同窗另记 denominator_class=NO_ARTIFACT 并**单列点名**；"
                  "`unreliable` 只保留给「真值自身失分窗」，两者不得混用。",
        "count_NO_ARTIFACT": len(noart),
        "count_runs": len(rows),
        "share": (round(len(noart) / len(rows), 3) if rows else None),
        "named_windows": ["%s/%s/%s" % (r["round"], r["win"], r["sub"]) for r in noart],
        "counts_by_class": dict(dist),
    }
    # 谓词落点: 产品源码里的 rc=4 契约拒收点
    src_hits = []
    p = os.path.join(REPO, "src/agent/r1/R1Pipeline.cs")
    if os.path.isfile(p):
        for i, ln in enumerate(io.open(p, encoding="utf-8").read().split("\n"), 1):
            if "契约未过" in ln:
                src_hits.append({"file": "src/agent/r1/R1Pipeline.cs", "line": i, "text": ln.strip()[:120]})
    out = {
        "round": "R588",
        "instrument": "eval/rover/r588/noartifact_cause_r588.py",
        "mode": "read_only (零产品改动 / 零新夹具 / 零远端)",
        "census_rows": rows,
        "class_distribution": dict(dist),
        "noartifact_replay": replays,
        "predicate_source_hits": src_hits,
        "denominator_policy_candidate5": denom,
        "controls": ctl,
        "has_teeth": (not ctl["fails"]),
    }
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"class_distribution": dict(dist), "noartifact": denom["named_windows"],
                      "replay": replays, "controls": ctl, "has_teeth": out["has_teeth"]},
                     ensure_ascii=False, indent=1))
    return 0 if out["has_teeth"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
