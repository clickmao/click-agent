#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R587 · 只读定因 ①: 「wythoff 单族失败是否落在**同一子规格**」。

零产品改动 / 零新夹具 / 零远端 —— 输入面全部为已冻结、已登记的产物快照。

判法（机械, 无人工口径）:
  1. 逐 (轮, 窗, 臂) 复制件取 `games/wythoff.py` 的 sha256 ⇒ **产物身份**。
     不同 sha ⇒ 不同实现 ⇒ 「同一子规格」命题只能按**实现族**判, 不能按输入族判。
  2. 对每份产物做**冷点判据形态指纹**（正则标记集, 互斥标签 + 允许多标签）:
       PHI_DIFF     : 用 `d = hi - lo` 与 φ 常数直接比 (标准 Wythoff 冷点判据)
       PHI_WINDOW   : 对 `int(m*phi)` 开窗口 (±k) 接受多个候选 ⇒ **过宽**判据
       BRUTE_LEX    : 冷点集由 (a,b) **字典序**嵌套循环 + `in cold` 递推构造 (序错 ⇒ 漏/错)
       AND_MEMO     : 记忆化/字典缓存构造
       SHAPE_OTHER  : 可识别但不在上表
       UNCLASSIFIED : 无任何标记命中 (须人读; 记为欠分类, 不静默)
  3. 把每份产物的失败类别分布与之映射: 同一 sha 在不同窗的失败签名是否**逐例相同**
     （同产物 ⇒ 同输入必同输出, 故同 sha 的失败签名漂移 = 器具读数缺陷, 不是被测漂移）。
  4. 自证有牙（负控）: 指纹函数对**注入的已知形态**必须给对应标签;
     且对一份「标准 φ 差判据」的合成样本必须**不**命中 PHI_WINDOW / BRUTE_LEX。

用法:
  python3 eval/rover/r587/wythoff_subspec_r587.py [--rounds r586,r587] [--out <path>]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re

REPO = "/home/agentuser/AgentFramework"
CASES = os.path.join(REPO, "eval/rover/r586/cases/cases-r521.json")

MARKERS = [
    ("PHI_DIFF", re.compile(r"(hi\s*-\s*lo|d\s*=\s*[a-z]+\s*-\s*[a-z]+)[\s\S]{0,200}?1\.618|\*\s*phi\b|1\.618033988749895")),
    ("PHI_WINDOW", re.compile(r"cand_u\s*-\s*\d|cand_u\s*\+\s*\d|for\s+cu\s+in")),
    ("PHI_APPROX", re.compile(r"1\.6[0-9]?\b(?!180)|1\.62\b")),
    ("PHI_ROUND", re.compile(r"round\(\s*[a-z_]*\s*\*\s*phi|round\(.*phi")),
    ("BRUTE_LEX", re.compile(r"for\s+[ab]\s+in\s+range\([^)]*\)[\s\S]{0,200}?for\s+[ab]\s+in\s+range\([^)]*\)[\s\S]{0,400}?in\s+cold")),
    ("SUM_ORDER", re.compile(r"for\s+s\s+in\s+range|for\s+tot\s+in\s+range|for\s+\w*sum\w*\s+in\s+range")),
    ("TABLE_PRECOMP", re.compile(r"PAIRS\s*=|COLD\s*=\s*[\[\(]|LOSING\s*=\s*\[")),
    ("EQUAL_ONLY", re.compile(r"a\s*==\s*b\s*$|x\s*==\s*y\s*$", re.M)),
    ("AND_MEMO", re.compile(r"@lru_cache|memo\[|functools\.cache")),
]


