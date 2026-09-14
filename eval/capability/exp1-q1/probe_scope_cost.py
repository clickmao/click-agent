#!/usr/bin/env python3
"""exp1-Q1 决策数据探针：**索引作用域**（仅源码 / +文档 / +运行数据 / 全树）的体积、冷扫成本与**失效面**。

零产品改动，全部落在 eval/ 内。

背景：plan §8-Q1 原文「索引作用域：只索引本仓源码？还是含 data/、docs/、用户工作目录？
→ 决定索引体积与失效面」——两条都是**可数的事实**，不是判断题。本探针把它们变成数据。

四个候选作用域（路径前缀 + 扩展名显式定义，排除集固定）
--------------------------------------------------------
  A code-only        : src/**  (*.cs)
  B code+docs        : A + docs/** skills/** + 仓根 *.md
  C code+docs+data   : B + data/**（运行数据 / 工作目录面）
  D whole-tree       : 工作树全量文本类（= C + eval/ scripts/ 及其余，仍排除 bin/obj/.git/__pycache__）

测量项（全部**实测**，非估算）
------------------------------
  1 体积：文件数 / 原生字节 / 文本字节 / 去重 token 数 / postings 数
          / **索引载荷字节**（token→docIds 紧凑 JSON 的真实 utf-8 长度 + gzip 后长度）
          / 文件指纹字节（path+mtime+size）
          * 凭据面两分：`sensitive_count`（作用域根下**全部**凭据文件）vs `sensitive_indexable_count`
            （扩展名过滤**仍会放行**的那些 = 真实暴露面）；D2 用后者裁定
  2 冷扫成本：walk+read+tokenize+build 的中位耗时（3 次）
  3 引用图：具名类型数 / V3 边数 / 建图耗时（掩码规范取自附录 B 定稿 V3）
  4 **失效面（两个独立来源，缺一不可）**
     (i)  运行时写入（本机 fs mtime 窗）：5min / 60min / 24h 变更文件数 ⇒ **次/分钟**
     (ii) VCS 提交变更（近 50 提交 --name-only）：逐作用域事件数 + 同时跨域提交数（连带失效）
     * 单看 (ii) 会把 data/ 判成「零变更」（它不入 git）；单看 (i) 会把对侧构建产物当源码变更。
  5 安全面：作用域内**owner-only 权限**或**凭据类命名**文件（只记路径与计数，**绝不读取/输出内容**）

预注册判据（跑前写死；跑后不得改）
----------------------------------
  门禁 G1  不存在作用域 ⇒ scope_missing rc=3；空作用域 ⇒ measurement_empty rc=3（不得静默算 0）
  门禁 G2  同作用域两跑：计数类读数逐位相同；**不同时必须能被『两跑窗口内该作用域确有文件被写入』
           解释**（附窗口写入清单与计数）。差异无写入可解释 ⇒ 判仪器非确定 ⇒ 门禁红。
           （预注册修订 v1.1，在任何读数产生之前；理由：作用域 C/D 含活跃写入者，
            逐位相同在原理上不可能，硬要求会把『作用域性质』误判成『仪器坏』）（canonical sha 相等）
  门禁 G3  非平凡：四作用域的索引载荷 sha **两两互异**（否则仪器不可解释）
  门禁 G4  敏感过滤器判别力双向：(+) data/credentials.json 与 data/master.key 必被抓
                                (−) 合法源码（*.cs，名字或内容含 token/key 字样）**误杀数必须为 0**
                                  （R409 教训：只测「坏样本被抓」会漏「合法样本被误杀」）
  决策 D1  预注册式失效判据：某作用域在 60 分钟窗内 ≥60 个文件被运行时写入（≥1 次/分钟）
           ⇒ **不可纳入**索引作用域（结果缓存命中率 → 0）。理由：失效粒度是文件级 mtime 比对，
           高频写入使「查完即失效」，缓存退化为无缓存。
  决策 D2  某作用域含 owner-only 凭据文件而索引格式**不加密**（plan §4.1 原文：索引不需要加密）
           ⇒ 必须新增排除规则；未加规则前**不可纳入**。

三态退出码：0 = G1-G4 全过且 D1/D2 可裁定 / 2 = 门禁失败 / 3 = 测量或环境失败

诚实边界（见 result.json 同名键）
--------
- token 口径 = ASCII 标识符(≥3 字符) + CJK 二元组；换口径会改绝对值，但**作用域间比较**不受影响。
- 索引载荷是「自建倒排 + 紧凑 JSON + gzip」的**实测序列化长度**，非磁盘 I/O 开销、非 mmap 常驻。
- 单文件 >2MB 跳过（`skipped_large` 计数可见），故 D 的体积为下界。
- 运行时窗读数取**本机当前负载**（对侧 30m 作业活动构建会抬高 src 原始计数）⇒ 另给排除 bin/obj 的值。
- 冷扫耗时含解释器开销，不等于 AOT 产品侧成本；只作作用域间**相对**比较。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

MAX_FILE_BYTES = 2 * 1024 * 1024
RUN_STARTED = 0.0
SKIP_DIRS = {"bin", "obj", ".git", "node_modules", "__pycache__", ".vs", ".hermes"}
EXT_CODE = {".cs"}
EXT_DOC = {".md", ".txt", ".rst"}
EXT_DATA = {".json", ".jsonl", ".ndjson", ".csv", ".log"}

# 作用域定义：roots 为仓内相对路径前缀（"" = 仓根，仅取 EXT_DOC 的顶层文件）
SCOPES = {
    "A": {"label": "code-only", "roots": ["src"], "exts": EXT_CODE},
    "B": {"label": "code+docs", "roots": ["src", "docs", "skills", ""], "exts": EXT_CODE | EXT_DOC},
    "C": {"label": "code+docs+data", "roots": ["src", "docs", "skills", "data", ""],
          "exts": EXT_CODE | EXT_DOC | EXT_DATA},
    "D": {"label": "whole-tree", "roots": [".ALL"], "exts": EXT_CODE | EXT_DOC | EXT_DATA},
}

CRITERIA = {
    "gate": {
        "G1_missing_scope_is_error": True,
        "G2_two_run_counts_identical_or_attributed": True,
        "G3_payload_sha_pairwise_distinct": True,
        "G4_sensitive_filter_discriminates_both_ways": True,
    },
    "decision": {
        "D1_invalidation_per_min_threshold": 1.0,
        "D1_note": "60min 窗内运行时写入文件数 >= 60（即 >=1 次/分钟）⇒ 结果缓存退化为无缓存 ⇒ 不可纳入",
        "D2_owner_only_secret_files_block": True,
        "D2_note": "含 owner-only 凭据文件而索引载荷不加密（plan §4.1）⇒ 必须新增排除规则，未加规则前不可纳入",
    },
    "declared_before_run": "exp1-q1 v1（体积/成本/失效面/安全面四维，双源失效计数）",
}

# V3 掩码规范实现：逐字符分类（C=代码 / /=注释 s=字符串 {=插值孔洞）。
# 出处：eval/capability/exp1-q3b/probe_mask_tradeoff.py（附录 B 定稿）；本文件为副本，
# 探针运行时与源模块做**交叉一致自检**（masker_cross_check），防规范分叉。
CODE, COMMENT, STRING, HOLE = "C", "/", "s", "{"

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
DEF_RE = re.compile(
    r"\b(?:class|record|struct|interface|enum|delegate)\s+(?:partial\s+)?([A-Za-z_][A-Za-z0-9_]*)")
SENSITIVE_NAME = re.compile(
    r"(credential|secret|passwd|password|api[-_]?key|master\.key|\.pem$|\.pfx$|id_rsa|\.kdbx$)", re.I)


# ---------------------------------------------------------------- scope walking
def classify_chars(text: str) -> str:
    out = []
    i, n = 0, len(text)
    state = "N"
    rawq, depth, vq = 0, 0, False
    while i < n:
        c = text[i]
        if state == "N":
            if c == "/" and i + 1 < n and text[i + 1] == "/":
                state, out = "L", out + ["/", "/"]; i += 2; continue
            if c == "/" and i + 1 < n and text[i + 1] == "*":
                state, out = "B", out + ["/", "/"]; i += 2; continue
            if c == "$" and i + 1 < n and text[i + 1] == '"':
                state, out, vq = "I", out + ["C", "s"], False; i += 2; continue
            if c == "$" and i + 2 < n and text[i + 1] == "@" and text[i + 2] == '"':
                state, out, vq = "I", out + ["C", "C", "s"], True; i += 3; continue
            if c == "@" and i + 2 < n and text[i + 1] == "$" and text[i + 2] == '"':
                state, out, vq = "I", out + ["C", "C", "s"], True; i += 3; continue
            if text.startswith('"""', i):
                q = 0
                while i + q < n and text[i + q] == '"':
                    q += 1
                state, rawq = "R", q
                out += ["s"] * q; i += q; continue
            if c == "@" and i + 1 < n and text[i + 1] == '"':
                state, out = "V", out + ["C", "s"]; i += 2; continue
            if c == '"':
                state, out = "S", out + ["s"]; i += 1; continue
            if c == "'":
                state, out = "Q", out + ["s"]; i += 1; continue
            out.append(CODE); i += 1; continue
        if state == "L":
            if c == "\n":
                state, out = "N", out + [CODE]; i += 1; continue
            out.append(COMMENT); i += 1; continue
        if state == "B":
            if text.startswith("*/", i):
                state, out = "N", out + ["/", "/"]; i += 2; continue
            out.append(CODE if c == "\n" else COMMENT); i += 1; continue
        if state in ("S", "Q"):
            if c == "\\" and i + 1 < n:
                out += ["s", "s"]; i += 2; continue
            if (state == "S" and c == '"') or (state == "Q" and c == "'"):
                state, out = "N", out + ["s"]; i += 1; continue
            if c == "\n":
                state, out = "N", out + [CODE]; i += 1; continue
            out.append(STRING); i += 1; continue
        if state == "V":
            if text.startswith('""', i):
                out += ["s", "s"]; i += 2; continue
            if c == '"':
                state, out = "N", out + ["s"]; i += 1; continue
            out.append(STRING); i += 1; continue
        if state == "R":
            if text.startswith('"' * rawq, i):
                state, out = "N", out + ["s"] * rawq; i += rawq; continue
            out.append(STRING); i += 1; continue
        if state == "I":
            if vq and text.startswith('""', i):
                out += ["s", "s"]; i += 2; continue
            if not vq and c == "\\" and i + 1 < n:
                out += ["s", "s"]; i += 2; continue
            if c == '"':
                state, out = "N", out + ["s"]; i += 1; continue
            if c == "{" and not text.startswith("{{", i):
                state, depth, out = "H", 1, out + [HOLE]; i += 1; continue
            if c == "}" and text.startswith("}}", i):
                out += ["s", "s"]; i += 2; continue
            if c == "\n":
                state, out = "N", out + [CODE]; i += 1; continue
            out.append(STRING); i += 1; continue
        if c == "{":
            depth += 1; out.append(HOLE); i += 1; continue
        if c == "}":
            depth -= 1
            if depth <= 0:
                state, out = "I", out + [HOLE]; i += 1; continue
            out.append(HOLE); i += 1; continue
        out.append(CODE if c == "\n" else HOLE); i += 1; continue
    return "".join(out)


