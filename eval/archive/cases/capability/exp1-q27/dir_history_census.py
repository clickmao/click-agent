#!/usr/bin/env python3
"""EXP1-Q27: 目录聚合证据「清单式 pin 可上闸性」普查 (只读既有数据, 不跑任何测量运行)。

背景: docs/verification-registry.json 中 evidence_kind=directory 的 8 行此前 pin_status=live
(零字节闸), 是「证据易主」最可能的形态。候选方案 = 目录清单摘要作冻结 pin, 但它成立的前提是
「目录不会随测量抖动」⇒ 上闸前必须先量 (先量后定)。

方法 (全部源于仓库既有数据):
  M1 索引清单   : `git ls-files -- <dir>` 的文件数 + 清单摘要 (`bind_evidence.dir_manifest`, 同源)
  M2 三态版本   : 已跟踪 / 未跟踪(??, 非忽略) / 忽略(!!) / 工作区已改  —— 三态必须分开:
                  首版把「现盘 walk - ls-files」当未跟踪 ⇒ 119 个 .gitignore 产物 (__pycache__/日志/临时配置)
                  被误报成「未入库证据」⇒ 8/8 判 live 的空心读数 (Q27 仪器缺陷, 已入档)
  M3 逐文件沿革 : 每个文件在首次加入之后被 M(改写) / D(删除) 的次数

预注册判定规则 (先写后跑):
  R1 索引文件 ≥1 ∧ 无未跟踪(非忽略) ∧ 无已改 ∧ 沿革无 M/D  =>  frozen / archived-per-round
  R2 有未跟踪(非忽略) 或 工作区已改                        =>  live / worktree-only
  R3 沿革含 M 或 D (当前干净)                              =>  live / evidence-overtaken
  R4 索引文件 = 0                                          =>  live / directory-aggregate-empty
  优先级 R2 > R3 > R4 > R1 (缺口优先于可闸)。
负控: `--selftest` 用两侧样例回放规则, 并断言「恒判 frozen」的哑规则在两例上给出不同结论
      (规则必须会动, 否则判定只是装饰)。
"""
import argparse, collections, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # eval/capability
import bind_evidence as be                          # 同源: 清单摘要/轮号段/词表均来自产品侧器具

OUT = os.path.join(HERE, "dir_census_q27.json")
REG = "docs/verification-registry.json"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout


def status_map(root):
    """三态 + 已改: path -> one of 'ignored' | 'untracked' | 'dirty'."""
    m = {}
    for line in git(root, "status", "--porcelain", "--ignored", "-uall").splitlines():
        code, p = line[:2], line[3:].strip().strip('"')
        m[p] = "ignored" if code == "!!" else ("untracked" if code == "??" else "dirty")
    return m


def history(root, dirs):
    per = collections.defaultdict(lambda: {"commits": [], "status": collections.defaultdict(list)})
    cur = None
    for line in git(root, "log", "--no-renames", "--name-status", "--format=@%H", "--", *dirs).splitlines():
        if line.startswith("@"):
            cur = line[1:]
            continue
        if not line.strip() or cur is None:
            continue
        parts = line.split("\t")
        st, path = parts[0][0], parts[-1]
        for d in dirs:
            if path == d or path.startswith(d + "/"):
                per[d]["status"][path].append(st)
                if cur not in per[d]["commits"]:
                    per[d]["commits"].append(cur)
    return per


def rule(facts):
    """纯规则: facts -> (pin_status, pin_reason)。样本可机械回放 (见 --selftest)。"""
    if facts["n_untracked"] > 0 or facts["n_dirty"] > 0:
        return "live", "worktree-only"
    if facts["n_rewritten"] > 0 or facts["n_deleted"] > 0:
        return "live", "evidence-overtaken"
    if facts["n_index_files"] == 0:
        return "live", "directory-aggregate-empty"
    return "frozen", "archived-per-round"


def census(root, dirs):
    st = status_map(root)
    hist = history(root, dirs)
    out = {}
    for d in dirs:
        idx = [p for p in sorted(set(git(root, "ls-files", "--", d).split())) if os.path.isfile(os.path.join(root, p))]
        man = be.dir_manifest(root, d)
        inside = [p for p in st if p == d or p.startswith(d + "/")]
        n_ign = sum(1 for p in inside if st[p] == "ignored")
        n_unt = sum(1 for p in inside if st[p] == "untracked")
        n_dir = sum(1 for p in inside if st[p] == "dirty")
        fs = hist[d]["status"]
        rewritten = sorted(p for p, s in fs.items() if "M" in s[1:] and p in idx)
        deleted = sorted(p for p, s in fs.items() if "D" in s)
        facts = {"n_index_files": len(idx), "n_untracked": n_unt, "n_dirty": n_dir,
                 "n_rewritten": len(rewritten), "n_deleted": len(deleted)}
        mode, reason = rule(facts)
        out[d] = {"dir": d, "manifest_sha12": man[0] if man else None, "manifest_files": man[1] if man else 0,
                  "n_ignored": n_ign, "n_commits": len(hist[d]["commits"]),
                  "rewritten_sample": rewritten[:3], "facts": facts,
                  "pin_status": mode, "pin_reason": reason}
    return out


