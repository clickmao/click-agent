#!/usr/bin/env python3
"""EXP1-Q6: 失效文档引用 (stale_path / relocated) 的四级归属复核 — v1.1.0

背景: 仪器 probe_doc_ref_integrity.py 把「精确路径不在树内且全树无同名候选」判 stale_path,
把「全树唯一同名候选在别处」判 relocated。两个桶都需要**外部真值**才谈得上缺陷定性
(「搜索不到」≠「已删除」; 「同名文件在别处」≠「文件没了」)。

v1.1.0 修两处**本仪器自身**的测量缺陷 (v1.0.0 实测暴露):
  (a) 时间轴锚错位: v1.0.0 用「文档最后一次提交」作写作时点 ⇒ 一次批量 docs 整理就会把
      写作于退役之前的**历史留痕**误判成「真死引用」(读数 7 项, 其中 6 项来自同一历史报告)。
      正解 = 锚到**该引用行自己的引入时点** (行级 blame + 全文档串级 -S 双证据)。
  (b) 每路径聚合用 dict 覆盖: 同一路径在不同文档里的时间轴归属**可以不同** ⇒ 不能取单值,
      必须按路径给**类别直方图** (单值聚合本身会掩盖多类)。

预注册判据 (读真实语料之前写定, 读数后不得改):
  L-1 存在性      : git ls-files --error-unmatch <path> 命中 ⇒ in_HEAD, 与仪器 stale 判定矛盾 ⇒ 仪器红
  L-2 无过滤全树搜索: os.walk 全树 (含被仪器 SKIP_DIR_PARTS 过滤的目录) 找同名文件
                      0 候选 ⇒ 支持"真删"候选; >0 ⇒ 仪器漏检 (measurement_defect, 不入缺陷账)
  L-3 真删外部真值 : git log --all --diff-filter=D -- <path> 取删除提交;
                      有提交 ∧ merge-base --is-ancestor <sha> HEAD ⇒ deleted_in_history (外部真值成立)
                      无删除提交 ∧ 历史里从未出现 ⇒ never_tracked (≠ 已删除, 单列)
  L-4 时间轴归属   : 双证据锚 (行级 blame_sha; 串级首次引入 intro_sha) 对 删除提交 D:
                      两条证据**都**晚于 D ⇒ dead_after_delete (真死引用, 红)
                      至少一条不晚于 D ⇒ retired_after_write (写作时有效, 事后退役 ⇒ 历史留痕, 不计红)
                      两证据互相矛盾 ⇒ axis_disagreement (弃权单列)
                      任一证据缺失 ⇒ 用可得者; 全缺 ⇒ ambiguous_no_time_axis (弃权)
  R-1 省略形态     : 引用路径含 '...' (文档作者简写) ⇒ path_elision (写法漂移, 不判"路径失效")
  R-2 定点可修     : 唯一候选 ∧ 行号在内 ∧ 符号齐备 ⇒ fixable_direct; 行号/符号不成立 ⇒ fact_drift; 多候选 ⇒ waived_ambiguous

判决三态: 缺陷 / 留痕(非缺陷) / 弃权。缺失或不可判**不得**计入缺陷 (「没测到」≠「测过是坏」)。
退出码: 0 = 全绿(无缺陷且无测量层异常) / 2 = 判定缺陷(断言失败) / 3 = 测量或环境失败(弃权)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "attribute_failed_refs-v1.2.0"


# ------------------------------------------------------------------ git 外部真值
def git(root: Path, *args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout.strip()


def head_existence(root: Path, path: str) -> bool:
    return git(root, "ls-files", "--error-unmatch", "--", path)[0] == 0


def deletion_truth(root: Path, path: str) -> dict:
    rc, out = git(root, "log", "--all", "--diff-filter=D", "--format=%H\x1f%cI\x1f%s", "--", path)
    dels = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3:
            dels.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
    ever = len([x for x in git(root, "log", "--all", "--format=%H", "--", path)[1].splitlines() if x.strip()])
    anc = git(root, "merge-base", "--is-ancestor", dels[0]["sha"], "HEAD")[0] == 0 if dels else None
    return {"deletion_commits": dels, "deletion_sha": dels[0]["sha"] if dels else None,
            "ancestor_of_head": anc, "tracked_commits": ever}


def blame_line_commit(root: Path, doc: str, line: int) -> str | None:
    """行级锚: 该引用行最后一次被改动的提交。"""
    rc, out = git(root, "blame", "-L", f"{line},{line}", "--porcelain", "--", doc)
    if rc != 0 or not out:
        return None
    first = out.splitlines()[0].split()
    return first[0] if first and len(first[0]) >= 7 else None


def intro_commit(root: Path, doc: str, needle: str) -> str | None:
    """串级锚: 该引用串在该文档中**首次**出现的提交 (git log -S 输出新→旧, 取末条)。

    必须带 --follow: 文档被重命名过时, 不带 --follow 会把**重命名提交**当成"首次出现"
    (实测 exp10 计划: 不带 = R392 重命名提交 20:49, 带 = 真正的 Added 提交 19:26) ⇒ 假红。
    """
    if not needle:
        return None
    rc, out = git(root, "log", "--follow", "--all", "--format=%H", f"-S{needle}", "--", doc)
    if rc != 0 or not out:
        return None
    shas = [x.strip() for x in out.splitlines() if x.strip()]
    return shas[-1] if shas else None


def is_anc(root: Path, a: str, b: str) -> bool | str | None:
    """True = b 晚于 a (a 是 b 的祖先); False = b 不晚于 a; 'same' = 同一提交; None = 不可判。"""
    if not a or not b:
        return None
    if a == b:
        return "same"
    return git(root, "merge-base", "--is-ancestor", a, b)[0] == 0


def time_axis(del_sha: str | None, blame_sha: str | None, intro_sha: str | None,
              blame_after: bool | str | None, intro_after: bool | str | None) -> tuple[str, str, str]:
    """L-4 纯函数 (可单测)。*_after 语义见 is_anc。

    分类次序 (先强证据, 后弃权, 最后才判缺陷):
      1) 任一证据**不晚于**退役提交 ⇒ 引用成形时该文件尚在 ⇒ retired_after_write (留痕)
         1b) 同时另有证据晚于退役 ⇒ 证据互斥 ⇒ axis_disagreement (弃权)
      2) 无"不晚于"证据, 但有证据**与退役同提交** ⇒ same_commit_as_deletion (弃权: 无法区分
         "提交前 recon" 与 "提交后残留" —— 一次提交同时退役文件并写入文档时必然出现, 计缺陷会成片假红)
      3) 全部可得证据都晚于退役 ⇒ dead_after_delete (真·写作时即失效)
    """
    if not del_sha:
        return "no_deletion_commit", "查不到删除提交 ⇒ 无时间轴可判(弃权)", "none"
    have = [a for a in (blame_after, intro_after) if a is not None]
    if not have:
        return "ambiguous_no_time_axis", "行级与串级锚点均不可得(如文档未入版本库) ⇒ 弃权", "none"
    src = "both" if len(have) == 2 else ("blame_only" if blame_after is not None else "intro_only")
    if any(h is False for h in have):
        if any(h is True for h in have):
            return "axis_disagreement", f"行级锚与串级锚互斥(blame_after={blame_after}, intro_after={intro_after}) ⇒ 弃权", "conflict"
        return "retired_after_write", "引用成形不晚于退役提交 ⇒ 写作时有效、事后退役 ⇒ 历史留痕(非缺陷)", src
    if any(h == "same" for h in have):
        return "same_commit_as_deletion", "引用成形与退役**同一提交** ⇒ 无法区分'documenting before' 与 'stale after' ⇒ 弃权(不计缺陷)", src
    return "dead_after_delete", "全部可得证据均晚于退役提交 ⇒ 写作时所指已不存在(真·死引用)", src


def unfiltered_hits(root: Path, basename: str) -> list[str]:
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        if basename in filenames:
            hits.append(Path(dirpath, basename).relative_to(root).as_posix())
    return sorted(hits)


# ------------------------------------------------------------------ 归属
def attribute_stale(root: Path, c: dict) -> dict:
    path, doc, line = c["path"], c["doc"], c.get("doc_line")
    rec = {"kind": "stale_path", "doc": doc, "doc_line": line, "path": path,
           "lines": [c["line_start"], c["line_end"]], "symbols": c.get("symbols") or [],
           "retire_marker": bool(c.get("retire_marker"))}
    rec["in_HEAD"] = head_existence(root, path)
    rec["unfiltered_hits"] = unfiltered_hits(root, Path(path).name)
    rec["del"] = deletion_truth(root, path)
    d_sha = rec["del"]["deletion_sha"]
    rec["blame_sha"] = blame_line_commit(root, doc, line) if isinstance(line, int) else None
    rec["intro_sha"] = intro_commit(root, doc, path)
    b_after = is_anc(root, d_sha, rec["blame_sha"]) if (d_sha and rec["blame_sha"]) else None
    i_after = is_anc(root, d_sha, rec["intro_sha"]) if (d_sha and rec["intro_sha"]) else None
    cls, why, src = time_axis(d_sha, rec["blame_sha"], rec["intro_sha"], b_after, i_after)
    rec["axis_source"] = src
    if rec["in_HEAD"]:
        cls, why = "measurement_defect", "路径仍在 HEAD 内 ⇒ 仪器 stale 判定为假"
    elif rec["unfiltered_hits"]:
        cls, why = "measurement_defect", f"全树存在同名文件 {rec['unfiltered_hits']} ⇒ 仪器漏检"
    elif not rec["del"]["deletion_commits"]:
        cls = "never_tracked" if rec["del"]["tracked_commits"] == 0 else "deleted_no_diff_filter"
        why = "历史中从未出现该路径 ⇒ 不是'已删除'(单列, 弃权)" if cls == "never_tracked" \
            else "曾跟踪但未取到删除提交(历史重写?) ⇒ 弃权"
    rec["class"], rec["reason"] = cls, why
    rec["is_defect"] = cls == "dead_after_delete"
    return rec


def attribute_relocated(root: Path, c: dict) -> dict:
    path, doc = c["path"], c["doc"]
    rec = {"kind": "relocated", "doc": doc, "doc_line": c.get("doc_line"), "path": path,
           "lines": [c["line_start"], c["line_end"]], "symbols": c.get("symbols") or [],
           "candidates": c.get("relocated_to") or []}
    if "..." in path:
        rec["class"], rec["reason"] = "path_elision", "文档作者简写(含 '...') ⇒ 写法漂移, 非路径失效"
    elif len(rec["candidates"]) != 1:
        rec["class"], rec["reason"] = "waived_ambiguous", "多候选 ⇒ 不任取(弃权)"
    elif c.get("relocated_fact_verdict") == "ok":
        rec["target"] = rec["candidates"][0]
        rec["class"], rec["reason"] = "fixable_direct", "唯一候选且行号/符号成立 ⇒ 可定点改写路径"
    else:
        rec["target"] = rec["candidates"][0]
        rec["class"] = "fact_drift"
        rec["reason"] = f"唯一候选但事实不成立({c.get('relocated_fact_verdict')}) ⇒ 需复核内容"
    rec["is_defect"] = rec["class"] == "fact_drift"
    return rec


def classify(root: Path, result: dict) -> dict:
    from collections import Counter
    stale = [attribute_stale(root, c) for c in result.get("stale_citations", [])
             if c.get("verdict") == "stale_path"]
    reloc = [attribute_relocated(root, c) for c in result.get("relocated_citations", [])]
    stale_lines = [c for c in result.get("stale_citations", []) if c.get("verdict") == "stale_lines"]
    per_path: dict[str, dict] = {}
    for r in stale:
        p = per_path.setdefault(r["path"], {"classes": Counter(), "docs": set(), "occurrences": 0,
                                            "deletion_sha": r["del"]["deletion_sha"],
                                            "ancestor_of_head": r["del"]["ancestor_of_head"],
                                            "tracked_commits": r["del"]["tracked_commits"],
                                            "in_HEAD": r["in_HEAD"], "unfiltered_hits": r["unfiltered_hits"]})
        p["classes"][r["class"]] += 1
        p["docs"].add(r["doc"])
        p["occurrences"] += 1
    for p in per_path.values():
        p["classes"] = dict(p["classes"])
        p["docs"] = sorted(p["docs"])
    return {"stale_path": stale, "relocated": reloc,
            "stale_lines_out_of_scope_n": len(stale_lines),
            "stale_path_occurrences": len(stale),
            "distinct_stale_paths": sorted(per_path),
            "per_path_stale_truth": per_path,
            "relocated_occurrences": len(reloc)}


# ------------------------------------------------------------------ 自证
def make_time_axis_fixture() -> dict:
    """真 git 夹具: 同一文件退役前后的两条引用必须落**不同**类别 (防判据恒真/恒假)。"""
    tmp = Path(tempfile.mkdtemp(prefix="q6cube-"))
    try:
        env = dict(os.environ, GIT_AUTHOR_NAME="q6", GIT_AUTHOR_EMAIL="q6@local",
                   GIT_COMMITTER_NAME="q6", GIT_COMMITTER_EMAIL="q6@local")
        def g(*a):
            return subprocess.run(["git", *a], cwd=str(tmp), capture_output=True, text=True, env=env).returncode
        g("init", "-q")
        (tmp / "src").mkdir()
        (tmp / "docs").mkdir()
        (tmp / "src/Thing.cs").write_text("class Thing { }\n", encoding="utf-8")
        (tmp / "docs/pre.md").write_text("# pre\nsee src/Thing.cs:1 (kept)\ntail\n", encoding="utf-8")
        (tmp / "docs/post.md").write_text("# post\nplaceholder line\ntail\n", encoding="utf-8")
        (tmp / "docs/same.md").write_text("# same\nplaceholder line\ntail\n", encoding="utf-8")
        g("add", "-A")
        g("commit", "-q", "-m", "c1 base")
        (tmp / "src/Thing.cs").unlink()
        (tmp / "docs/same.md").write_text("# same\nsee src/Thing.cs:1 (same commit as retire)\ntail\n", encoding="utf-8")
        g("add", "-A")
        g("commit", "-q", "-m", "c2 delete src/Thing.cs + doc records it")
        (tmp / "docs/post.md").write_text("# post\nsee src/Thing.cs:1 (added after retire)\ntail\n", encoding="utf-8")
        g("add", "-A")
        g("commit", "-q", "-m", "c3 doc cites retired file")
        out = {}
        for name, line in (("pre.md", 2), ("post.md", 2), ("same.md", 2)):
            doc = f"docs/{name}"
            bl = blame_line_commit(tmp, doc, line)
            inr = intro_commit(tmp, doc, "src/Thing.cs")
            d = deletion_truth(tmp, "src/Thing.cs")["deletion_sha"]
            b_after = is_anc(tmp, d, bl) if bl else None
            i_after = is_anc(tmp, d, inr) if inr else None
            out[name] = time_axis(d, bl, inr, b_after, i_after)[0]
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_selftest(repo: Path) -> int:
    checks = []

    def chk(name, cond, obs):
        checks.append({"check": name, "pass": bool(cond), "observed": obs})

    live = "src/agent.host/Program.cs"
    chk("P1_live_path_in_HEAD", head_existence(repo, live) is True, live)
    t = deletion_truth(repo, "src/agent/registry/CapabilityPlugin.cs")
    chk("P2_deleted_has_commit_and_ancestor", bool(t["deletion_commits"]) and t["ancestor_of_head"] is True,
        {"sha": t["deletion_sha"], "anc": t["ancestor_of_head"]})
    tg = deletion_truth(repo, "src/agent/RoverZqNeverExisted9Xx.cs")
    chk("N1_never_tracked_not_deleted", not tg["deletion_commits"] and tg["tracked_commits"] == 0,
        {"tracked": tg["tracked_commits"]})
    chk("N2_unfiltered_zero_for_deleted", unfiltered_hits(repo, "CapabilityPlugin.cs") == [], "CapabilityPlugin.cs")
    chk("N2b_unfiltered_positive_control", len(unfiltered_hits(repo, "Program.cs")) > 0,
        unfiltered_hits(repo, "Program.cs")[:3])
    chk("F1_dead_after_delete", time_axis("AA", "BB", "CC", True, True)[0] == "dead_after_delete", "")
    chk("F2_retired_after_write", time_axis("AA", "BB", "CC", False, False)[0] == "retired_after_write", "")
    chk("F3_axis_conflict_waived", time_axis("AA", "BB", "CC", True, False)[0] == "axis_disagreement", "")
    chk("F4_no_deletion_waived", time_axis(None, "BB", "CC", None, None)[0] == "no_deletion_commit", "")
    chk("F5_single_evidence_used", time_axis("AA", "BB", None, True, None)[0] == "dead_after_delete", "blame_only")
    chk("F6_same_commit_waived", time_axis("AA", "AA", "AA", "same", "same")[0] == "same_commit_as_deletion", "")
    chk("F7_earlier_beats_same", time_axis("AA", "BB", "AA", False, "same")[0] == "retired_after_write", "")
    chk("F8_same_beats_later", time_axis("AA", "AA", "BB", "same", True)[0] == "same_commit_as_deletion", "")
    chk("P3_elision_bucket",
        attribute_relocated(repo, {"path": "src/a/.../B.cs", "doc": "d.md", "line_start": 1,
                                   "line_end": 1, "symbols": [], "relocated_to": []})["class"] == "path_elision", "")
    chk("N3_elision_negative_control",
        attribute_relocated(repo, {"path": "src/a/B.cs", "doc": "d.md", "line_start": 1, "line_end": 1,
                                   "symbols": [], "relocated_to": ["src/b/B.cs"],
                                   "relocated_fact_verdict": "ok"})["class"] == "fixable_direct", "")
    # 真 git 夹具: 判据必须两向可分 (防"恒红"与"恒绿"两种空心)
    fx = make_time_axis_fixture()
    chk("T1_fixture_pre_retire_is_history", fx.get("pre.md") == "retired_after_write", fx)
    chk("T2_fixture_post_retire_is_defect", fx.get("post.md") == "dead_after_delete", fx)
    chk("T3_fixture_same_commit_is_undecidable", fx.get("same.md") == "same_commit_as_deletion", fx)
    ok = all(c["pass"] for c in checks)
    print(json.dumps({"selftest": VERSION, "all_pass": ok,
                      "passed": sum(1 for c in checks if c["pass"]), "n": len(checks),
                      "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--result", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    root = Path(args.repo).resolve()
    if args.selftest:
        if not (root / ".git").exists():
            print(json.dumps({"stage": "precheck", "error": "not_a_git_repo", "exit_code": 3}, ensure_ascii=False))
            return 3
        return run_selftest(root)
    if not (root / ".git").exists() or not (root / "docs").is_dir():
        print(json.dumps({"stage": "precheck", "error": "repo_or_docs_missing",
                          "checked": {"git": (root / ".git").exists(), "docs": (root / "docs").is_dir()},
                          "exit_code": 3}, ensure_ascii=False))
        return 3
    if not args.result or not Path(args.result).is_file():
        print(json.dumps({"stage": "precheck", "error": "instrument_result_missing",
                          "result": args.result, "exit_code": 3}, ensure_ascii=False))
        return 3
    from collections import Counter
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    rep = classify(root, result)
    rep["probe"] = VERSION
    rep["source_result"] = args.result
    rep["class_counts"] = {"stale_path": dict(Counter(r["class"] for r in rep["stale_path"])),
                           "relocated": dict(Counter(r["class"] for r in rep["relocated"]))}
    defects = [r for r in rep["stale_path"] + rep["relocated"] if r["is_defect"]]
    measurement = [r for r in rep["stale_path"] + rep["relocated"] if r["class"] == "measurement_defect"]
    rep["n_defects"] = len(defects)
    rep["n_measurement_defects"] = len(measurement)
    # 口径冲突可见: stale_path 桶的定义是"被删", 若外部真值查不到删除提交 ⇒ 计数单列(不硬判红)
    rep["n_no_deletion_truth"] = sum(1 for r in rep["stale_path"] if r["class"] == "no_deletion_commit")
    rep["exit_code"] = 2 if (defects or measurement) else 0
    if args.out:
        Path(args.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"probe": VERSION, "class_counts": rep["class_counts"],
                      "n_defects": len(defects), "n_measurement_defects": len(measurement),
                      "defect_items": [{"doc": r["doc"], "line": r["doc_line"], "path": r["path"],
                                        "reason": r["reason"]} for r in defects],
                      "exit_code": rep["exit_code"]}, ensure_ascii=False, indent=2))
    return rep["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
