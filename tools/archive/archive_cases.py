#!/usr/bin/env python3
"""
archive_cases.py — 用例归档装置（R543 · RF0001 精简轮）
========================================================
目标: 把**不需要的用例/器具/产物**从活跃面迁到归档面 `eval/archive/cases/**`，
      只保留「经典用例」。

保留规则（fail-closed，机检）:
  K1 显式白名单 WHITELIST —— 主线判定面（KPI 挂钩：t1/g1/ms1 夹具+判据器、前置器、契约/结构/API/归档闸…）
  K2 可执行闭包 reach —— 从可执行根（src/** 产品与测试、tools/**、scripts/**、.git/hooks）+ 机器台账
     （`docs/verification-registry.json` / `eval/capability/kpi.jsonl` / `instruments.json`）出发的
     **文件级引用**闭包。只从可执行文件展开；数据文件是叶子
     （R542 recon 实证：corpus/fixture 里出现路径字符串 ≠ 引用，会被误判 ⇒ 必须封死）。
  K3 通配扫描保护 GLOB —— 引用方用 `dir/*` 之类通配扫的目录，其下文件整目录保留。
  K4 目录级引用 —— 该目录必须继续存在（不护其中文件；空目录补 `.gitkeep`）。
自排除: `eval/archive/**` 永不进候选（器具产物必自排除出被扫语料）。

归档 = 迁移 + 引用重写 + 重签台账，**不删**。

用法:
  python3 tools/archive/archive_cases.py --plan | --dry-run | --apply | --resign | --verify | --restore
"""
import argparse, ast, hashlib, json, os, re, subprocess, sys, collections

ARCHIVE_DIR = "eval/archive/cases"
REG = "eval/archive/case-registry.json"
INDEX = "eval/archive/CASE-INDEX.md"
PLAN_JSON = "/tmp/r543_cases_plan.json"
ID_PREFIX = "AC"
SELF_EXCLUDE = ("eval/archive/",)
CAND_PREFIX = ("eval/",)
EXEC_PREFIX = ("src/", "tools/", "scripts/")
EXEC_EXT = (".py", ".cs", ".sh", ".ps1", ".js")
LEDGERS = ("docs/verification-registry.json", "eval/capability/kpi.jsonl",
           "eval/capability/instruments.json", "eval/capability/exec_precondition.json")
WHITELIST = (
    "eval/rover/lib/", "eval/rover/r507pre/", "eval/rover/r510/", "eval/rover/r536/",
    "eval/rover/r539/", "eval/rover/r540/", "eval/rover/r541/", "eval/rover/r542/",
    "eval/capability/exp1-q51/", "eval/capability/kpi.jsonl", "eval/capability/instruments.json",
    "eval/capability/exec_precondition.json", "eval/capability/status.py",
    "eval/verification/", "eval/recall/r487/",
    # 前序轮封存草案 `eval/rover/ARCHIVE.md` 钦定的「现行可运行链」白名单轮（保持对侧裁定，不推翻）
    "eval/rover/r371d7/", "eval/rover/r413/", "eval/rover/r415/", "eval/rover/r429/",
    "eval/rover/r431/", "eval/rover/r435/", "eval/rover/r449/", "eval/rover/r455/",
    "eval/rover/r469/", "eval/rover/r482/", "eval/rover/r483/", "eval/rover/r489/",
    "eval/rover/r493/", "eval/rover/r498/", "eval/rover/r502/", "eval/rover/r503/",
    "eval/rover/r504/", "eval/rover/r511/", "eval/rover/r515/", "eval/rover/r519/",
    "eval/rover/r520/", "eval/rover/r521/", "eval/rover/r525/", "eval/rover/r527/",
    "eval/rover/r528/", "eval/rover/r529/", "eval/rover/r531/", "eval/rover/r532/",
    "eval/rover/r533/",
    # bge 面按用户口径为「静默后台」但**活跃**（工作树有在改文件，见 git status）
    "eval/bge/",
)
REWRITE_DOCS = ("README.md", "docs/evidence", "docs/plans", "docs/external-reference")
PATH_RE = re.compile(r"(?:src|tools|scripts|eval|docs|config|skills|data)/[A-Za-z0-9_./\-]*[A-Za-z0-9_/\-]")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def sh(cmd, check=False):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, cwd=ROOT)
    if check and r.returncode != 0:
        raise SystemExit(f"FAILED: {cmd}\n{r.stderr[:500]}")
    return r.stdout


