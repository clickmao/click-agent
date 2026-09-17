#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 合批轴挂载证明器 v2 (实发 prompt 取证, 不用自陈)。

单变量轴 = env `AGENTFRAMEWORK_ACTION_MERGE`; 产品改动 = `ActionLoopDiscipline.MergeText` 第 7 条。
本器只做一件事: 证明「开轴后**实发** system 的差量 = 第 7 条全文, 且前缀逐字节不变」。

判据:
  M1 A1-on 的 system 是 A2-merge system 的前缀 (保形: 只追加, 不改前段)
  M2 差量 **逐字节等于** `src/agent.modelqueue/ActionLoopDiscipline.cs` 里 `MergeText` 字面量拼接
     (从源码抽取, 不硬编码副本 ⇒ 文本改了本器自动跟着改; 长度 + sha256_12 双列)
  M3 A0-off (纪律关) 的 system 里既无纪律块锚也无第 7 条锚
  M4 两臂 system 均含 R525 分区常量前缀锚 (第 7 条没被插进中段)

用法:
  python3 eval/rover/r531/mount_check_r531.py [--run-dir <run>] [--window w1] [--out <json>]
  python3 eval/rover/r531/mount_check_r531.py --neg-control      # 器具自检 (必须判红)
rc: 0 = M1..M4 全绿 (或负控模式两针全中); 1 = 有判据未过。
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

REPO = "/home/agentuser/AgentFramework"
R531 = os.path.join(REPO, "eval/rover/r531")
DEFAULT_RUN = os.path.join(R531, "run-0917-213234")

MERGE_CLAUSE_HEAD = "\n7. 一次成型 (合批)"
DISCIPLINE_HEAD = "[上下文纪律 · 必守]"
PREFIX_ANCHOR = "[会话基线 v2 · 分区常量前缀]"
SRC = os.path.join(REPO, "src/agent.modelqueue/ActionLoopDiscipline.cs")


def merge_text_from_source():
    """从源码抽取 MergeText: 取 `public const string MergeText =` 之后到**字符串外的** `;`
    的全部字面量, 按 C# 语义拼接 (逐字符扫描, 不信正则 —— 文本里可能含 `;` 或 `\"`)。"""
    raw = io.open(SRC, encoding="utf-8").read()
    m = re.search(r"public const string MergeText\s*=", raw)
    if not m:
        raise SystemExit("[致命] 源码找不到 MergeText 常量")
    i = m.end()
    parts = []
    while i < len(raw):
        ch = raw[i]
        if ch == ";":
            break
        if ch != '"':
            i += 1
            continue
        i += 1
        buf = []
        while i < len(raw):
            c = raw[i]
            if c == "\\":
                buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(raw[i + 1], raw[i + 1]))
                i += 2
                continue
            if c == '"':
                i += 1
                break
            buf.append(c)
            i += 1
        parts.append("".join(buf))
    if not parts:
        raise SystemExit("[致命] MergeText 无字符串字面量")
    return "".join(parts)


def arm_ranges(run_dir):
    """读 <run>/logs/idx.txt (形如 `A0-off 1 80 0`) 得各臂请求区间 ⇒ {臂名: (lo, hi)}。"""
    p = os.path.join(run_dir, "logs", "idx.txt")
    if not os.path.isfile(p):
        return {}
    out = {}
    for ln in io.open(p, encoding="utf-8").read().splitlines():
        f = ln.split()
        if len(f) >= 3 and f[1].isdigit() and f[2].isdigit():
            out[f[0]] = (int(f[1]), int(f[2]))
    return out


def sys_of(run_dir, idx):
    p = os.path.join(run_dir, "adapter", "full-agent-%03d.json" % idx)
    msgs = json.load(io.open(p, encoding="utf-8"))
    if isinstance(msgs, dict):
        msgs = [msgs]
    return "".join(m.get("content") or "" for m in msgs if m.get("role") == "system")


def judge(a0, a1, a2, merge_text):
    delta = a2[len(a1):] if a2.startswith(a1) else None
    checks = {
        "M1_prefix_relation": a2.startswith(a1),
        "M2_delta_byte_equal_merge_text": delta == merge_text,
        "M3_A0_off_has_no_discipline_block": (DISCIPLINE_HEAD not in a0) and (MERGE_CLAUSE_HEAD not in a0),
        "M4_prefix_anchor_present_both": (PREFIX_ANCHOR in a1) and (PREFIX_ANCHOR in a2),
    }
    meta = {
        "sys_chars": {"A0-off": len(a0), "A1-on": len(a1), "A2-merge": len(a2)},
        "delta_chars": None if delta is None else len(delta),
        "merge_text_chars": len(merge_text),
        "delta_sha12": None if delta is None else hashlib.sha256(delta.encode()).hexdigest()[:12],
        "merge_text_sha12": hashlib.sha256(merge_text.encode()).hexdigest()[:12],
        "delta_repr": (delta[:120] + "…") if delta else None,
    }
    return checks, meta


