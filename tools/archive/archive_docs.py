#!/usr/bin/env python3
"""旧版本文档归档装置（RF0001 起）：把 v0.13–v1.01 的计划/报告/变更日志移入 docs/archive/，
生成机读台账 + 人读索引，并重写活文档里的指针。

用法：
  --plan     重新计算归档面（保留面规则单一源），落 /tmp/rf_plan2.json
  --dry-run  只打印将要移动/重写的内容
  --apply    git mv + 生成台账/索引 + 重写活文档指针
  --verify   机检：覆盖 100% / 无悬空引用 / DocRef 全解析 / 索引行数=台账条数

保留面（不归档）规则：
  ① 当前功能描述与活台账（README*、api.md、architecture.md、CLI/Role/Skill/验证形式规范、
     iteration-master-plan、test-dimensions-ledger、dev-return-digest、status.json、round-collision-log …）
  ② 机器引用面：src/ tools/ scripts/ config/ .github-local/ 下**可执行或注释**里引用的 docs 路径
     （改了要么重发布 AOT，要么动 cron/hook ⇒ 一律保持原位）
  ③ docs/verification-registry.json 的证据行路径（网关要求 eval/ 或 docs/reports/ 前缀，不可改）
  ④ docs/reports/bge/**（scripts/bge_idle_train.sh 的写入面）
"""
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAN_JSON = "/tmp/rf_plan2.json"
ARCHIVE_DIR = "docs/archive"
REG = f"{ARCHIVE_DIR}/archive-registry.json"
INDEX = f"{ARCHIVE_DIR}/ARCHIVE-INDEX.md"
DOCREF_PLAN = "docs/plans/v715_dev_plan.taskplan.json"
REWRITE_DOCS = ["README.md", "README_EN.md", "docs/plans/RF0001-fable-aligned-development-plan.md"]
KEEP_EXPLICIT = {
    "docs/improvements.md",
    "docs/reports/iteration-master-plan.md",
    "docs/reports/test-dimensions-ledger.md",
    "docs/reports/dev-return-digest.md",
    "docs/reports/status.json",
    "docs/reports/round-collision-log.jsonl",
    "docs/reports/dynamic-telemetry-eval-rollback-strategy.md",
    "docs/plans/v0.22.0-longterm-backlog.md",
    "docs/plans/v715_dev_plan.taskplan.json",
}
KEEP_PREFIX = ("docs/reports/bge/",)
CAND_PREFIX = ("docs/plans/", "docs/reports/", "docs/changelogs/")
PATH_RE = re.compile(r"docs/[A-Za-z0-9_./\u4e00-\u9fff-]+\.[A-Za-z0-9]+")


def sh(cmd: str, check: bool = False) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"FAIL: {cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def tracked(patterns: str) -> list[str]:
    return [f for f in sh(f"git ls-files {patterns}").split("\n") if f]


def classify() -> dict:
    cand = tracked("docs/plans docs/reports docs/changelogs")
    keep_reason: dict[str, set[str]] = {}
    for f in tracked("src tools scripts config .github-local"):
        if not os.path.exists(f):
            continue
        txt = open(f, encoding="utf-8", errors="replace").read()
        for m in set(PATH_RE.findall(txt)):
            if m.startswith(CAND_PREFIX):
                keep_reason.setdefault(m, set()).add(f)
    # ③ registry：evidence_* / cmd / gap_note / negative_control 引用的路径**必须现盘存在**（R2/R2b/R2c 机检）
    #    ⇒ 保持原位；只有 covers[]（设计依据指针）可以随文件迁到归档路径（机检只要求存在）。
    reg = json.load(open("docs/verification-registry.json"))
    KEEP_FIELDS = {"evidence_path", "evidence_report", "evidence_cmd", "gap_note",
                   "negative_control", "external_assets"}
    reg_paths: set[str] = set()

    def walk(o, fld="?"):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, fld)
        elif isinstance(o, str):
            for p in (o.split("(")[0].strip() if fld != "evidence_cmd" else o).split():
                p = p.strip("`(),")
                if p.startswith(CAND_PREFIX) and "." in p.split("/")[-1] and fld in KEEP_FIELDS:
                    reg_paths.add(p)
    walk(reg)
    for p in reg_paths:
        keep_reason.setdefault(p, set()).add("docs/verification-registry.json")
    plan = json.load(open(DOCREF_PLAN))
    docrefs: set[str] = set()

    def walk2(o):
        if isinstance(o, dict):
            if isinstance(o.get("DocRef"), str):
                docrefs.add(o["DocRef"])
            for v in o.values():
                walk2(v)
        elif isinstance(o, list):
            for v in o:
                walk2(v)
    walk2(plan)
    keep = [f for f in cand if f in KEEP_EXPLICIT or f.startswith(KEEP_PREFIX) or f in keep_reason]
    arch = [f for f in cand if f not in set(keep)]
    return {"keep": keep, "archive": arch,
            "keep_reason": {k: sorted(v) for k, v in keep_reason.items()},
            "docrefs_to_rewrite": sorted(d for d in docrefs if d in set(arch))}