def tracked(pattern=None):
    return [l for l in sh(["git", "ls-files"] + ([pattern] if pattern else [])).split("\n") if l]


def clean(p):
    p = p.strip().strip('"\'`,);:')
    while p.endswith(("/", ".")) and len(p) > 1:
        p = p[:-1]
    return p


def lits_py(path):
    """Python 字符串字面量（**排除 docstring**：文档/散文里的路径不是引用 —— 同一纪律见 tools/refactor/delete_ref_gate.py）"""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="ignore").read())
    except (SyntaxError, OSError):
        return []
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docs.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


def lits_text(path):
    out = []
    try:
        txt = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return out
    for line in txt.split("\n"):
        if path.endswith(".cs"):
            out.append(line.split("//", 1)[0])
        else:
            if line.lstrip().startswith("#"):
                continue
            out.append(line)
    return out


def refs_of(path):
    lits = lits_py(path) if path.endswith(".py") else lits_text(path)
    out = set()
    for lit in lits:
        for m in PATH_RE.finditer(lit):
            out.add(clean(m.group(0)))
    return out


GLOB_TOKEN_RE = re.compile(r"(?:src|tools|scripts|eval|docs|config|skills|data)/[A-Za-z0-9_./\-*?]*\*[A-Za-z0-9_./\-*?]*")


def glob_regex(pat):
    out, i = [], 0
    while i < len(pat):
        if pat[i] == "*":
            if i + 1 < len(pat) and pat[i + 1] == "*":
                out.append(".*"); i += 2
            else:
                out.append("[^/]*"); i += 1
        elif pat[i] == "?":
            out.append("[^/]"); i += 1
        else:
            out.append(re.escape(pat[i])); i += 1
    return re.compile("^" + "".join(out) + "$")


def glob_protected(globs, tracked_files):
    """通配扫描保护: 只护**模式真正命中**的文件（不做前缀整树保护）。
    退化模式（如 `eval/**`、`src/*` 这种"整个面"提及，无文件名/无轮次级作用域）不构成保护，
    否则整个面会被一句目录提及钉死。判据: 模式须含扩展名 '.' 或 ≥3 段路径。"""
    pats = set()
    for lit in globs:
        for m in GLOB_TOKEN_RE.finditer(lit):
            pat = m.group(0).strip()
            if "." not in pat and pat.count("/") < 2:
                continue
            pats.add(pat)
    rxs = [glob_regex(p) for p in pats]
    prot = set()
    for f in tracked_files:
        if any(rx.match(f) for rx in rxs):
            prot.add(f)
    return prot, pats


def is_specific(seg):
    """目录/文件段是否"足够具体"（避免把 eval/capability 这类通用名当成整体保护锚点）"""
    return bool(re.search(r"[0-9_-]", seg)) or len(seg) >= 12


