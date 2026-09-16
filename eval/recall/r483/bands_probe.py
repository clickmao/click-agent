#!/usr/bin/env python3
"""R483: 【探索】精度分档读数 —— 复用 R481-F 的源码派生端口 (不复制规则), 按 prereg_r481g 的档定义切分。

语言无关: 候选分类只依据 port 自身抽取结果与路径代数, 不依赖文件后缀/语言标签。
三态: rc=0 读数完成 / rc=2 内部不变量失败 (fail-closed) / rc=3 缺输入或端口派生失败 (弃权)。
不变量: ① 各档 refs 之和 == 端口总 refs (守恒) ② 零候选档 ⇒ null (禁作 0) ③ 两句断言失败即 rc=2。
"""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PORT_PATH = ROOT / "eval" / "recall" / "links_port_r482.py"
PREREG = ROOT / "eval" / "recall" / "prereg_r481g.json"
OUT_DIR = ROOT / "eval" / "recall" / "r483"
BANDS = ("markdown", "root_rel", "explicit_rel", "slash_token")


def load_port():
    spec = importlib.util.spec_from_file_location("port_r482", PORT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def band_of(port, value, raw, origin, root):
    """档归属 (与 prereg_r481g.bands.definitions 逐条对应)。"""
    if origin == "markdown":
        return "markdown"
    if origin == "url":
        return None  # unreported, 不入档
    if raw.startswith(port.REL_PREFIXES):
        return "explicit_rel"
    full = os.path.normpath(os.path.join(root, value))
    inside = full == root or full.startswith(root + os.sep)
    return "root_rel" if inside else "slash_token"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DIR / "bands.json"))
    ap.add_argument("--limit", type=int, default=0, help="只扫前 N 个文件 (冒烟用; >0 时 marked partial)")
    ap.add_argument("--nc-conservation", action="store_true", help="负控: 故意破坏守恒 ⇒ 须 rc=2")
    a = ap.parse_args(argv)

    for p in (PORT_PATH, PREREG):
        if not p.is_file():
            print("MISS:", p)
            return 3
    try:
        port = load_port()
        port.derive()          # 端口派生失败 ⇒ DeriveError ⇒ rc=3 弃权
    except Exception as ex:    # noqa: BLE001
        print("MISS: 端口派生失败:", type(ex).__name__, ex)
        return 3

    root = port.ROOT
    files = port.collect()
    # 器具自污染闸: 本探针的产物目录不得入语料 (否则每跑一次 pin 就漂移 ⇒ 读数不可复现)
    SELF_OUT = ("eval/recall/r483/",)
    files = [(rel, txt) for rel, txt in files if not rel.replace(os.sep, "/").startswith(SELF_OUT)]
    if not files:
        print("MISS: 语料根为空")
        return 3
    partial = a.limit > 0
    if partial:
        files = files[: a.limit]

    st = {b: dict(refs=0, resolved=0, dangling=0, escaped=0, rewrite_ok=0, failclosed=0) for b in BANDS}
    meta = dict(files=len(files), refs=0, url_unreported=0, external_by_origin=dict(markdown=0, rel=0))
    corpus_h = hashlib.sha256()
    for rel, txt in files:
        corpus_h.update(f"{rel}:{len(txt.encode('utf-8'))}\n".encode("utf-8"))
        for value, raw, origin in port.extract(txt, referrer=rel):
            meta["refs"] += 1
            if origin == "url":
                meta["url_unreported"] += 1
                continue
            # 与端口 measure() 语义一致: 任一来源若最终值是 scheme 地址 ⇒ external, 单列 unreported, 禁入档分母
            if any(value.lower().startswith(s.lower()) for s in port.SCHEMES):
                meta["url_unreported"] += 1
                meta["external_by_origin"]["markdown" if origin == "markdown" else "rel"] += 1
                continue
            b = band_of(port, value, raw, origin, root)
            d = st[b]
            d["refs"] += 1
            full = os.path.normpath(os.path.join(root, value))
            inside = full == root or full.startswith(root + os.sep)
            if not inside:
                d["dangling"] += 1
                d["escaped"] += 1
                continue
            if os.path.isfile(full):
                d["resolved"] += 1
                if b == "explicit_rel":
                    if value != raw:
                        d["rewrite_ok"] += 1
                    else:
                        d["failclosed"] += 1
                continue
            d["dangling"] += 1
            if b == "explicit_rel" and value == raw:
                d["failclosed"] += 1

    # 守恒不变量 (fail-closed)
    if a.nc_conservation:
        st["markdown"]["refs"] += 1     # 负控: 制造守恒破裂
    banded = sum(st[b]["refs"] for b in BANDS)
    if banded + meta["url_unreported"] != meta["refs"]:
        print("ASSERT: 守恒失败", banded, meta["url_unreported"], meta["refs"])
        return 2
    for b in BANDS:
        if st[b]["refs"] == 0 and b == "markdown" and not partial:
            print("ASSERT: markdown 档零候选 (语料异常)")
            return 2

    def rate(b, num, den):
        return None if st[b][den] == 0 else round(st[b][num] / st[b][den], 4)

    out = {
        "round": "R483",
        "instrument": {"path": str(PORT_PATH.relative_to(ROOT)), "reused_port": "r482",
                       "rule_source_sha16": port.C["_rule_sha256"][:16],
                       "self_sha16": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]},
        "corpus": {"files": meta["files"], "files_sha16": corpus_h.hexdigest()[:16], "partial": partial,
                   "self_out_excluded": ["eval/recall/r483/"],
                   "head": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                          capture_output=True, text=True).stdout.strip(),
                   "worktree_dirty_files": len([l for l in subprocess.run(
                       ["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True)
                       .stdout.splitlines() if l.strip()])},
        "readings": {"refs_total": meta["refs"], "url_unreported": meta["url_unreported"],
                     "external_by_origin": meta["external_by_origin"], "bands": st},
        "judgment": {
            "markdown": {"target": "resolved_rate >= 0.90", "value": rate("markdown", "resolved", "refs")},
            "root_rel": {"target": "resolved_rate >= 0.90", "value": rate("root_rel", "resolved", "refs")},
            "explicit_rel": {"target": "rewrite_ok_rate >= 0.85", "value": rate("explicit_rel", "rewrite_ok", "refs"),
                             "failclosed": st["explicit_rel"]["failclosed"]},
            "slash_token": {"target": "无门槛 (命名噪声计量)", "value": rate("slash_token", "resolved", "refs"),
                            "dangling": st["slash_token"]["dangling"]},
            "url": {"target": "unreported (禁作 0)", "value": None},
        },
        "comparability": "仅当 (corpus.files_sha16, instrument.rule_source_sha16) 与前读数全等方可对照; 否则标『不可比(语料漂移)』",
        "prereg": str(PREREG.relative_to(ROOT)),
    }
    for k, v in out["judgment"].items():
        if k in ("markdown", "root_rel", "explicit_rel"):
            tgt = 0.90 if k != "explicit_rel" else 0.85
            v["pass"] = None if v["value"] is None else bool(v["value"] >= tgt)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"corpus": out["corpus"], "refs_total": meta["refs"], "url_unreported": meta["url_unreported"],
                      "judgment": out["judgment"]}, ensure_ascii=False, indent=1))
    print("bands_detail", json.dumps(st, ensure_ascii=False))
    print("out", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
