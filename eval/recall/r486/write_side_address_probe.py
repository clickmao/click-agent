#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R486 【探索】写侧地址有效性诊断 (描述性口径, 语言无关).

目的: R483 分档读数暴露 markdown 档 0.8125 的悬空**不是** slash token 混杂所致 ⇒ 需判定悬空
     归属「解析侧缺陷」还是「写侧从未写出该目标」。本器具只读仓库文本, 不做语义推断:
       分类 = f(目标字符串, 引用方目录, 语料现存路径集合)      # 路径代数, 与语言/后缀无关
     三类判定:
       resolved       目标按引用方目录/仓根解析成功
       moved          目标不存在, 但**同基名文件存在于语料** ⇒ 路径写误或被移动 (写侧可修)
       never_written  目标不存在且全语料无同基名    ⇒ 目标从未落盘 (写侧缺失)
     单列: escape(越根) / url(带 scheme, unreported, 禁作 0)

三态退出码: 0=完成且守恒 1=断言不成立(判红) 3=缺输入/语料为空
负控: --nc-perturb 把一个 resolved 目标改成不存在的名字 ⇒ 必须翻为 moved 或 never_written
自污染闸: 本器具自身产物目录不得入被扫语料 (否则每跑一次读数漂移)
"""
import argparse, hashlib, json, os, re, sys, unicodedata
from collections import Counter

SELF_OUT = ("eval/recall/r486/",)
SKIP_DIR = {".git", "bin", "obj", "node_modules", ".hermes", ".venv", "venv", "dist", "build", "__pycache__"}
SCAN_SUFFIX = (".md", ".markdown", ".txt")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
LINK = re.compile(r"\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")


def walk_files(root, keep=None):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if rel_dir == ".":
            rel_dir = ""
        if any((rel_dir + "/").startswith(s) or rel_dir.startswith(s.rstrip("/")) for s in SELF_OUT):
            continue
        for fn in filenames:
            if keep is not None and not fn.lower().endswith(keep):
                continue
            rel = (rel_dir + "/" + fn) if rel_dir else fn
            if any(rel.startswith(s) for s in SELF_OUT):
                continue
            out.append(rel)
    return sorted(out)


def corpus_files(root):
    """引用扫描面: 只有文本类文件才可能携带链接."""
    return walk_files(root, keep=SCAN_SUFFIX)


def existing_files(root):
    """存在性判定面: 目标可以是任何类型 (含 .cs/.json/.svg 等), 只有非忽略目录被排除."""
    return walk_files(root, keep=None)


def norm_target(t):
    t = t.strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1]
    t = t.split("#", 1)[0].split("?", 1)[0]
    t = t.replace("\\", "/")
    try:
        t = unicodedata.normalize("NFC", t)
    except Exception:
        pass
    return t


def classify(target, referrer_dir, fileset, basename_index):
    if target == "":
        return "empty", None
    if SCHEME.match(target) and not re.match(r"^[A-Za-z]:[/\\]", target):
        return "url", None
    cand = target[1:] if target.startswith("/") else (referrer_dir + "/" + target if referrer_dir else target)
    parts = []
    escaped = False
    for seg in cand.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            else:
                escaped = True
            continue
        parts.append(seg)
    if escaped:
        return "escape", None
    resolved = "/".join(parts)
    if resolved in fileset:
        return "resolved", resolved
    base = parts[-1] if parts else ""
    if base and base in basename_index:
        return "moved", resolved
    return "never_written", resolved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--limit-files", type=int, default=0)
    ap.add_argument("--nc-perturb", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    files = corpus_files(root)
    if args.limit_files:
        files = files[: args.limit_files]
    if not files:
        print("ASSERT: 语料为空", file=sys.stderr)
        return 3

    fileset = set(existing_files(root))
    basename_index = Counter(p.rsplit("/", 1)[-1] for p in fileset)
    sha = hashlib.sha256("\n".join("%s|%d" % (p, os.path.getsize(os.path.join(root, p))) for p in files).encode()).hexdigest()[:16]

    counter = Counter()
    samples = {}
    refs_total = 0
    for rel in files:
        try:
            raw = open(os.path.join(root, rel), "r", encoding="utf-8", errors="replace").read()
        except OSError:
            counter["io_error"] += 1
            continue
        referrer_dir = rel.rsplit("/", 1)[0] if "/" in rel else ""
        for m in LINK.finditer(raw):
            tgt_raw = m.group(1)
            tgt = norm_target(tgt_raw)
            if args.nc_perturb and classify(tgt, referrer_dir, fileset, basename_index)[0] == "resolved":
                tgt = tgt + "_r486_perturbed_missing"
            kind, resolved = classify(tgt, referrer_dir, fileset, basename_index)
            refs_total += 1
            counter[kind] += 1
            key = (kind, tgt_raw[:80])
            if counter[kind] <= 40 and key not in samples and len(samples) < 4000:
                samples[key] = {"ref": tgt_raw[:120], "referrer": rel, "classified": kind, "resolved_as": resolved}
    ordered = []
    seen = Counter()
    for (kind, _), v in samples.items():
        if seen[kind] >= args.samples:
            continue
        seen[kind] += 1
        ordered.append(v)

    resolved_n = counter["resolved"]
    denom = refs_total - counter["url"] - counter["empty"]
    report = {
        "instrument": "write_side_address_probe.py",
        "status": "ok" if not args.nc_perturb else "nc",
        "root": root,
        "corpus": {"files": len(files), "files_sha16": sha, "scan_suffix": list(SCAN_SUFFIX), "self_out_excluded": list(SELF_OUT)},
        "refs": {"total": refs_total, "url_unreported": counter["url"], "empty": counter["empty"]},
        "classes": {k: counter[k] for k in ("resolved", "moved", "never_written", "escape", "url", "empty", "io_error")},
        "resolved_ratio_paths_only": round(resolved_n / denom, 4) if denom else None,
        "conservation": {"expr": "refs_total == sum(classes)", "ok": refs_total == sum(counter[k] for k in ("resolved", "moved", "never_written", "escape", "url", "empty", "io_error"))},
        "samples": ordered,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: report[k] for k in ("status", "refs", "classes", "resolved_ratio_paths_only", "conservation")}, ensure_ascii=False))
    print("corpus:", report["corpus"])
    if not report["conservation"]["ok"]:
        print("ASSERT: 守恒失败", file=sys.stderr)
        return 1
    if args.nc_perturb and counter["resolved"] != 0:
        print("ASSERT: 负控未翻红 resolved=%d" % counter["resolved"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