def scan(tracked_files, dirs):
    """返回 reach(文件级闭包) / why / kept_dirs / glob_raw(通配原文)

    闭包语义: 从「可执行根」出发, 只从**可执行文件**展开引用(数据文件是叶子);
    台账(registry/kpi/instruments)是**引用源**也是被引用者, 其指向的可执行文件同样展开
    ⇒ 采用不动点迭代(而非队列单趟), 否则「台账→器具→器具文件」链会断在第二跳。
    """
    tset = set(tracked_files)
    # 唯一 basename 表: 允许「动态拼路径」(Path.Combine("eval","x.json")) 的引用被识别
    bc = collections.Counter(os.path.basename(f) for f in tracked_files)
    uniq = {os.path.basename(f): f for f in tracked_files if bc[os.path.basename(f)] == 1}
    # 唯一目录名表: 允许 Path.Combine("eval","capability","r422","fixture-sessions") 式的目录引用
    dc = collections.Counter(os.path.basename(d) for d in dirs)
    uniq_dirs = {os.path.basename(d): d for d in dirs if dc[os.path.basename(d)] == 1 and is_specific(os.path.basename(d))}

    def is_exec(p):
        return p.endswith(EXEC_EXT) or "." not in os.path.basename(p)

    reach, why, kept_dirs, globs, done = set(), {}, set(), set(), set()
    for f in tracked_files:
        if (f.startswith(EXEC_PREFIX) or f.startswith("tools/hooks/") or f == ".git/hooks/pre-commit") \
                and is_exec(f) and not f.startswith(SELF_EXCLUDE):
            reach.add(f); why.setdefault(f, "EXEC_ROOT")

    def absorb(cur, lits):
        live = cur.startswith(EXEC_PREFIX) or cur.startswith("tools/hooks/")
        for lit in lits:
            if "*" in lit:
                globs.add(lit)
            for m in PATH_RE.finditer(lit):
                p = clean(m.group(0))
                if p in tset:
                    if p not in reach:
                        reach.add(p); why.setdefault(p, f"REF:{cur}")
                    if not is_exec(p):
                        why.setdefault(p, f"REF+LEAF:{cur}")
                elif p in dirs:
                    kept_dirs.add(p)
                    # 活面(产品/器具)点名的目录 ⇒ 目录内容须可用（历史脚本只要求目录存在）
                    if live and p.count("/") >= 2 and is_specific(p.rsplit("/", 1)[1]):
                        for f in tset:
                            if f.startswith(p + "/"):
                                reach.add(f); why.setdefault(f, f"DIR-LIVE:{cur}")
            for tok in re.split(r"[^A-Za-z0-9_.\-]+", lit):   # 唯一 basename: 动态拼路径兜底
                q = uniq.get(tok)
                if q and q not in reach and q in tset:
                    reach.add(q); why.setdefault(q, f"BASE:{cur}")
                d = uniq_dirs.get(tok)                        # 唯一目录名
                if d:
                    for f in tset:
                        if f.startswith(d + "/") and f not in reach:
                            reach.add(f); why.setdefault(f, f"BASE-DIR:{cur}")
            # n-gram 路径重建: Path.Combine("eval","capability","r422","fixture-sessions") ⇒ 逐窗拼回
            toks = re.split(r"[^A-Za-z0-9_.\-]+", lit)
            for i in range(len(toks)):
                for n in (2, 3, 4, 5):
                    j = i + n
                    if j > len(toks):
                        break
                    cand = "/".join(toks[i:j])
                    if cand in tset:
                        if cand not in reach:
                            reach.add(cand); why.setdefault(cand, f"NGRAM:{cur}")
                        if not is_exec(cand):
                            why.setdefault(cand, f"NGRAM+LEAF:{cur}")
                    elif cand in dirs:
                        kept_dirs.add(cand)
                        if live and cand.count("/") >= 2 and is_specific(cand.rsplit("/", 1)[1]):
                            for f in tset:
                                if f.startswith(cand + "/"):
                                    reach.add(f); why.setdefault(f, f"NGRAM-DIR:{cur}")

    for led in LEDGERS:
        if led not in tset:
            continue
        reach.add(led); why.setdefault(led, "LEDGER")
        try:
            txt = open(os.path.join(ROOT, led), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for m in PATH_RE.finditer(txt):
            p = clean(m.group(0))
            if p in tset:
                reach.add(p); why.setdefault(p, f"LEDGER:{led}")
            elif p in dirs:
                kept_dirs.add(p)

    while True:
        todo = [f for f in sorted(reach) if is_exec(f) and f not in done and os.path.isfile(os.path.join(ROOT, f))]
        if not todo:
            break
        for cur in todo:
            done.add(cur)
            try:
                lits = lits_py(os.path.join(ROOT, cur)) if cur.endswith(".py") else lits_text(os.path.join(ROOT, cur))
            except OSError:
                continue
            absorb(cur, lits)
    return reach, why, kept_dirs, globs


def is_whitelisted(p):
    return any(p == w or p.startswith(w) for w in WHITELIST)


def classify():
    tf = tracked()
    tset = set(tf)
    dirs = set()
    for f in tf:
        parts = f.split("/")
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]))
    reach, why, kept_dirs, globs = scan(tf, dirs)
    gp, gpat = glob_protected(globs, tf)
    cand, keep = [], []
    for f in tf:
        if not f.startswith(CAND_PREFIX) or f.startswith(SELF_EXCLUDE):
            continue
        if os.path.basename(f) == ".gitkeep":      # 占位文件不参与归档（目录级引用的存在性由 kept_dirs 负责）
            continue
        if is_whitelisted(f) or f in reach or f in gp:
            keep.append(f)
        else:
            cand.append(f)
    return {"files": tf, "keep": sorted(keep), "why": why, "glob_protected": sorted(gp),
            "glob_patterns": sorted(gpat), "kept_dirs": sorted(kept_dirs), "cand": sorted(cand)}


