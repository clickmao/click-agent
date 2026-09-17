#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R528 · 挂载取证 (J1): 纪律第 6 条是否**真的进了实发 system 正文**。

「有代码行」不等于生效 (skill 口径) ⇒ 取 adapter 全量 dump (`full-agent-<n>.json` = 该次调用的
完整 messages 数组, 首条 role=system) 的**实发文本**逐字节判定:

  C1 处理臂 (A1-on) 的 system 含锚 `产物落位与自验` ∧ `工作根`; 控制臂 (A0-off) **不含**;
  C2 同一次调用序位上, A1-on system == A0-off system + "\\n\\n" + <纪律块> (逐字节, 前缀相同);
  C3 反解出的纪律块 sha256 **跨调用/跨臂/跨窗恒定** (常量块 ⇒ 不破坏常量前缀);
  C4 纪律块恰含 6 条编号项 (1..6 各一次) —— 防「锚在但条目被截断」。

用法:
  python3 eval/rover/r528/mount_check_r528.py --dir w1=eval/rover/r528/run-.../adapter \
      --range "A0-off=1,2" --range "A1-on=3,7" --out /tmp/mount-w1.json
退出码: 0 = C1..C4 全过; 1 = 判据不成立; 3 = 输入缺失/器具缺陷 (fail-closed, 不计入被测读数)。
"""
import argparse
import glob
import hashlib
import io
import json
import os
import re
import sys

REPO = "/home/agentuser/AgentFramework"
ANCHOR_A = "产物落位与自验"
ANCHOR_B = "工作根"
ITEM_RE = re.compile(r"(?:^|\n)(\d)\. ", re.M)


def sys_text(dump_dir, idx):
    for pat in ("full-agent-%03d.json" % idx, "full-agent-%d.json" % idx):
        p = os.path.join(dump_dir, pat)
        if os.path.isfile(p):
            msgs = json.load(io.open(p, encoding="utf-8", errors="replace"))
            for m in msgs:
                if isinstance(m, dict) and m.get("role") == "system":
                    c = m.get("content")
                    return c if isinstance(c, str) else ""
            return ""
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", action="append", required=True, help="<窗口>=<adapter目录>")
    ap.add_argument("--range", action="append", required=True, dest="ranges", help="<臂>=<起>,<止>")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    dirs = dict(d.split("=", 1) for d in a.dir)
    rng = {}
    for r in a.ranges:
        arm, span = r.split("=", 1)
        lo, hi = span.split(",")
        rng[arm] = (int(lo), int(hi))

    out = {"round": "R528", "what": "J1 挂载取证 (实发 system 正文)", "windows": {}, "checks": {}}
    all_ok = True
    blocks = {}

    for win, d in dirs.items():
        wrec = {"dir": d, "arms": {}}
        for arm, (lo, hi) in sorted(rng.items()):
            texts = []
            for i in range(lo, hi + 1):
                t = sys_text(d, i)
                if t is None:
                    out.setdefault("missing_dumps", []).append("%s/%s idx=%d" % (win, arm, i))
                    continue
                texts.append((i, t))
            wrec["arms"][arm] = {
                "calls": len(texts),
                "has_anchor_A": any(ANCHOR_A in t for _, t in texts),
                "has_anchor_B": any(ANCHOR_B in t for _, t in texts),
                "lens": [len(t) for _, t in texts],
                "sha8s": sorted({hashlib.sha256(t.encode()).hexdigest()[:8] for _, t in texts}),
            }
        # C2/C3: 同序位前缀关系 + 反解纪律块
        if wrec["arms"].get("A1-on", {}).get("calls") and wrec["arms"].get("A0-off", {}).get("calls"):
            a0 = [t for t in (sys_text(d, i) for i in range(rng["A0-off"][0], rng["A0-off"][1] + 1))
                  if isinstance(t, str)]
            a1 = [t for t in (sys_text(d, i) for i in range(rng["A1-on"][0], rng["A1-on"][1] + 1))
                  if isinstance(t, str)]
            k = min(len(a0), len(a1))
            suf = [a1[j][len(a0[j]) + 2:] for j in range(k) if a1[j].startswith(a0[j] + "\n\n")]
            # 同序位对齐只在两侧步结构一致时成立 (宿主修复回路调用无该块) ⇒ 判据取「至少 1 对可反解
            # 出块 ∧ 全部可反解出的块唯一」, 而不是「k 对全等」(后者会把步数不等当成未挂载)。
            wrec["C2_pairs_derived"] = len(suf)
            wrec["C2_offset_ok"] = len(suf) >= 1
            if suf:
                shas = {hashlib.sha256(s.encode()).hexdigest() for s in suf}
                wrec["block_sha8"] = sorted({s[:8] for s in shas})
                wrec["C3_block_constant"] = len(shas) == 1
                blk = suf[0]
                blocks[win] = hashlib.sha256(blk.encode()).hexdigest()
                items = [int(x) for x in ITEM_RE.findall(blk)]
                # 纪律块 = 固定 1..6 段 (宿主修复回路调用可能不含该块 ⇒ 已按前缀关系过滤)
                wrec["C4_items"] = items
                wrec["C4_items_complete"] = items == [1, 2, 3, 4, 5, 6]
                wrec["block_len"] = len(blk)
        out["windows"][win] = wrec

    c1 = all(v["arms"].get("A1-on", {}).get("has_anchor_A") and
             v["arms"].get("A1-on", {}).get("has_anchor_B") and
             not v["arms"].get("A0-off", {}).get("has_anchor_A", True) and
             not v["arms"].get("A0-off", {}).get("has_anchor_B", True)
             for v in out["windows"].values())
    c2 = all(v.get("C2_offset_ok") for v in out["windows"].values())
    c3 = all(v.get("C3_block_constant") for v in out["windows"].values()) and len(set(blocks.values())) <= 1
    c4 = all(v.get("C4_items_complete") for v in out["windows"].values())
    out["checks"] = {"C1_anchors_arm_split": c1, "C2_byte_prefix_null": c2,
                     "C3_discipline_block_constant": c3, "C4_six_items_present": c4,
                     "block_sha8_cross_window": sorted({h[:8] for h in blocks.values()}),
                     "missing_dumps": out.get("missing_dumps", [])}
    all_ok = bool(c1 and c2 and c3 and c4)

    missing = bool(out["checks"]["missing_dumps"]) or not out["windows"]
    with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    if missing:
        print("MOUNT_INPUT_MISSING missing=%s ⇒ rc=3 (器具/输入缺陷, 不计入被测读数)"
              % out["checks"]["missing_dumps"][:4])
        return 3
    for win, v in out["windows"].items():
        print("win=%s A1_len=%s A0_len=%s anchors(A1)=%s/%s anchors(A0)=%s/%s block_sha8=%s items=%s"
              % (win, v["arms"]["A1-on"]["lens"][:1], v["arms"]["A0-off"]["lens"][:1],
                 v["arms"]["A1-on"]["has_anchor_A"], v["arms"]["A1-on"]["has_anchor_B"],
                 v["arms"]["A0-off"]["has_anchor_A"], v["arms"]["A0-off"]["has_anchor_B"],
                 v.get("block_sha8"), v.get("C4_items")))
    print("MOUNT_VERDICT %s checks=%s" % ("PASS" if all_ok else "FAIL", out["checks"]))
    print("OUT %s" % os.path.relpath(a.out, REPO))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