def sem_hash(src: str) -> str:
    """语义骨架哈希: 去注释/文档串/空行, 归一并空白 ⇒ 证明「不同 sha」不是排版差异。"""
    s = re.sub(r'"""(?:.|\n)*?"""', "", src)
    s = re.sub(r"'''(?:.|\n)*?'''", "", s)
    s = re.sub(r"#[^\n]*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def sha12(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def fingerprint(src: str):
    hits = [tag for tag, rx in MARKERS if rx.search(src)]
    if not hits:
        return (["UNCLASSIFIED"], False)
    if not ({"PHI_DIFF"} & set(hits)) and not ({"PHI_WINDOW"} & set(hits)) and "BRUTE_LEX" not in hits:
        hits.append("SHAPE_OTHER")
    return (sorted(set(hits)), True)


def selftest_fingerprint():
    """负控: 指纹必须对已知形态给对应标签, 且对标准形态不误报过宽/暴力。"""
    out = []
    std = "d = hi - lo\nreturn lo == int(d * 1.618033988749895)\n"
    tags, ok = fingerprint(std)
    if "PHI_DIFF" not in tags:
        out.append("标准 φ 差判据未命中 PHI_DIFF")
    if "PHI_WINDOW" in tags or "BRUTE_LEX" in tags:
        out.append("标准形态误报 PHI_WINDOW/BRUTE_LEX: %s" % tags)
    win = "cand_u = int(m * phi)\nfor cu in (cand_u - 2, cand_u - 1, cand_u, cand_u + 1, cand_u + 2):\n    cv = cu + m\n"
    tags2, _ = fingerprint(win)
    if "PHI_WINDOW" not in tags2:
        out.append("±窗口形态未命中 PHI_WINDOW: %s" % tags2)
    brute = ("cold=set()\nfor a in range(LIM+1):\n    for b in range(LIM+1):\n"
             "        for i in range(a+1):\n            for j in range(b+1):\n"
             "                if (a-i,b-j) in cold:\n                    is_cold=False\n")
    tags3, _ = fingerprint(brute)
    if "BRUTE_LEX" not in tags3:
        out.append("字典序暴力形态未命中 BRUTE_LEX: %s" % tags3)
    junk, _ = fingerprint("def f():\n    return 42\n")
    if junk != ["UNCLASSIFIED"]:
        out.append("无标记文本应欠分类为 UNCLASSIFIED: %s" % junk)
    return out


def load_cases():
    allc = json.load(io.open(CASES, encoding="utf-8"))
    return [c for c in allc if c["game"] == "wythoff"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default="r585,r586")
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r587/wythoff-subspec-r587.json"))
    a = ap.parse_args()
    cases = load_cases()
    st = selftest_fingerprint()

    copies, by_sha = [], {}
    for rk in a.rounds.split(","):
        sroot = os.path.join(REPO, "eval/rover", rk, "snapshots")
        if not os.path.isdir(sroot):
            continue
        for win in sorted(os.listdir(sroot)):
            wd = os.path.join(sroot, win)
            if not os.path.isdir(wd):
                continue
            for arm in sorted(os.listdir(wd)):
                f = os.path.join(wd, arm, "g1", "games", "wythoff.py")
                if not os.path.isfile(f):
                    copies.append({"round": rk, "win": win, "arm": arm, "wythoff_py": None})
                    continue
                b = io.open(f, "rb").read()
                src = b.decode("utf-8", "replace")
                tags, classified = fingerprint(src)
                rec = {"round": rk, "win": win, "arm": arm, "sha12": sha12(b), "sem12": sem_hash(src),
                       "bytes": len(b), "lines": src.count("\n") + 1, "tags": tags, "classified": classified}
                copies.append(rec)
                by_sha.setdefault(rec["sha12"], {"specs": [], "copies": []})
                by_sha[rec["sha12"]]["specs"].append({"round": rk, "win": win, "arm": arm, "tags": tags})
                by_sha[rec["sha12"]]["copies"].append("%s/%s/%s" % (rk, win, arm))

    # 失败签名: 取已登记定因件 (R586) 的逐 (窗,臂) 类别分布做映射; 不重算判分
    causep = os.path.join(REPO, "eval/rover/r586/wythoff-cause-r586.json")
    sig = {}
    if os.path.isfile(causep):
        cd = json.load(io.open(causep, encoding="utf-8"))
        for k, v in (cd.get("per_arm_window") or {}).items():
            sig[k] = {"n_pass": v.get("n_pass"), "classes": v.get("classes"), "fail_idx": sorted(v.get("fail_idx") or [])}
    per_sha_sig = {}
    for rec in copies:
        if not rec.get("sha12"):
            continue
        k = "%s|%s" % (rec["win"], rec["arm"])
        per_sha_sig.setdefault(rec["sha12"], {})[k] = sig.get(k)

    # 同一 sha 在不同窗的失败签名是否逐例相同
    sha_sig_stable = {}
    for s, m in per_sha_sig.items():
        fs = [json.dumps(v, sort_keys=True) for v in m.values() if v]
        sha_sig_stable[s] = {"n_windows": len(m), "signatures_distinct": len(set(fs)),
                             "stable": len(set(fs)) <= 1}

    # 同一输入在不同 sha 下的落点 (从 raw_rows 取, 只读)
    landings = {}
    if os.path.isfile(causep):
        cd = json.load(io.open(causep, encoding="utf-8"))
        for k, rows in (cd.get("raw_rows") or {}).items():
            for r in rows:
                if r.get("class") not in ("OK", "MOVE_NOT_COLD"):
                    continue
                for rec in copies:
                    if rec["win"] + "|" + rec["arm"] == k and rec.get("sha12"):
                        landings.setdefault("idx%02d" % r["idx"], {}).setdefault(rec["sha12"], set()).add(
                            "%s->%s" % (r["class"], r.get("got")))
    landings = {k: {s: sorted(v) for s, v in m.items()} for k, m in landings.items()}

    n_cls = len([c for c in copies if c.get("classified")])
    out = {
        "round": "R587",
        "instrument": "eval/rover/r587/wythoff_subspec_r587.py",
        "mode": "read_only (零产品改动 / 零新夹具 / 零远端)",
        "copies": copies,
        "n_copies": len(copies),
        "n_distinct_programs": len([s for s in by_sha]),
        "n_distinct_sem": len({c["sem12"] for c in copies if c.get("sem12")}),
        "sem_equals_sha_identity": (len({c["sem12"] for c in copies if c.get("sem12")}) ==
                                    len({c["sha12"] for c in copies if c.get("sha12")})),
        "by_sha": {s: {"copies": v["copies"], "tags": sorted({t for x in v["specs"] for t in x["tags"]})}
                   for s, v in by_sha.items()},
        "tag_histogram": {t: len([c for c in copies if t in (c.get("tags") or [])])
                          for t in sorted({t for c in copies for t in (c.get("tags") or [])})},
        "per_sha_window_signature": sha_sig_stable,
        "landings_by_case": landings,
        "unclassified": [c for c in copies if c.get("tags") == ["UNCLASSIFIED"]],
        "missing_wythoff_py": [c for c in copies if not c.get("wythoff_py", "")],
        "fingerprint_selftest_fails": st,
        "has_teeth": (not st),
        "classified_ratio": round(n_cls / max(len(copies), 1), 3),
    }
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"n_copies": out["n_copies"], "n_distinct_programs": out["n_distinct_programs"],
                      "tag_histogram": out["tag_histogram"], "selftest_fails": st,
                      "classified_ratio": out["classified_ratio"]}, ensure_ascii=False, indent=1))
    return 0 if not st else 1


if __name__ == "__main__":
    raise SystemExit(main())