def new_path(old):
    return f"{ARCHIVE_DIR}/{old[len('eval/'):]}" if old.startswith("eval/") else f"{ARCHIVE_DIR}/{old}"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def summarize(p):
    try:
        for ln in open(p, encoding="utf-8", errors="replace"):
            s = re.sub(r"[`*_>]", "", re.sub(r"^#+\s*", "", ln.strip()))
            if s:
                return s[:72]
    except OSError:
        pass
    return "(二进制/空)"


def entries(arch):
    out = []
    for i, old in enumerate(sorted(arch), 1):
        ap = os.path.join(ROOT, old)
        out.append({"id": f"{ID_PREFIX}-{i:04d}", "orig": old, "now": new_path(old),
                    "bytes": os.path.getsize(ap),
                    "lines": len(open(ap, "rb").read().splitlines()),
                    "sha256": sha256(ap), "kind": old.split("/")[1] if "/" in old[4:] else "root",
                    "summary": summarize(ap)})
    return out


def write_registry(ents, keep_note):
    os.makedirs(os.path.join(ROOT, ARCHIVE_DIR), exist_ok=True)
    json.dump({"schema": "cases-archive/v1", "created_round": "R543",
               "policy": "保留面 = 白名单 ∪ 可执行闭包 ∪ 通配扫描保护（见 tools/archive/archive_cases.py 头）",
               "count": len(ents), "total_lines": sum(e["lines"] for e in ents),
               "total_bytes": sum(e["bytes"] for e in ents), "keep_note": keep_note,
               "entries": ents},
              open(os.path.join(ROOT, REG), "w"), ensure_ascii=False, indent=1)


def write_index(ents):
    by = collections.Counter(e["orig"].split("/")[1] for e in ents)
    lines = ["# 用例归档索引（RF0001 精简轮 R543）", "",
             "> 生成物：`python3 tools/archive/archive_cases.py --apply`；机读台账 = `case-registry.json`。",
             f"> 条目 **{len(ents)}** ｜ 行数 **{sum(e['lines'] for e in ents):,}** ｜ 字节 **{sum(e['bytes'] for e in ents):,}**",
             "> 分布 " + " / ".join(f"{k} {v}" for k, v in by.most_common()),
             "> 保留面（经典用例 / KPI 挂钩 / 机器引用面）**不入档**，规则见装置头部。",
             "", "| 归档号 | 原路径 | 行 | 一句话 |", "|---|---|---|---|"]
    for e in ents[:400]:
        lines.append(f"| {e['id']} | `{e['orig']}` | {e['lines']} | {e['summary']} |")
    if len(ents) > 400:
        lines.append(f"| … | 其余 {len(ents) - 400} 条见 `case-registry.json` | | |")
    open(os.path.join(ROOT, INDEX), "w").write("\n".join(lines) + "\n")


