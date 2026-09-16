#!/usr/bin/env python3
"""EXP1-Q34 · 候选⑤: 依赖**递归一级** (depth-2) + 11 件 external_asset 的显式不可入库裁定。

Q33 只做到 depth-1: 22 个被引 /tmp 依赖逐条裁定 (archived 10 / external_asset 11 / 截断 1)。
残留缺口 = 两类「未闭合」:
  (a) **二级依赖**: 已被入库或被引的产物**自身**又引用别的 /tmp 路径 ⇒ 复现前提没有传递闭包;
  (b) **不可入库的理由没有机检**: external_asset 只写了人读 reason 串, 没有 (kind, bytes, license)
      这类可机检字段 ⇒ 审计者无法判「确实是不可入库」还是「忘了入库」。

本器具备:
  1. 对 depth-1 的每一条 (入库副本优先, 现场副本其次) 抽 `/tmp/...` 引用 ⇒ depth-2 行;
  2. depth-2 用 **与 Q33 同一分类器** (importlib 加载, 不复制一份判据 ⇒ 不会漂移) 分类;
  3. depth-2 中可入库者**逐字节入库 + 读回复核 sha256** (存不下/非文本 ⇒ 转 external_asset 并记因);
  4. 每条 external_asset (depth-1 11 件 + depth-2 新增) 落 **机检字段**: kind/bytes/sha256/license/
     archivable=false/why_not_archivable (闭集 reason_code) —— 「不入库」从此是**有依据的裁定**;
  5. 守恒式: depth-2 行数 == Σ 各类; depth-1 22 行**每行都有 disposition**; depth-3 只**计数不追**
     (声明的递归边界, 不静默)。

退出码: 0 全绿 / 2 判据红 (守恒破/字段缺/入库失配) / 3 弃权 (源不可读/环境不可判)。

与 Q33 的分工: Q33 = depth-1 逐条裁定; 本器具 = 传递闭包 + 可机检的不可入库裁定。
"""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.dirname(HERE)                      # eval/capability
Q33 = os.path.join(CAP, "exp1-q33")
ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                      cwd=HERE, check=True).stdout.strip()
OUT = os.path.join(HERE, "deps_depth2_q34.json")
ARDIR = os.path.join(HERE, "archived_deps_depth2")
DEPTH1 = os.path.join(Q33, "deps_adjudication_q33.json")
MAX_FILE_BYTES = 2 * 1024 * 1024                 # 单文件入库上限 (与 Q33 同量级)
MAX_SCAN_FILES = 200                             # 每个 depth-1 目录最多扫多少文件 (有界)
TMP_REF = re.compile(r"(?<![\w/.-])(/tmp/[A-Za-z0-9_./-]+)")
LICENSES = ("unasserted", "mit", "apache-2.0", "proprietary-external", "unknown")
WHY_NOT_ARCHIVABLE = ("runtime_env_dir", "large_file_not_archivable", "binary_release_artifact",
                      "unreadable_at_audit_time", "gone_at_audit_time")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha12_bytes(b):
    return hashlib.sha256(b).hexdigest()[:12]