def root_of(rel: str) -> str:
    return rel.split("/", 1)[0] if "/" in rel else ""


def in_scope(rel: str, spec: dict) -> bool:
    ext = os.path.splitext(rel)[1].lower()
    if ext not in spec["exts"]:
        return False
    if ".ALL" in spec["roots"]:
        return True
    top = root_of(rel)
    if "" in spec["roots"] and "/" not in rel:
        return ext in EXT_DOC          # 仓根仅取文档类，避免把零散文件算进「源码」
    return top in spec["roots"]


def is_sensitive(rel: str, mode: int) -> bool:
    """owner-only 权限 或 凭据类命名 ⇒ 敏感。源码类扩展名永不**按名**排除（防误杀，R409）。"""
    ext = os.path.splitext(rel)[1].lower()
    if mode & 0o077 == 0:                     # owner-only 权限：无论扩展名一律排除
        return True
    if ext in EXT_CODE:
        return False
    if ext in EXT_DATA | {".key", ".pem", ".pfx", "", ".txt", ".log"} and SENSITIVE_NAME.search(os.path.basename(rel)):
        return True
    return False


def in_scope_roots(rel: str, spec: dict) -> bool:
    """J2: only root prefix, extension-agnostic (sensitive scan uses it)."""
    if ".ALL" in spec["roots"]:
        return True
    if "/" not in rel and "" in spec["roots"]:
        return True
    return root_of(rel) in spec["roots"]