def rewrite_refs(arch):
    moved = {o: new_path(o) for o in arch}
    targets = set()
    for d in REWRITE_DOCS:
        p = os.path.join(ROOT, d)
        if os.path.isfile(p):
            targets.add(d)
        elif os.path.isdir(p):
            targets |= {f for f in tracked(f"{d}*") if f.endswith((".md", ".json"))}
    changed = []
    for f in sorted(targets):
        ap = os.path.join(ROOT, f)
        if not os.path.exists(ap):
            continue
        txt = open(ap, encoding="utf-8", errors="replace").read()
        new = txt
        for o, nw in moved.items():
            new = new.replace(o, nw)
        if new != txt:
            open(ap, "w").write(new)
            changed.append(f)
    return changed


def stale_evidence_refs(arch):
    n = 0
    for o in arch:
        out = sh(["git", "grep", "-n", "--fixed-strings", o, "--", "eval"])
        n += len([l for l in out.split("\n") if l.strip() and "archive/cases" not in l])
    return n


def do_apply(plan):
    arch = plan["cand"]
    # 前置闸: 归档面已有条目必须与本次候选一致（防「台账被截断/覆盖」类事故，见 R543 实况）
    existing = [f for f in tracked() if f.startswith(ARCHIVE_DIR + "/")]
    if existing and len(existing) != len(arch):
        print(f"ABORT: 归档面已有 {len(existing)} 文件但候选 {len(arch)} ⇒ 先跑 --rebuild && --restore && --dry-run")
        return 1
    ents = entries(arch)
    os.makedirs(os.path.join(ROOT, ARCHIVE_DIR), exist_ok=True)
    changed = rewrite_refs(arch)
    for e in ents:
        # 逐文件后置条件: 目标名必须是纯前缀改写, 且移动前后存在性可核 ⇒ 任何"名字错位"当场 abort
        assert e["now"] == new_path(e["orig"]), f"dest 非前缀改写: {e['orig']} -> {e['now']}"
        src, dst = os.path.join(ROOT, e["orig"]), os.path.join(ROOT, e["now"])
        assert os.path.isfile(src) and not os.path.exists(dst), f"前态非法: {e['orig']}"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        sh(["git", "mv", "--", e["orig"], e["now"]], check=True)
        assert os.path.isfile(dst) and not os.path.exists(src), f"后态非法: {e['orig']} -> {e['now']}"
    for e in ents:
        e["sha256_now"] = sha256(os.path.join(ROOT, e["now"]))
    # 空目录补 .gitkeep（目录级引用面必须继续存在）
    keep_note = {"kept_empty_dirs": 0, "rewritten_docs": len(changed)}
    for d in plan["kept_dirs"]:
        if d.startswith(SELF_EXCLUDE) or not os.path.isdir(os.path.join(ROOT, d)):
            continue
        if not [f for f in tracked(f"{d}/*") if f.startswith(d + "/")]:
            gk = f"{d}/.gitkeep"
            open(os.path.join(ROOT, gk), "w").write("")
            sh(["git", "add", gk])
            keep_note["kept_empty_dirs"] += 1
    write_registry(ents, keep_note)
    write_index(ents)
    print(f"APPLY: 归档 {len(ents)} 文件 / {sum(e['lines'] for e in ents):,} 行 / "
          f"{sum(e['bytes'] for e in ents)/1048576:.2f} MB")
    print(f"       重写活文档 {len(changed)}: " + ", ".join(changed[:6]))
    print(f"       补空目录 .gitkeep {keep_note['kept_empty_dirs']}")