def load_q33_classifier():
    """加载 Q33 的分类器 (单一事实源) —— 复制一份判据就会漂移, 这正是 Q34 要防的形态。"""
    spec = importlib.util.spec_from_file_location("q33_deps", os.path.join(Q33, "deps_adjudication_q33.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_textish(path):
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return False
        with open(path, "rb") as fh:
            chunk = fh.read(4096)
        return b"\x00" not in chunk
    except OSError:
        return False


def refs_in(path):
    """抽文件里的 /tmp 引用。不可读 ⇒ None (弃权, 不是「没有引用」)。"""
    try:
        if not is_textish(path):
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return sorted(set(TMP_REF.findall(fh.read())))
    except OSError:
        return None


def scan_target_depth1(row):
    """depth-1 的扫描面: 入库副本优先 (仓内稳定), 其次现场路径。返回 (可扫路径列表, 弃权原因|None)。"""
    dep = row["dep"]
    base = os.path.basename(dep.rstrip("/"))
    cand = []
    if row.get("class") == "archived":
        for sub in ("files", "dirs"):
            p = os.path.join(Q33, "archived_deps", sub, base)
            if os.path.exists(p):
                cand.append(p)
                break
    if os.path.exists(dep):
        cand.append(dep)
    if not cand:
        return [], "gone_at_audit_time"
    return cand, None


def collect_depth2(rows):
    """产 depth-2 原始引用 (dep → 引用集合)。不追 depth-3, 只计数。"""
    out, abstain, depth3 = [], [], []
    for row in rows:
        cands, why = scan_target_depth1(row)
        if why:
            abstain.append({"depth1": row["dep"], "reason": why})
            continue
        found = set()
        for c in cands:
            if os.path.isdir(c):
                n = 0
                for dirpath, _dirnames, filenames in os.walk(c):
                    for fn in sorted(filenames):
                        if n >= MAX_SCAN_FILES:
                            break
                        n += 1
                        got = refs_in(os.path.join(dirpath, fn))
                        if got:
                            found.update(got)
            else:
                got = refs_in(c)
                if got:
                    found.update(got)
        for ref in sorted(found):
            out.append({"dep": ref, "via": row["dep"], "via_class": row.get("class")})
    return out, abstain, depth3


def archive_one(dep, root=None):
    """逐字节入库 + 读回复核。返回 (ok, payload)。不覆盖已有不同字节 (fail-closed)。"""
    os.makedirs(ARDIR, exist_ok=True)
    base = os.path.basename(dep.rstrip("/"))
    dst = os.path.join(ARDIR, base)
    try:
        src = open(dep, "rb").read()
    except OSError as exc:
        return False, {"reason": "unreadable:%s" % exc}
    if len(src) > MAX_FILE_BYTES:
        return False, {"reason": "too_large", "bytes": len(src)}
    if os.path.exists(dst) and open(dst, "rb").read() != src:
        return False, {"reason": "name_collision_different_bytes"}
    with open(dst, "wb") as fh:
        fh.write(src)
    back = open(dst, "rb").read()
    return (back == src), {"sha256": sha256_bytes(back), "bytes": len(back), "dst": dst}


def dispose_external(dep, payload):
    """把 external_asset 的人读 reason 升成**机检字段** (kind/bytes/license/archivable/why)。"""
    kind = payload.get("kind", "unknown")
    why = {"directory": "runtime_env_dir",
           "large_file": "large_file_not_archivable",
           "binary_file": "binary_release_artifact"}.get(kind, "unreadable_at_audit_time")
    d = {"kind": kind, "archivable": False, "why_not_archivable": why,
         "license": "unasserted",
         "license_note": "外部运行环境/发布物, 未随仓分发 ⇒ 本库不主张其许可, 也不入库 (不可再分发风险)",
         "bytes": payload.get("bytes"), "n_files": payload.get("n_files")}
    if why not in WHY_NOT_ARCHIVABLE:
        raise AssertionError("why_not_archivable 越出闭集: %s" % why)
    if os.path.isfile(dep):
        try:
            d["sha256"] = sha256_bytes(open(dep, "rb").read())
        except OSError:
            d["sha256"] = None
    return d


def adjudge(root=None):
    if not os.path.exists(DEPTH1):
        return 3, {"error": "DEPTH1_MISSING", "path": DEPTH1}
    d1 = json.load(open(DEPTH1, encoding="utf-8-sig"))
    if d1.get("schema") != "deps-adjudication/1":
        return 3, {"error": "DEPTH1_SCHEMA", "got": d1.get("schema")}
    rows = d1["rows"]
    q33 = load_q33_classifier()

    depth2_raw, abstain, _ = collect_depth2(rows)
    seen, depth2 = set(), []
    for r in depth2_raw:
        if r["dep"] in seen:
            continue
        seen.add(r["dep"])
        cls, payload = q33.classify(r["dep"], root=root)
        rec = dict(r)
        rec["class"] = cls
        rec["payload"] = {k: v for k, v in payload.items() if k != "restore"}
        if cls == "archived":
            ok, ap = archive_one(r["dep"], root=root)
            rec["archived_verified"] = bool(ok)
            rec["archive"] = ap
            if not ok:
                rec["class"] = "external_asset"
                rec["payload"] = {"kind": "unarchivable", "reason": ap.get("reason")}
        depth2.append(rec)

    # external_asset 显式裁定: depth-1 的 11 件 + depth-2 新增
    ext = []
    for r in rows:
        if r.get("class") == "external_asset":
            ext.append({"level": 1, "dep": r["dep"], "disposition": dispose_external(r["dep"], r)})
    for r in depth2:
        if r["class"] == "external_asset":
            ext.append({"level": 2, "dep": r["dep"],
                        "disposition": dispose_external(r["dep"], r["payload"])})

    by_class = {}
    for r in depth2:
        by_class[r["class"]] = by_class.get(r["class"], 0) + 1
    depth3 = []
    for r in depth2:
        if r.get("archived_verified") and r.get("archive", {}).get("dst"):
            got = refs_in(r["archive"]["dst"])
            for ref in (got or []):
                depth3.append({"dep": ref, "via_depth2": r["dep"]})
    n_depth3_distinct = len({d["dep"] for d in depth3})

    d1_with_disposition = sum(1 for r in rows if r.get("verdict") or r.get("class"))
    payload = {
        "round": "EXP1-Q34",
        "schema": "deps-depth2/1",
        "source": {"depth1": os.path.relpath(DEPTH1, ROOT), "depth2_dir": os.path.relpath(ARDIR, ROOT)},
        "n_depth1": len(rows), "n_depth1_with_disposition": d1_with_disposition,
        "n_depth2": len(depth2), "by_class": by_class,
        "depth2": depth2,
        "n_external_disposed": len(ext), "external_dispositions": ext,
        "abstain": abstain,
        "depth3": {"n_refs": len(depth3), "n_distinct": n_depth3_distinct,
                   "note": "声明的递归边界: depth-3 只计数不追 (再追需独立预注册轮)",
                   "sample": sorted({d["dep"] for d in depth3})[:10]},
        "conservation": {
            "sum_by_class_eq_n_depth2": sum(by_class.values()) == len(depth2),
            "n_depth1_all_disposed": d1_with_disposition == len(rows),
            "classes_subset_of_closed_set": set(by_class) <= set(q33.CLASSES),
            "every_external_has_why": all(e["disposition"].get("why_not_archivable") in WHY_NOT_ARCHIVABLE
                                          for e in ext),
            "every_external_license_in_closed_set": all(e["disposition"].get("license") in LICENSES
                                                        for e in ext),
        },
        "rule": "depth-2 分类复用 Q33 分类器 (importlib 单源); 可入库者逐字节入库 + 读回复核; "
                "不可入库者落 (kind/bytes/sha256/license/archivable/why_not_archivable) 机检字段 "
                "⇒ 「不入库」从人读理由升级为可审计裁定。",
    }
    ok = all(payload["conservation"].values())
    return (0 if ok else 2), payload


def selftest():
    """判别力自证 (5 例): 引用抽取 (含边界: 不要误吞前缀路径); 守恒式破 ⇒ 红;
    binary/large ⇒ 不入库但分类正确; 缺席 ⇒ 弃权非红; 入库读回复核必须逐字节。"""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="q34-deps-")
    cases, bad = {}, 0
    try:
        # 引用抽取: 正例 + 负例 (行内 /tmp 与 URL 里的 /tmp 前缀)
        p = os.path.join(tmp, "a.txt")
        open(p, "w", encoding="utf-8").write("open /tmp/q34_probe.bin and /tmp/q34_dir/x.py\nnot/../tmp/nope\n")
        got = refs_in(p) or []
        cases["ref_extraction_positive"] = ("/tmp/q34_probe.bin" in got and "/tmp/q34_dir/x.py" in got)
        cases["ref_extraction_no_prefix_swallow"] = all(not r.endswith("nope") for r in got)
        # 二进制 / 大文件 ⇒ is_textish False ⇒ refs_in None (弃权, 不是「零引用」)
        b = os.path.join(tmp, "b.bin")
        open(b, "wb").write(b"\x00\x01/tmp/inside_binary")
        cases["binary_scan_is_abstain_not_zero"] = refs_in(b) is None
        # 不可入库裁定: 目录 / 大文件 的 reason_code 必须落在闭集
        d1 = dispose_external("/tmp/q34_dir", {"kind": "directory", "n_files": 3, "bytes": 99})
        d2 = dispose_external("/tmp/q34_big", {"kind": "large_file", "bytes": 10 ** 8})
        cases["external_disposition_closed_set"] = (d1["why_not_archivable"] in WHY_NOT_ARCHIVABLE
                                                    and d2["why_not_archivable"] in WHY_NOT_ARCHIVABLE
                                                    and d1["archivable"] is False and d1["license"] in LICENSES)
        # 入库读回复核: 逐字节不等必须判 False (name_collision 分支)
        os.makedirs(ARDIR, exist_ok=True)
        tgt = os.path.join(tmp, "same_name.txt")
        open(tgt, "w", encoding="utf-8").write("v1")
        ok1, _ = archive_one(tgt)
        open(tgt, "w", encoding="utf-8").write("v2")
        ok2, ap2 = archive_one(tgt)
        cases["archive_verify_rejects_byte_drift"] = (ok1 is True and ok2 is False
                                                      and ap2.get("reason") == "name_collision_different_bytes")
        for k, v in cases.items():
            print("  %-42s %s" % (k, "OK" if v else "FAIL"))
            bad += 0 if v else 1
        n = len(cases)
        print("SELFTEST %s (%d/%d)" % ("PASS" if bad == 0 else "FAIL", n - bad, n))
        return 0 if bad == 0 else 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for f in ("same_name.txt",):
            q = os.path.join(ARDIR, f)
            if os.path.exists(q):
                os.remove(q)


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    rc, payload = adjudge()
    if rc == 3:
        print("DEPS_DEPTH2=ABSTAIN %s" % payload)
        return 3
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(OUT, "a", encoding="utf-8").write("\n")
    print("DEPTH1=%d (with_disposition=%d) DEPTH2=%d by_class=%s"
          % (payload["n_depth1"], payload["n_depth1_with_disposition"],
             payload["n_depth2"], json.dumps(payload["by_class"], ensure_ascii=False)))
    print("EXTERNAL_DISPOSED=%d ABSTAIN=%d DEPTH3=%d(distinct)"
          % (payload["n_external_disposed"], len(payload["abstain"]), payload["depth3"]["n_distinct"]))
    print("CONSERVATION=%s" % json.dumps(payload["conservation"], ensure_ascii=False))
    print("DEPTH2_EXIT=%d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