def new_path(old: str) -> str:
    kind = old.split("/")[1]              # plans|reports|changelogs
    return f"{ARCHIVE_DIR}/{kind}/{old.split('/')[-1]}"


def sha256(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def summary(p: str) -> str:
    try:
        for ln in open(p, encoding="utf-8", errors="replace"):
            s = ln.strip()
            if not s:
                continue
            s = re.sub(r"^#+\s*", "", s)
            s = re.sub(r"[`*_>]", "", s)
            return s[:88]
    except Exception:
        pass
    return "(空/不可读)"


def entries(arch: list[str]) -> list[dict]:
    out = []
    for i, old in enumerate(sorted(arch), 1):
        n = new_path(old)
        out.append({"id": f"AR-{i:04d}", "orig": old, "now": n,
                    "lines": len(open(old, "rb").read().splitlines()),
                    "bytes": os.path.getsize(old), "sha256": sha256(old),
                    "dir": old.split("/")[1], "summary": summary(old)})
    return out


def write_registry(ents: list[dict]) -> None:
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    json.dump({"schema": "docs-archive/v1", "created_round": "R541",
               "policy": "旧版本线 v0.13–v1.01 文档归档；保留面见 tools/archive/archive_docs.py 头部规则",
               "count": len(ents), "total_lines": sum(e["lines"] for e in ents),
               "entries": ents}, open(REG, "w"), ensure_ascii=False, indent=1)


def write_index(ents: list[dict], stale_refs: int) -> None:
    by_dir = collections.Counter(e["dir"] for e in ents)
    lines = ["# 归档索引（旧版本线 v0.13–v1.01）", "",
             "> 生成物：`python3 tools/archive/archive_docs.py --apply`。机读台账 = `archive-registry.json`。",
             f"> 条目 **{len(ents)}** ｜ 行数 **{sum(e['lines'] for e in ents):,}** ｜ "
             f"分布 plans {by_dir['plans']} / reports {by_dir['reports']} / changelogs {by_dir['changelogs']}",
             "> 保留面（当前功能描述 / 活台账 / 机器引用面 / BGE 写入面）**不入档**，理由逐条记在台账 `keep_reason`。",
             "", "| 归档号 | 原路径 | 行数 | 一句话 |", "|---|---|---|---|"]
    for e in ents:
        lines.append(f"| {e['id']} | `{e['orig']}` | {e['lines']} | {e['summary']} |")
    lines += ["", "## 机检", "",
              "- 覆盖：台账条数 = `docs/archive/{plans,reports,changelogs}` 下实际文件数（`--verify`）。",
              "- 悬空：`src|tools|scripts|config|README|docs/plans` 面对归档路径的引用必须为 0。",
              f"- 证据面历史指针：`eval/**` 内仍指向原路径的字符串 **{stale_refs}** 处 —— 证据是历史记录，**不重写**；"
              "按同名文件在 `docs/archive/{kind}/` 下可回溯。"]
    open(INDEX, "w").write("\n".join(lines) + "\n")


def rewrite_refs(arch: list[str]) -> list[str]:
    moved = {old: new_path(old) for old in arch}
    targets = set(REWRITE_DOCS)
    # 活文档（docs/**.md）+ 计划 JSON + 机器台账指针（registry.covers / status.json）：
    # 只做**原路径字面替换**（保形，不重排 JSON）；证据面 eval/** 与 docs/archive/** 不动。
    targets |= {f for f in tracked("docs/*.md docs/plans") if f.endswith((".md", ".json"))}
    targets |= {"docs/verification-registry.json", "docs/reports/status.json"}
    changed = []
    for f in sorted(targets):
        if not os.path.exists(f):
            continue
        txt = open(f, encoding="utf-8", errors="replace").read()
        new = txt
        for old, nw in moved.items():
            new = new.replace(old, nw)
        if new != txt:
            open(f, "w").write(new)
            changed.append(f)
    return changed


def stale_evidence_refs(arch: list[str]) -> int:
    n = 0
    for old in arch:
        n += len([l for l in sh(f"git grep -n --fixed-strings {json.dumps(old)} -- eval").split("\n") if l.strip()])
    return n


def do_apply(plan: dict) -> None:
    arch = plan["archive"]
    ents = entries(arch)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    # 1) 先重写 DocRef（原路径字符串还在时替换，避免 DocRef 指向不存在的文件）
    changed = rewrite_refs(arch)
    # 2) git mv
    for e in ents:
        os.makedirs(os.path.dirname(e["now"]), exist_ok=True)
        sh(f"git mv {json.dumps(e['orig'])} {json.dumps(e['now'])}", check=True)
    # 3) 台账 + 索引
    for e in ents:
        e["sha256_now"] = sha256(e["now"])
    write_registry(ents)
    write_index(ents, stale_evidence_refs(arch))
    print(f"APPLY: 归档 {len(ents)} 文件 / {sum(e['lines'] for e in ents):,} 行")
    print(f"       重写活文档 {len(changed)}: " + ", ".join(changed))


def do_resign() -> int:
    """在**迁移完成后**（含链接重写）重签台账：记录归档后 sha、归档前 blob sha、既有归档面清单。"""
    reg = json.load(open(REG))
    ents = reg["entries"]
    base = sh("git rev-parse HEAD").strip()
    reg["base_commit"] = base
    rewritten = 0
    for e in ents:
        e["lines"] = len(open(e["now"], "rb").read().splitlines())
        e["bytes"] = os.path.getsize(e["now"])
        e["sha256_now"] = sha256(e["now"])
        blob = sh(f"git show {base}:{json.dumps(e['orig'])}")
        e["sha256_orig"] = hashlib.sha256(blob.encode("utf-8", "surrogateescape")).hexdigest()
        if e["sha256_orig"] != e["sha256_now"]:
            rewritten += 1
    on_disk = {f for f in tracked(ARCHIVE_DIR) if f not in (REG, INDEX)}
    reg["preexisting"] = sorted(on_disk - {e["now"] for e in ents})
    reg["rewritten_entries"] = rewritten
    json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)
    print(f"RESIGN: 条目 {len(ents)} · 内容被链接重写 {rewritten} · 既有归档 {len(reg['preexisting'])} · base {base[:8]}")
    return 0