def do_resign():
    reg = json.load(open(os.path.join(ROOT, REG)))
    base = sh(["git", "rev-parse", "HEAD"]).strip()
    reg["base_commit"] = base
    for e in reg["entries"]:
        ap = os.path.join(ROOT, e["now"])
        e["bytes"] = os.path.getsize(ap)
        e["lines"] = len(open(ap, "rb").read().splitlines())
        e["sha256_now"] = sha256(ap)
        blob = sh(["git", "show", f"{base}:{e['orig']}"])
        e["sha256_orig"] = hashlib.sha256(blob.encode("utf-8", "surrogateescape")).hexdigest()
    json.dump(reg, open(os.path.join(ROOT, REG), "w"), ensure_ascii=False, indent=1)
    same = sum(1 for e in reg["entries"] if e.get("sha256_orig") == e["sha256_now"])
    print(f"RESIGN: 条目 {len(reg['entries'])} / sha 与归档前一致 {same} / base {base[:8]}")
    return 0


def do_verify():
    reg = json.load(open(os.path.join(ROOT, REG)))
    ents = reg["entries"]
    bad = []
    # 1) 台账 ↔ 现盘
    for e in ents:
        ap = os.path.join(ROOT, e["now"])
        if not os.path.exists(ap):
            bad.append(f"缺档 {e['now']}")
        elif sha256(ap) != e.get("sha256_now"):
            bad.append(f"sha 漂移 {e['now']}")
    badname = [f"{e['orig']} -> {e['now']}" for e in ents if e["now"] != new_path(e["orig"])]
    if badname:
        bad.append(f"目标名非前缀改写 {len(badname)}: {badname[:3]}")
    on_disk = [f for f in tracked(f"{ARCHIVE_DIR}*") if f.startswith(ARCHIVE_DIR + "/") and not f.endswith(".gitkeep")]
    if len(on_disk) != len(ents):
        bad.append(f"覆盖不符: 现盘 {len(on_disk)} vs 台账 {len(ents)}")
    # 2) 悬空: 可执行面 + 台账面 引用必须现盘存在
    tf = tracked(); tset = set(tf)
    dirs = {"/".join(f.split("/")[:i]) for f in tf for i in range(1, len(f.split("/")))}
    reach, why, kept_dirs, _ = scan(tf, dirs)
    dangling = []
    for f in sorted(reach):
        if not f.endswith(EXEC_EXT):
            continue
        for lit in (lits_py(os.path.join(ROOT, f)) if f.endswith(".py") else lits_text(os.path.join(ROOT, f))):
            for m in PATH_RE.finditer(lit):
                p = clean(m.group(0))
                if p in tset and p.startswith(("eval/",)) and not os.path.exists(os.path.join(ROOT, p)):
                    dangling.append(f"{f} -> {p}")
    if dangling:
        bad.append(f"悬空引用 {len(dangling)}: {dangling[:3]}")
    # 3) 索引 = 台账
    idx_rows = len([l for l in open(os.path.join(ROOT, INDEX), encoding="utf-8") if l.startswith("| AC-")])
    if idx_rows and idx_rows != min(len(ents), 400):
        bad.append(f"索引行 {idx_rows} != min(台账,400) {min(len(ents), 400)}")
    print(f"VERIFY: 条目 {len(ents)} / 现盘 {len(on_disk)} / 索引行 {idx_rows} / 可执行闭包 {len(reach)}")
    if bad:
        print("FAIL:")
        for b in bad[:8]:
            print("  -", b)
        return 1
    print("PASS: 覆盖 100% · sha 一致 · 无悬空引用 · 索引=台账")
    return 0


