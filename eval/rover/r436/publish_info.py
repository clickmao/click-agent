#!/usr/bin/env python3
"""R436 发布形态台账 — 全部读数由命令产出（禁手抄）。

产出 eval/rover/r436/publish-info.json，供 compare_r436.py 引 C1。
读取: sha256/bytes/IL 警告数/CS 警告分布/native 标记/env -i 自启 rc/V0 闸/与上一发布(pub_r435b)的字节差簇。
"""
import hashlib
import json
import os
import re
import subprocess
import sys

D = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/agentuser/AgentFramework"
BIN = "/tmp/pub_r436/agenthost"
LOG = "/tmp/pub_r436.log"
PREV = "/tmp/pub_r435b/agenthost"


def sh(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


log = open(LOG, encoding="utf-8", errors="replace").read() if os.path.exists(LOG) else ""
info = {
    "bin": BIN,
    "sha256": sha(BIN) if os.path.exists(BIN) else None,
    "bytes": os.path.getsize(BIN) if os.path.exists(BIN) else None,
    "il_warnings": len(re.findall(r"warning IL\d+", log)),
    "cs_warnings": {m: len(re.findall(rf"warning {m}\b", log)) for m in sorted(set(re.findall(r"warning (CS\d+)", log)))},
    "native_code": "Generating native code" in log,
    "rc_from_log": (re.findall(r"^rc=(\d+)$", log, re.M) or [None])[-1],
    "head": sh(f"cd {ROOT} && git rev-parse HEAD")[1],
    "tree_dirty": bool(sh(f"cd {ROOT} && git status --porcelain")[1]),
    "pub_log": LOG,
}
rc, out = sh(f"env -i {BIN} --version <<< '/exit'")
info["env_i_version_rc_heredoc"] = rc            # 器具保留字段(已知假红: herestring 与真实调用方式不同)
# 权威做法: 与 prov_check 完全同法 (subprocess + input='/exit\n' + cwd=bin 目录)
p = subprocess.run(["env", "-i", os.path.abspath(BIN), "--version"], input="/exit\n",
                   capture_output=True, text=True, timeout=30, cwd=os.path.dirname(os.path.abspath(BIN)))
info["env_i_version_rc"] = p.returncode
info["env_i_banner"] = (p.stdout or "").splitlines()[0] if p.stdout else None
_prov = json.load(open(os.path.join(D, "prov-A-p12.json"), encoding="utf-8")) if os.path.exists(os.path.join(D, "prov-A-p12.json")) else {}
prov = _prov.get("under_test") and [_prov["under_test"]] + list(_prov.get("negative_controls") or []) or ([] if not _prov else [_prov])
under = prov[0] if prov else {}
neg = prov[1:]
info["v0_under_test"] = {"path": under.get("path"), "native_ok": under.get("native_ok"), "bare_rc": under.get("bare_rc"), "bytes": under.get("bytes")}
info["v0_negative_control"] = [{"path": r.get("path"), "native_ok": r.get("native_ok"), "bare_rc": r.get("bare_rc")} for r in neg]
info["v0_gate_pass"] = bool(under.get("native_ok")) and bool(neg) and all(r.get("native_ok") is False for r in neg)
if os.path.exists(PREV):
    rc, out = sh(f"cmp -l {PREV} {BIN} | wc -l")
    info["diff_vs_prev_publish"] = {"prev": PREV, "prev_sha256": sha(PREV), "diff_bytes": int(out or 0),
                                   "note": "同源码两次 AOT 发布的字节差 (BuildID/时间戳类)"}
    rc, offs = sh(f"cmp -l {PREV} {BIN} | awk '{{print $1}}'")
    if offs:
        o = [int(x) for x in offs.split()]
        clusters, start, prev = 1, o[0], o[0]
        for x in o[1:]:
            if x - prev > 512:
                clusters += 1
            prev = x
        info["diff_vs_prev_publish"].update({"off_min": o[0], "off_max": o[-1], "gap_clusters": clusters})
json.dump(info, open(os.path.join(D, "publish-info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(info, ensure_ascii=False, indent=2))
sys.exit(0 if (info["il_warnings"] == 0 and info["native_code"] and info["env_i_version_rc"] == 0) else 3)