def do_verify() -> int:
    bad = []
    reg = json.load(open(REG))
    ents = reg["entries"]
    on_disk = {f for f in tracked(ARCHIVE_DIR) if f not in (REG, INDEX)}
    covered = {e["now"] for e in ents} | set(reg.get("preexisting", []))
    if covered != on_disk:
        bad.append(f"覆盖不符: 台账 {len(covered)} vs 磁盘 {len(on_disk)} (缺台账 {sorted(on_disk - covered)[:3]})")
    for e in ents:
        if not os.path.exists(e["now"]):
            bad.append(f"缺文件: {e['now']}")
        if os.path.exists(e["orig"]):
            bad.append(f"原件仍在: {e['orig']}")
        if sha256(e["now"]) != e.get("sha256_now", e.get("sha256")):
            bad.append(f"内容变了: {e['now']}")
    # 悬空引用
    pat = " ".join(f"--fixed-strings {json.dumps(e['orig'])}" for e in ents[:400])
    for scope in ("src tools scripts config README.md README_EN.md docs/plans"):
        out = sh(f"git grep -n {pat} -- {scope}")
        for ln in out.split("\n"):
            if ln.strip():
                bad.append(f"悬空引用[{scope}]: {ln[:160]}")
    # DocRef 全解析
    plan = json.load(open(DOCREF_PLAN))
    refs = []

    def w(o):
        if isinstance(o, dict):
            if isinstance(o.get("DocRef"), str):
                refs.append(o["DocRef"])
            for v in o.values():
                w(v)
        elif isinstance(o, list):
            for v in o:
                w(v)
    w(plan)
    for r in refs:
        if not os.path.exists(r):
            bad.append(f"DocRef 不存在: {r}")
    idx_rows = sum(1 for l in open(INDEX) if l.startswith("| AR-"))
    if idx_rows != len(ents):
        bad.append(f"索引行数 {idx_rows} != 台账 {len(ents)}")
    print(f"VERIFY: 条目 {len(ents)} / DocRef {len(refs)} 全解析 / 索引行 {idx_rows}")
    if bad:
        print("FAIL:")
        for b in bad[:40]:
            print("  -", b)
        return 1
    print("PASS: 覆盖 100% · 无悬空引用 · DocRef 全解析 · 索引=台账")
    return 0


def main() -> int:
    os.chdir(REPO)
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    for m in ("plan", "dry-run", "apply", "resign", "verify"):
        g.add_argument(f"--{m}", action="store_true")
    a = ap.parse_args()
    if a.verify:
        return do_verify()
    if a.resign:
        return do_resign()
    plan = classify()
    json.dump(plan, open(PLAN_JSON, "w"), ensure_ascii=False, indent=1)
    lines = sum(len(open(f, "rb").read().splitlines()) for f in plan["archive"])
    print(f"候选 {len(plan['keep']) + len(plan['archive'])} | 保留 {len(plan['keep'])} | 归档 {len(plan['archive'])} ({lines:,} 行)")
    print("DocRef 待重写", len(plan["docrefs_to_rewrite"]))
    if a.dry_run:
        for f in plan["archive"][:12]:
            print("  →", f, "=>", new_path(f))
        print(f"  … 共 {len(plan['archive'])} 条")
    if a.apply:
        do_apply(plan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