def load_arm_sys(run_dir, arm):
    rng = arm_ranges(run_dir)
    if arm not in rng:
        return None, None
    lo = rng[arm][0]
    return sys_of(run_dir, lo), lo


def derive_window(run_dir):
    """窗口名: 目录名尾缀 -w<k> > 目录内 SUMMARY-<win>.txt > 未知。"""
    base = os.path.basename(run_dir.rstrip("/"))
    m = re.search(r"-(w\d+)$", base)
    if m:
        return m.group(1)
    hits = sorted(f for f in os.listdir(run_dir) if f.startswith("SUMMARY-") and f.endswith(".txt"))
    if hits:
        return hits[0][len("SUMMARY-"):-len(".txt")]
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=DEFAULT_RUN)
    ap.add_argument("--window", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--neg-control", action="store_true")
    a = ap.parse_args()

    win = a.window or derive_window(a.run_dir)
    out = a.out or os.path.join(R531, "evidence", "mount-r531-%s.json" % win)
    mt = merge_text_from_source()

    a0, i0 = load_arm_sys(a.run_dir, "A0-off")
    a1, i1 = load_arm_sys(a.run_dir, "A1-on")
    a2, i2 = load_arm_sys(a.run_dir, "A2-merge")
    if None in (a0, a1, a2):
        print("[致命] 缺臂 system (run=%s 缺 A0-off/A1-on/A2-merge 之一)" % a.run_dir)
        return 3

    res = {
        "round": "R531",
        "instrument": "eval/rover/r531/mount_check_r531.py (v2)",
        "run_dir": os.path.relpath(a.run_dir, REPO),
        "window": win,
        "sys_request_idx": {"A0-off": i0, "A1-on": i1, "A2-merge": i2},
        "source_of_truth": os.path.relpath(SRC, REPO) + " :: MergeText (源码抽取)",
        "var": "AGENTFRAMEWORK_ACTION_MERGE",
    }
    checks, meta = judge(a0, a1, a2, mt)
    res.update(meta)
    res["checks"] = checks
    res["MOUNT_OK"] = all(checks.values())

    nres = None
    if a.neg_control:
        # NC1: 把 A1/A2 角色对调 ⇒ M1/M2 必红 (防「恒真门」)
        c1, _ = judge(a0, a2, a1, mt)
        # NC2: 同一臂当基线 (差量空) ⇒ M2 必红
        c2, _ = judge(a0, a1, a1, mt)
        nres = {
            "NC1_roles_swapped_expect_red": {"M1": c1["M1_prefix_relation"], "M2": c1["M2_delta_byte_equal_merge_text"]},
            "NC2_self_vs_self_expect_red": {"M2": c2["M2_delta_byte_equal_merge_text"]},
            "NC1_fired": (not c1["M1_prefix_relation"]) or (not c1["M2_delta_byte_equal_merge_text"]),
            "NC2_fired": not c2["M2_delta_byte_equal_merge_text"],
        }
        nres["NEG_CONTROL_OK"] = nres["NC1_fired"] and nres["NC2_fired"]
        res["neg_control"] = nres

    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)

    for k in ("M1_prefix_relation", "M2_delta_byte_equal_merge_text",
              "M3_A0_off_has_no_discipline_block", "M4_prefix_anchor_present_both"):
        print("%-34s %s" % (k, "PASS" if checks[k] else "FAIL"))
    print("sys_chars", res["sys_chars"], "delta_chars", res["delta_chars"],
          "merge_text_chars", res["merge_text_chars"])
    print("delta_sha12=%s merge_text_sha12=%s" % (res["delta_sha12"], res["merge_text_sha12"]))
    print("MOUNT_OK=%s" % res["MOUNT_OK"])
    if nres:
        print("NC1_fired=%s NC2_fired=%s NEG_CONTROL_OK=%s" % (nres["NC1_fired"], nres["NC2_fired"], nres["NEG_CONTROL_OK"]))
    print("OUT=%s" % out)
    if a.neg_control:
        return 0 if nres["NEG_CONTROL_OK"] else 1
    return 0 if res["MOUNT_OK"] else 1


if __name__ == "__main__":
    sys.exit(main())
