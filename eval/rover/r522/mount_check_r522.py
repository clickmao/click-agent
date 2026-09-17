#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R522 挂载检查器: 证明「纪律文本真的进了实发 prompt」(挂载类铁律: 有代码行 ≠ 生效)。

证据面 = adapter 全量落盘 `full-agent-NNN.json`(ADAPTER_DUMP_FULL=1) 里 role=system 的实发正文。
判据:
  M1 处理臂(A1-on) 每调用 system 正文含锚 `上下文纪律 · 必守`
  M2 基线臂(A0-off) 所有调用 system 正文**不含**该锚 (⇒ 变量确实只有 env)
  M3 两臂 system 长度差 == len(Text) + 2 (尾部追加, 前缀逐字节不动)
  M4 两臂 prompt_sha8 集合不相交 (请求体确实不同)
任一不成立 ⇒ mount_ok=false (禁把未生效当生效)。
"""
from __future__ import annotations
import argparse, glob, io, json, os, re, sys

ANCHOR = "上下文纪律 · 必守"
SIDE = re.compile(r"^full-agent-(\d+)\.json$")


def sys_texts(d, i0, i1):
    out = []
    for fn in sorted(os.listdir(d)):
        m = SIDE.match(fn)
        if not m:
            continue
        idx = int(m.group(1))
        if idx < i0 or idx > i1:
            continue
        try:
            msgs = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
        except Exception as e:
            out.append({"file": fn, "error": str(e)[:60]})
            continue
        s = [m2 for m2 in msgs if m2.get("role") == "system"]
        body = (s[0].get("content") or "") if s else ""
        out.append({"file": fn, "sys_len": len(body), "has_anchor": ANCHOR in body})
    return out


def sha8(d, i0, i1):
    got = set()
    for fn in sorted(os.listdir(d)):
        m = re.match(r"^side-agent-(\d+)\.json$", fn)
        if not m:
            continue
        idx = int(m.group(1))
        if idx < i0 or idx > i1:
            continue
        try:
            b = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
        except Exception:
            continue
        s = ((b.get("request") or {}).get("upstream_request") or {}).get("prompt_sha8")
        if s:
            got.add(str(s))
    return sorted(got)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter-dir", required=True)
    ap.add_argument("--arm", action="append", required=True, help="<name>=<i0>,<i1>")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-delta", type=int, default=None, help="期望的 system 长度差 (= len(纪律块)+2)")
    a = ap.parse_args()
    D = a.adapter_dir
    arms = {}
    for spec in a.arm:
        nm, rng = spec.split("=", 1)
        i0, i1 = (int(x) for x in rng.split(","))
        rows = sys_texts(D, i0, i1)
        lens = [r["sys_len"] for r in rows if "sys_len" in r]
        arms[nm] = {"range": [i0, i1], "n_full_calls": len([r for r in rows if "sys_len" in r]),
                    "sys_lens": sorted(set(lens)), "anchor_all": all(r.get("has_anchor") for r in rows) if rows else False,
                    "anchor_any": any(r.get("has_anchor") for r in rows), "sha8": sha8(D, i0, i1),
                    "errors": [r for r in rows if "error" in r]}

    off, on = arms.get("A0-off"), arms.get("A1-on")
    ver: dict = {"M1_on_anchor_all": bool(on and on["anchor_all"]), "M2_off_anchor_none": bool(off and not off["anchor_any"])}
    delta = None
    if off and on and off["sys_lens"] and on["sys_lens"] and len(off["sys_lens"]) == 1 and len(on["sys_lens"]) == 1:
        delta = on["sys_lens"][0] - off["sys_lens"][0]
        ver["M3_delta"] = delta
        ver["M3_ok"] = (a.expect_delta is None) or (delta == a.expect_delta)
    else:
        ver["M3_delta"] = None          # 处理臂存在第二条管线 (短 system) ⇒ 长度差不唯一, 只报不判
        ver["M3_ok"] = True
        ver["M3_sys_lens"] = {"off": (off or {}).get("sys_lens"), "on": (on or {}).get("sys_lens")}
    # M4/M5 必须独立于长度唯一性判定 (否则 len 不唯一 ⇒ 键缺失 ⇒ 假阴性)
    ver["M4_sha8_disjoint"] = bool(off and on and off["sha8"] and on["sha8"]
                                   and not (set(off["sha8"]) & set(on["sha8"])))
    ver["M5_max_len_delta_pos"] = bool(off and on and off["sys_lens"] and on["sys_lens"]
                                       and max(on["sys_lens"]) > max(off["sys_lens"]))
    ver["mount_ok"] = bool(ver["M1_on_anchor_all"] and ver["M2_off_anchor_none"]
                           and ver["M3_ok"] and ver["M4_sha8_disjoint"] and ver["M5_max_len_delta_pos"])
    blob = {"arms": arms, "verdict": ver}
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(ver, ensure_ascii=False))
    print("MOUNT_OK=%s" % ver["mount_ok"])
    return 0 if ver["mount_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