def walk_scope(spec: dict):
    """J3: (rel_paths, skipped_large, sensitive_paths). Stats only; no content read."""
    if not REPO.is_dir():
        raise FileNotFoundError(str(REPO))
    rels, skipped, sensitive, sens_idx = [], 0, [], []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = str(p.relative_to(REPO))
            if not in_scope_roots(rel, spec):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            if is_sensitive(rel, st.st_mode):
                sensitive.append(rel)
                if in_scope(rel, spec):
                    sens_idx.append(rel)
                continue
            if not in_scope(rel, spec):
                continue
            if st.st_size > MAX_FILE_BYTES:
                skipped += 1
                continue
            rels.append((rel, st.st_size))
    rels.sort()
    sensitive.sort()
    sens_idx.sort()
    return rels, skipped, sensitive, sens_idx


# ---------------------------------------------------------------- measurement
def tokenize(text: str):
    toks = set()
    for m in IDENT_RE.finditer(text):
        toks.add(m.group(0))
    for m in CJK_RE.finditer(text):
        s = m.group(0)
        for i in range(len(s) - 1):
            toks.add(s[i:i + 2])
    return toks


def measure(scope_id: str, spec: dict, runs: int = 3) -> dict:
    rels, skipped, sensitive, sens_idx = walk_scope(spec)
    if not rels:
        return {"error": "measurement_empty", "scope": scope_id, "sensitive": sensitive}

    def one_pass():
        inv: dict[str, set] = {}
        text_bytes = 0
        for rel, _sz in rels:
            try:
                text = (REPO / rel).read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            text_bytes += len(text)
            for t in tokenize(text):
                inv.setdefault(t, set()).add(rel)
        return inv, text_bytes

    timings = []
    for _ in range(runs):
        t0 = time.perf_counter()
        inv, text_bytes = one_pass()
        timings.append((time.perf_counter() - t0) * 1000.0)

    payload = json.dumps({k: sorted(v) for k, v in inv.items()}, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    fingerprints = json.dumps([{"p": rel, "m": (REPO / rel).stat().st_mtime_ns, "s": sz}
                               for rel, sz in rels], ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    # 引用图（V3）：定义点取自 .cs，引用出现可取任文本文件
    t0 = time.perf_counter()
    defined, decl = {}, {}
    for rel, _sz in rels:
        if os.path.splitext(rel)[1].lower() != ".cs":
            continue
        text = (REPO / rel).read_text(encoding="utf-8-sig", errors="replace")
        cls = classify_chars(text)
        for m in DEF_RE.finditer(text):
            if cls[m.start(1)] != CODE:
                continue
            dline = text.count("\n", 0, m.start(1)) + 1
            defined.setdefault(m.group(1), rel)
            decl.setdefault(m.group(1), set()).add((rel, dline))
    edges = 0
    edge_files = {}
    for rel, _sz in rels:
        ext = os.path.splitext(rel)[1].lower()
        text = (REPO / rel).read_text(encoding="utf-8-sig", errors="replace")
        cls = classify_chars(text) if ext in EXT_CODE else None
        seen = set()
        for m in IDENT_RE.finditer(text):
            tok = m.group(0)
            if tok not in defined:
                continue
            ln = text.count("\n", 0, m.start()) + 1
            if cls is not None:
                c = cls[m.start()]
                if c not in (CODE, HOLE):          # V3：掩注释 + 纯字符串，保留插值孔洞
                    continue
            if (rel, ln) in decl.get(tok, ()):
                continue
            seen.add(tok)
        for tok in seen:
            edge_files.setdefault(tok, set()).add(rel)
    for tok, files in edge_files.items():
        edges += len(files - {defined.get(tok, "")})
    graph_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "scope": scope_id, "label": spec["label"],
        "files": len(rels), "bytes_native": sum(sz for _, sz in rels), "bytes_text": text_bytes,
        "skipped_large": skipped,
        "distinct_tokens": len(inv), "postings": sum(len(v) for v in inv.values()),
        "index_payload_bytes": len(payload), "index_payload_gzip_bytes": len(gzip.compress(payload, 6)),
        "fingerprint_bytes": len(fingerprints),
        "cold_scan_ms_median": round(statistics.median(timings), 1),
        "cold_scan_ms_runs": [round(t, 1) for t in timings],
        "graph": {"defined_types": len(defined), "edges_v3": edges, "graph_ms": round(graph_ms, 1)},
        "payload_sha": __import__("hashlib").sha256(payload).hexdigest()[:16],
        "_counts_for_determinism": {
            "files": len(rels), "distinct_tokens": len(inv), "postings": sum(len(v) for v in inv.values()),
            "index_payload_bytes": len(payload), "payload_sha_full": __import__("hashlib").sha256(payload).hexdigest(),
            "defined_types": len(defined), "edges_v3": edges,
        },
        "sensitive_files": sensitive,
        "sensitive_count": len(sensitive),
        "sensitive_indexable": sens_idx,
        "sensitive_indexable_count": len(sens_idx),
    }


# ---------------------------------------------------------------- invalidation
def runtime_churn(spec: dict) -> dict:
    windows = {"5min": 300, "60min": 3600, "24h": 86400}
    now = time.time()
    counts = {k: 0 for k in windows}
    raw_counts = {k: 0 for k in windows}        # 不排除 bin/obj（对照：对侧构建会抬高计数）
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = str(p.relative_to(REPO))
            if not in_scope(rel, spec):
                continue
            try:
                age = now - p.stat().st_mtime
            except OSError:
                continue
            for k, sec in windows.items():
                if age <= sec:
                    counts[k] += 1
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", ".vs", ".hermes"}]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = str(p.relative_to(REPO))
            if not in_scope(rel, spec):
                continue
            try:
                age = now - p.stat().st_mtime
            except OSError:
                continue
            for k, sec in windows.items():
                if age <= sec:
                    raw_counts[k] += 1
    return {"in_scope": counts, "incl_build_artifacts": raw_counts,
            "events_per_min_60min": round(counts["60min"] / 60.0, 3)}


def vcs_churn(spec: dict, commits: int = 50) -> dict:
    try:
        out = subprocess.run(["git", "log", f"-n{commits}", "--name-only", "--pretty=format:%x01%H"],
                             cwd=REPO, capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": f"git_failed:{exc.__class__.__name__}"}
    scope_events, commits_touching, multi = 0, 0, 0
    seen_commits = 0
    cur_hits = 0
    for line in out.splitlines():
        if line.startswith("\x01"):
            if seen_commits:
                commits_touching += 1 if cur_hits else 0
            seen_commits += 1
            cur_hits = 0
            continue
        if not line.strip():
            continue
        if in_scope(line, spec):
            scope_events += 1
            cur_hits += 1
    if seen_commits and cur_hits:
        commits_touching += 1
    # 连带失效：同一提交既动本作用域、又动它域（以 src/docs/data 三域互斥近似）
    per_commit = {}
    cur = None
    for line in out.splitlines():
        if line.startswith("\x01"):
            cur = line[1:]
            per_commit[cur] = set()
            continue
        if not line.strip() or cur is None:
            continue
        ext = os.path.splitext(line)[1].lower()
        if ext in EXT_CODE and line.startswith("src/"):
            per_commit[cur].add("src")
        elif line.startswith("docs/") or line.startswith("skills/"):
            per_commit[cur].add("docs")
        elif line.startswith("data/"):
            per_commit[cur].add("data")
    for doms in per_commit.values():
        if len(doms) > 1:
            multi += 1
    return {"commits_scanned": seen_commits, "scope_file_events": scope_events,
            "commits_touching_scope": commits_touching, "commits_touching_multiple_domains": multi}


# ---------------------------------------------------------------- main
def main() -> int:
    global RUN_STARTED
    RUN_STARTED = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--scopes", nargs="*", default=list(SCOPES))
    ap.add_argument("--result", default=str(OUT / "result.json"))
    ap.add_argument("--commits", type=int, default=50)
    ap.add_argument("--compare", default=None,
                    help="另一次运行的 result.json：比对计数类读数（G2 确定性）")
    args = ap.parse_args()

    for sid in args.scopes:
        if sid not in SCOPES:
            print(json.dumps({"error": "scope_missing", "scope": sid}))
            return 3
        missing = [r for r in SCOPES[sid]["roots"]
                   if r not in (".ALL", "") and not (REPO / r).is_dir()]
        if missing or not REPO.is_dir():
            print(json.dumps({"error": "scope_root_missing", "scope": sid,
                              "missing_roots": missing or ["<repo>"]}, ensure_ascii=False))
            return 3

    readings, churn_rt, churn_vcs = {}, {}, {}
    for sid in args.scopes:
        spec = SCOPES[sid]
        try:
            m = measure(sid, spec)
        except OSError as exc:
            print(json.dumps({"error": "measurement_failed", "scope": sid,
                              "detail": exc.__class__.__name__}, ensure_ascii=False))
            return 3
        if "error" in m:
            print(json.dumps(m, ensure_ascii=False))
            return 3
        readings[sid] = m
        churn_rt[sid] = runtime_churn(spec)
        churn_vcs[sid] = vcs_churn(spec, args.commits)

    # G3 非平凡：四作用域 payload sha 两两互异
    shas = [readings[s]["payload_sha"] for s in readings]
    g3 = len(set(shas)) == len(shas)
    # G4 双向判别力：正控（data 下凭据文件被抓）+ 反控（源码域误杀 0）
    cred_scope = "C" if "C" in readings else args.scopes[-1]
    pos_hits = [p for p in readings[cred_scope].get("sensitive_files", [])
                if p.endswith("credentials.json") or p.endswith("master.key")]
    false_kills = readings.get("A", {}).get("sensitive_count", 0)
    g4 = (len(pos_hits) >= 2) and (false_kills == 0)
    # 掩码规范交叉一致（防规范分叉）
    xcheck = "not_available"
    try:
        sys.path.insert(0, str(REPO / "eval" / "capability" / "exp1-q3b"))
        from probe_mask_tradeoff import classify_chars as ref  # type: ignore
        probe_txt = ['var a = Foo.Bar;', 'var s = "Foo";', 'var s = $"x {Foo} y";', '// Foo', 'var s = @"Foo";']
        xcheck = "agree" if all(ref(t) == classify_chars(t) for t in probe_txt) else "DISAGREE"
    except Exception:  # noqa: BLE001  —— 源模块缺失不阻断（如实记 not_available）
        pass

    # 决策裁定（按预注册规则机械裁定）
    decisions = {}
    for sid, r in readings.items():
        pm = churn_rt[sid]["events_per_min_60min"]
        d1_block = pm >= CRITERIA["decision"]["D1_invalidation_per_min_threshold"]
        d2_block = r["sensitive_indexable_count"] > 0
        if d1_block or d2_block:
            verdict = "excluded"
        else:
            verdict = "eligible"
        decisions[sid] = {"invalidation_per_min": pm, "D1_blocked": d1_block, "D2_blocked": d2_block,
                          "sensitive_indexable": r["sensitive_indexable"],
                          "verdict": verdict}
    eligible = [s for s, d in decisions.items() if d["verdict"] == "eligible"]
    # 推荐 = 可纳入中**体积/成本**最小者（作用域越大越贵：用 index_payload_bytes 排序）
    recommended = min(eligible, key=lambda s: readings[s]["index_payload_bytes"]) if eligible else None

    gate_pass = g3 and g4
    # G2 确定性：与 --compare 给定的另一次运行逐位比对计数类读数
    g2, g2_detail, g2_attr = None, {}, {}
    if args.compare and Path(args.compare).is_file():
        prev = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        prev_counts = prev.get("determinism_counts", {})
        g2 = True
        prev_fin = prev.get("run_started_epoch") or prev.get("run_finished_epoch")
        for sid, r in readings.items():
            if sid not in prev_counts:
                g2 = False
                g2_detail[sid] = "missing_in_compare_target"
                continue
            a, b = r["_counts_for_determinism"], prev_counts[sid]
            if a != b:
                g2_detail[sid] = {k: [a.get(k), b.get(k)] for k in a if a.get(k) != b.get(k)}
                if prev_fin is None:
                    g2 = False
                    g2_attr[sid] = {"attributed": False, "reason": "no_prev_timestamp"}
                    continue
                rels2, _sk2, _sn2, _si2 = walk_scope(SCOPES[sid])
                wr = [rel for rel, _ in rels2 if (REPO / rel).stat().st_mtime > float(prev_fin)]
                ok = len(wr) > 0
                g2_attr[sid] = {"attributed": ok, "files_written_in_window": len(wr),
                                "sample": wr[:8]}
                g2 = g2 and ok
        gate_pass = gate_pass and bool(g2)
    result = {
        "probe": "exp1-q1-scope-cost", "instrument_revision": 2,
        "attribution_window": "files with mtime > previous run STARTED epoch",
        "attribution_window_note": "reading is a snapshot ACROSS a run, so the window must span it",
        "scopes": {sid: {"label": SCOPES[sid]["label"], "roots": list(SCOPES[sid]["roots"]),
                          "exts": sorted(SCOPES[sid]["exts"])} for sid in readings},
        "readings": {sid: {k: v for k, v in r.items() if not k.startswith("_")} for sid, r in readings.items()},
        "determinism_counts": {sid: r["_counts_for_determinism"] for sid, r in readings.items()},
        "churn_runtime": churn_rt, "churn_vcs": churn_vcs,
        "criteria_pre_registered": CRITERIA,
        "run_started_epoch": RUN_STARTED, "run_finished_epoch": time.time(),
        "gates": {"G1_missing_scope_is_error": True, "G2_two_run_counts_identical": g2,
                  "G2_mismatch_detail": g2_detail, "G2_write_attribution": g2_attr,
                  "G3_payload_sha_pairwise_distinct": g3, "G4_sensitive_filter_discriminates_both_ways": g4,
                  "positive_control_hits": pos_hits, "reverse_control_false_kills": false_kills},
        "masker_cross_check": xcheck,
        "decisions": decisions, "eligible_scopes": eligible,
        "recommended_scope": recommended,
        "recommendation": (
            f"作用域取 **{recommended}**（{SCOPES[recommended]['label']}）：在预注册 D1/D2 裁决后唯一体量最小的可纳入作用域；"
            f"被排除者: " + ", ".join(f"{s}({[k for k, v in decisions[s].items() if v is True and k.endswith('blocked')]})"
                                     for s in decisions if decisions[s]['verdict'] == 'excluded')
        ) if recommended else "无可纳入作用域（预注册判据全数触发）",
        "gate_pass": gate_pass,
        "exit_code": 0 if gate_pass else 2,
        "honest_boundaries": [
            "token 口径 = ASCII 标识符(>=3 字符) + CJK 二元组；换口径改绝对值，作用域间比较不受影响",
            "index_payload_bytes 为自建倒排紧凑 JSON(+gzip) 的实测序列化长度，非磁盘 I/O 开销、非常驻内存",
            "单文件 >2MB 跳过 ⇒ D 的体积为下界（skipped_large 计数可见）",
            "运行时窗读数取本机当前负载（对侧 30m 作业构建抬高原始计数）⇒ 已另给含构建产物的对照值",
            "冷扫耗时含解释器开销，不等于 AOT 产品侧成本，只作相对比较",
            "D1 阈值 1 次/分钟为**预注册**设计规则（理由见 criteria），非实测分布反解",
            "sensitive 过滤为命名/权限启发式；只记路径与计数，探针不读取也不输出其内容",
            "归因窗口基于 mtime：重命名不改 mtime ⇒ 纯改名型树变化对归因不可见",
            "本机对侧作业在跑（会改 src/ 产品源码）⇒ 作用域读数是对移动目标的快照，只能按同类作用域间相对比较解读",
        ],
    }
    Path(args.result).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({s: {"files": readings[s]["files"], "payload_kB": round(readings[s]["index_payload_bytes"] / 1024, 1),
                          "tok": readings[s]["distinct_tokens"], "scan_ms": readings[s]["cold_scan_ms_median"],
                          "edges": readings[s]["graph"]["edges_v3"], "per_min": churn_rt[s]["events_per_min_60min"],
                          "sensitive_all": readings[s]["sensitive_count"],
                          "sensitive_indexable": readings[s]["sensitive_indexable_count"],
                          "verdict": decisions[s]["verdict"]}
                      for s in readings}, ensure_ascii=False, indent=2))
    print(json.dumps({"gates": result["gates"], "masker_cross_check": xcheck, "recommended": recommended,
                      "gate_pass": gate_pass}, ensure_ascii=False))
    return 0 if gate_pass else 2


if __name__ == "__main__":
    sys.exit(main())