def do_restore():
    reg = json.load(open(os.path.join(ROOT, REG)))
    n = 0
    for e in reg["entries"]:
        src, dst = os.path.join(ROOT, e["now"]), os.path.join(ROOT, e["orig"])
        if not os.path.exists(src):
            continue
        if os.path.exists(dst):          # 同路径残留（如 .gitkeep 占位）⇒ 直接覆盖，否则 git mv 会 fatal
            os.remove(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        sh(["git", "mv", "-f", e["now"], e["orig"]], check=True)
        n += 1
    print(f"RESTORE: 回迁 {n} 文件")
    return 0


def do_rebuild():
    """从**现状**(归档面索引)反推重建台账 —— 供 apply 误截断台账后的恢复（幂等）。"""
    ents = []
    for f in tracked():
        if not f.startswith(ARCHIVE_DIR + "/"):
            continue
        orig = "eval/" + f[len(ARCHIVE_DIR + "/cases/"):]
        e = {"orig": orig, "now": f, "bytes": os.path.getsize(os.path.join(ROOT, f)),
             "lines": len(open(os.path.join(ROOT, f), "rb").read().splitlines()),
             "sha256": sha256(os.path.join(ROOT, orig)) if os.path.exists(os.path.join(ROOT, orig))
             else sha256(os.path.join(ROOT, f)),
             "kind": orig.split("/")[1] if "/" in orig[4:] else "root",
             "summary": summarize(os.path.join(ROOT, f))}
        e["sha256_now"] = sha256(os.path.join(ROOT, f))
        ents.append(e)
    ents.sort(key=lambda e: e["orig"])
    for i, e in enumerate(ents, 1):
        e["id"] = f"{ID_PREFIX}-{i:04d}"
    write_registry(ents, {"kept_empty_dirs": 0, "rewritten_docs": 0, "rebuilt": True})
    write_index(ents)
    print(f"REBUILD: 台账重建 {len(ents)} 条")
    return 0


def do_resync():
    """判定面变更后对齐现状: 新 KEEP 的条目回迁原路径, 新候选补档."""
    plan = classify()
    keep, cand = set(plan["keep"]), set(plan["cand"])
    reg_p = os.path.join(ROOT, REG)
    reg = json.load(open(reg_p)) if os.path.exists(reg_p) else {"entries": []}
    ents = {e["orig"]: e for e in reg.get("entries", [])}
    back = [o for o in ents if o in keep]
    for o in sorted(back):
        n = ents[o]["now"]
        if os.path.exists(os.path.join(ROOT, n)):
            os.makedirs(os.path.dirname(os.path.join(ROOT, o)), exist_ok=True)
            sh(["git", "mv", n, o], check=True)
        ents.pop(o)
    add = [o for o in cand if o not in ents]
    for e in entries(add):
        os.makedirs(os.path.dirname(os.path.join(ROOT, e["now"])), exist_ok=True)
        sh(["git", "mv", e["orig"], e["now"]], check=True)
        e["sha256_now"] = sha256(os.path.join(ROOT, e["now"]))
        ents[e["orig"]] = e
    keep_note = {"kept_empty_dirs": 0, "rewritten_docs": len(rewrite_refs(list(ents))), "resync": True}
    out = sorted(ents.values(), key=lambda e: e["orig"])
    for i, e in enumerate(out, 1):
        e["id"] = f"{ID_PREFIX}-{i:04d}"
    write_registry(out, keep_note)
    write_index(out)
    print(f"RESYNC: 回迁 {len(back)} / 补档 {len(add)} / 台账 {len(out)} 条")
    return 0


def do_selftest():
    """负控 + 正控：器具自身的断言（每器具须负控）。"""
    plan = classify()
    keep, cand, why = set(plan["keep"]), set(plan["cand"]), plan["why"]
    fails = []
    # P1 正控: 主线判定面必须在 KEEP
    for f in ("eval/rover/r507pre/exec_precondition.py", "eval/capability/kpi.jsonl",
              "eval/capability/exp1-q51/oracle_q51.py"):
        if f not in keep:
            fails.append(f"P1 KEEP 漏 {f}")
    # P2 正控: 提交钩子链上的机检器必须在 KEEP（防「钩子是无扩展名文件 ⇒ 不被展开」同类缺陷）
    for f in ("eval/capability/decl_sweep.py", "eval/capability/bind_evidence.py"):
        if f in cand:
            fails.append(f"P2b 钩子机检器被判候选 {f}")
    # P3 正控: 产品/器具根不得进候选
    if any(f.startswith(("src/", "tools/", "scripts/", "docs/")) for f in cand):
        fails.append("P3 候选越界到 src/tools/scripts/docs")
    # N1 负控: 归档候选不得含任何机器台账(registry/kpi/instruments)引用的路径
    led_refs = set()
    for led in LEDGERS:
        if led in set(plan["files"]):
            txt = open(os.path.join(ROOT, led), encoding="utf-8", errors="ignore").read()
            for m in PATH_RE.finditer(txt):
                p = clean(m.group(0))
                if p in set(plan["files"]):
                    led_refs.add(p)
    if led_refs & cand:
        fails.append(f"N1 候选含台账引用 {len(led_refs & cand)}: {sorted(led_refs & cand)[:3]}")
    # N2 负控: 数据叶子(corpus/fixture)不得被当成引用展开源
    leak = [f for f, v in why.items()
            if v.startswith("REF:") and not (v.split("REF:", 1)[1].endswith(EXEC_EXT)
                                             or "." not in os.path.basename(v.split("REF:", 1)[1]))]
    if leak:
        fails.append(f"N2 数据叶子被展开 {len(leak)}: {leak[:3]}")
    # N3 负控: 归档面自身不得进候选
    if any(f.startswith(SELF_EXCLUDE) for f in cand):
        fails.append("N3 eval/archive 自身进候选")
    # N4 负控: 空集/全量归零 => 装置失效
    if not cand or len(cand) > 0.8 * len([f for f in plan["files"] if f.startswith("eval/")]):
        fails.append(f"N4 候选规模异常 {len(cand)}")
    print(f"SELFTEST: KEEP {len(keep)} / 候选 {len(cand)} / 台账引用 {len(led_refs)}")
    if fails:
        for f in fails:
            print("  FAIL:", f)
        return 1
    print("  PASS: 正控 2 · 负控 4 (台账不误档 / 数据叶子不误判 / 自排除 / 规模非退化)")
    return 0


def do_dry(plan):
    cand = plan["cand"]
    tot = sum(os.path.getsize(os.path.join(ROOT, f)) for f in cand)
    print(f"tracked {len(plan['files'])} | KEEP(eval) {len(plan['keep'])} | 通配保护 {len(plan['glob_protected'])} "
          f"| 目录引用面 {len(plan['kept_dirs'])} | 候选 {len(cand)} ({tot/1048576:.2f} MB)")
    agg = collections.Counter(); byt = collections.Counter()
    for f in cand:
        parts = f.split("/")
        k = "/".join(parts[:3]) if len(parts) > 3 and re.match(r"(r\d+|exp1-q\d+)", parts[2]) else "/".join(parts[:2])
        agg[k] += 1
        byt[k] += os.path.getsize(os.path.join(ROOT, f))
    print("  归档候选 top15:")
    for k, n in agg.most_common(15):
        print(f"    {k:42s} {n:5d} files {byt[k]/1048576:8.2f} MB")
    print("  KEEP 面构成:", collections.Counter(
        ("GLOB" if f in set(plan["glob_protected"]) else
         ("LEDGER" if plan["why"].get(f, "").startswith("LEDGER") else
          ("REF" if f in plan["why"] else "WHITELIST"))) for f in plan["keep"]).most_common())
    print(f"  通配模式 {len(plan['glob_patterns'])} 个 / 命中保护 {len(plan['glob_protected'])} 文件")
    for p in plan["glob_patterns"][:10]:
        print("    glob:", p)


def main():
    ap = argparse.ArgumentParser()
    for m in ("plan", "dry-run", "apply", "resign", "verify", "restore", "resync", "rebuild", "selftest"):
        ap.add_argument(f"--{m}", action="store_true")
    a = ap.parse_args()
    if a.plan or a.dry_run:
        plan = classify()
        json.dump(plan, open(PLAN_JSON, "w"), ensure_ascii=False, indent=1)
        print(f"PLAN → {PLAN_JSON}")
        do_dry(plan)
    elif a.apply:
        do_apply(json.load(open(PLAN_JSON)))
    elif a.resign:
        return do_resign()
    elif a.verify:
        return do_verify()
    elif a.restore:
        return do_restore()
    elif a.rebuild:
        return do_rebuild()
    elif a.resync:
        return do_resync()
    elif a.selftest:
        return do_selftest()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