def selftest():
    """两侧样例 + 哑规则负控: 规则会动才算判据。"""
    cases = [
        ("clean-addonly", {"n_index_files": 27, "n_untracked": 0, "n_dirty": 0, "n_rewritten": 0, "n_deleted": 0},
         ("frozen", "archived-per-round")),
        ("untracked-present", {"n_index_files": 27, "n_untracked": 1, "n_dirty": 0, "n_rewritten": 0, "n_deleted": 0},
         ("live", "worktree-only")),
        ("dirty-present", {"n_index_files": 27, "n_untracked": 0, "n_dirty": 2, "n_rewritten": 0, "n_deleted": 0},
         ("live", "worktree-only")),
        ("history-rewritten", {"n_index_files": 8, "n_untracked": 0, "n_dirty": 0, "n_rewritten": 5, "n_deleted": 0},
         ("live", "evidence-overtaken")),
        ("empty-index", {"n_index_files": 0, "n_untracked": 0, "n_dirty": 0, "n_rewritten": 0, "n_deleted": 0},
         ("live", "directory-aggregate-empty")),
    ]
    bad = []
    for name, facts, want in cases:
        got = rule(facts)
        if got != want:
            bad.append("%s: got %s want %s" % (name, got, want))
    dummy = [("frozen", "archived-per-round") for _ in cases]      # 负控: 恒真哑规则
    differs = sum(1 for (_, _, want), dd in zip(cases, dummy) if want != dd)
    print("SELFTEST cases=%d mismatch=%d dummy_rule_differs_on=%d" % (len(cases), len(bad), differs))
    for b in bad:
        print("  MISMATCH", b)
    if bad or differs < 2:
        print("SELFTEST=FAIL (规则未通过两侧样例或哑规则负控)")
        return 2
    print("SELFTEST=PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    root = be.repo_root()
    rows = [r for r in json.loads(open(os.path.join(root, REG), encoding="utf-8").read())["rows"]
            if (r.get("evidence_generated_with") or {}).get("evidence_kind") == "directory"]
    dirs = sorted({r["evidence_path"].rstrip("/") for r in rows})
    cen = census(root, dirs)
    # 交叉核对: 普查规则 vs 产品侧器具 derive() 必须逐行一致 (同一语义两处实现 ⇒ 必须互相钉住)
    tracked, dirty = be.git_state(root)
    disagree = []
    for r in rows:
        d = r["evidence_path"].rstrip("/")
        want = (cen[d]["pin_status"], cen[d]["pin_reason"])
        got = be.derive(root, r, tracked, dirty)
        if want != (got["pin_status"], got["pin_reason"]):
            disagree.append({"id": r["id"], "census": want, "derive": (got["pin_status"], got["pin_reason"])})
    per_row = [{"id": r["id"], "dir": r["evidence_path"].rstrip("/"),
                "pin_status": cen[r["evidence_path"].rstrip("/")]["pin_status"],
                "pin_reason": cen[r["evidence_path"].rstrip("/")]["pin_reason"],
                "manifest_sha12": cen[r["evidence_path"].rstrip("/")]["manifest_sha12"]} for r in rows]
    dist = collections.Counter(x["pin_status"] for x in per_row)
    res = {"round": "EXP1-Q27", "instrument": "eval/capability/exp1-q27/dir_history_census.py",
           "rows": len(rows), "dirs": len(dirs), "dist_by_row": dict(dist),
           "dist_by_dir": dict(collections.Counter(v["pin_status"] for v in cen.values())),
           "census_vs_derive_disagreements": disagree,
           "census": cen, "per_row": per_row}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("ROWS=%d DIRS=%d dist_by_row=%s dist_by_dir=%s" % (len(rows), len(dirs), dict(dist),
                                                            res["dist_by_dir"]))
    for d, v in sorted(cen.items()):
        print("  %-22s idx=%-3d ignored=%-3d untr=%-2d dirty=%-2d rew=%-2d del=%-2d commits=%-3d %s/%s man=%s"
              % (d, v["facts"]["n_index_files"], v["n_ignored"], v["facts"]["n_untracked"],
                 v["facts"]["n_dirty"], v["facts"]["n_rewritten"], v["facts"]["n_deleted"],
                 v["n_commits"], v["pin_status"], v["pin_reason"], v["manifest_sha12"]))
    print("OUT=%s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
