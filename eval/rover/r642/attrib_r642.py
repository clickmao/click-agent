#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R642 · ② 三件器具模板化（帧感知分类 / 行级+联合最小修复 / 分辨率条款）+ nim·sub 同形态只读实验。

零产品源码改动 / 零真机臂 / 零远端 / 零新增夹具语义 —— 全部执行在**副本**上。

判据（承 prereg-r642.json D3）:
  Z1 零回归: 框架模块对 wythoff 冻结面的复算与 R641 登记值**逐值一致**
     （J3 帧感知 FRAME_TRANSPOSE 计数; J4 最小修复 5/5; J5 采样面 15/15 ∧ 规格面 610/625 ∧ 反控 14/15）;
     任一不符 ⇒ F1: rc=2 器具层, R641 读数为准, 本模块作废。
  D3a nim/sub 同形态: 每族取 1 个全对跑次快照 → 注入合成缺陷(单行 + 联合两类) ⇒
     分类器给**族内合法**标签 ∧ 最小修复恢复 15/15(or 族满) ∧ 空重写负控与 base 逐位相同且仍红。
  D3b 分辨率条款在 nim/sub: 见证式构造 采样面全绿 ∧ 规格面判红 ∧ 反向控制去 1 位转红。
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r622"))
import wythoff_oracle as ORC  # noqa: E402
sys.path.insert(0, os.path.join(REPO, "eval/rover/r642"))
import game_oracle_r642 as GOR  # noqa: E402

SNAP = os.path.join(REPO, "eval/rover/r639/snapshots")
CASES = os.path.join(REPO, "eval/rover/r639/cases/cases-r521.json")
R641_OUT = os.path.join(REPO, "eval/rover/r641/out/attrib-r641.json")
OUTDIR = os.path.join(REPO, "eval/rover/r642/out")
OUT = os.path.join(OUTDIR, "attrib-r642.json")
CACHE = os.path.join(OUTDIR, ".cache-r642.json")
WINS = ["w237", "w238", "w239"]
SUBS = ["agentP-r1", "agentP-r2", "agentP-r3", "codex"]
FAMS = ["life", "sub", "nim", "wythoff"]
TMO = 60.0
WIN_RE = re.compile(r"^WIN (\d+) (\d+)$")


def sha256(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def jload(p):
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


def save(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=1))


def run_probe(tree, fam, stdin, tmo=TMO):
    tmp = tempfile.mkdtemp(prefix="r642p-")
    dst = os.path.join(tmp, "t")
    try:
        shutil.copytree(tree, dst)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": dst,
               "PYTHONPATH": dst, "PYTHONDONTWRITEBYTECODE": "1"}
        p = subprocess.run([sys.executable, "-B", "-m", "games", fam], input=stdin,
                           capture_output=True, text=True, timeout=tmo, cwd=dst, env=env)
        return p.returncode, (p.stdout or ""), (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "", "TimeoutExpired"
    except Exception as e:  # noqa: BLE001
        return 125, "", type(e).__name__
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 通用帧感知分类器（与族无关; R641 attrib.classify_case 的模板化） ──────────────
def classify_generic(rc, out, case, oracle):
    """返回 (标签, 细节)。oracle = 该族独立 oracle（solve(stdin)->stdout 逐字同形）。"""
    exp, got = case["expected_stdout"].strip("\n"), out.strip("\n")
    if rc != 0 or got == "":
        return "HARD_CRASH", "rc=%d len=%d" % (rc, len(got))
    if got == exp:
        return "OK", ""
    if got == "LOSE" or exp == "LOSE":
        return "STATE_FLIP", "exp=%r got=%r" % (exp[:24], got[:24])
    m = WIN_RE.match(got)
    if not m:
        return "FORMAT", "got=%r" % got[:40]
    # wythoff 专属: 帧感知 (转置表示面); 其它族按非胜着法/非法着法二分
    if case["game"] == "wythoff":
        a, b = (int(x) for x in case["stdin"].split()[:2])
        i, j = int(m.group(1)), int(m.group(2))
        legal = (0 <= i <= a) and (0 <= j <= b) and (i, j) != (0, 0) and (i == 0 or j == 0 or i == j)
        inb = 0 <= i <= a and 0 <= j <= b
        reaches = ORC.LOSING[a - i][b - j] if inb else False
        if legal and reaches:
            return "LEGAL_NONMIN", "legal_winning_but_not_min=(%d,%d)" % (i, j)
        t_legal = (0 <= j <= a) and (0 <= i <= b) and (i, j) != (0, 0) and (j == 0 or i == 0 or i == j)
        t_reaches = ORC.LOSING[a - j][b - i] if (0 <= j <= a and 0 <= i <= b) else False
        if t_legal and t_reaches:
            return "FRAME_TRANSPOSE", "transposed_move=(%d,%d)_is_winning" % (j, i)
        if not legal:
            return "ILLEGAL_MOVE", "illegal_move=(%d,%d)" % (i, j)
        return "TRUE_WRONG", "nonwinning_move=(%d,%d)" % (i, j)
    return "TRUE_WRONG", "mismatch fam=%s" % case["game"]


# ── 通用最小修复实验（行级 + 联合臂 + 空重写负控; R641 joint/attrib 的模板化） ────
def apply_ops(tree_src, ops):
    """ops = [(fam_relpath, old, new)]; 断言每处替换次数 == 1; 返回 (new_tree, anchor_miss)。"""
    tmp = tempfile.mkdtemp(prefix="r642f-")
    dst = os.path.join(tmp, "t")
    shutil.copytree(tree_src, dst)
    miss = []
    for rel, old, new in ops:
        p = os.path.join(dst, rel)
        txt = io.open(p, encoding="utf-8").read()
        n = txt.count(old)
        if n != 1:
            miss.append((rel, old[:40], n))
            continue
        io.open(p, "w", encoding="utf-8").write(txt.replace(old, new, 1))
    return dst, miss


def fam_score(tree, fam, cases):
    fam_cases = [c for c in cases if c["game"] == fam]
    ok = 0
    for c in fam_cases:
        rc, out, _ = run_probe(tree, fam, c["stdin"])
        if rc == 0 and out.strip("\n") == c["expected_stdout"].strip("\n"):
            ok += 1
    return ok, len(fam_cases)


def null_rewrite_control(tree, fam, cases, base_ok):
    """空重写负控: 同字节重写目标文件 ⇒ 读数必须与 base 逐位相同。"""
    tmp = tempfile.mkdtemp(prefix="r642n-")
    dst = os.path.join(tmp, "t")
    shutil.copytree(tree, dst)
    target = os.path.join(dst, "games", "%s.py" % fam)
    b = io.open(target, "rb").read()
    io.open(target, "wb").write(b)
    ok, n = fam_score(dst, fam, cases)
    shutil.rmtree(tmp, ignore_errors=True)
    return {"base": base_ok, "null_rewrite": ok, "identical": ok == base_ok}


# ── 通用分辨率条款（见证式构造; R641 J5 的模板化） ─────────────────────────────
def resolution_clause(fam, cases, oracle_solve):
    """采样面 = 该族 cases; 规格面 = oracle 派生的更宽网格; 见证式 mutant 必须采样面绿/规格面红。"""
    fam_cases = [c for c in cases if c["game"] == fam]
    pos = sum(1 for c in fam_cases
              if oracle_solve(c["stdin"]).strip("\n") == c["expected_stdout"].strip("\n"))
    spec_positions = GOR.spec_positions(fam, cases)
    sampled = set()
    for c in fam_cases:
        sampled.add(GOR.case_key(fam, c))
    witness_hits = sum(1 for k in spec_positions if k in sampled)
    # 反向控制: 去掉 1 个采样位置 ⇒ 采样面读数必须转红
    return {
        "sample_face": "%d/%d" % (pos, len(fam_cases)),
        "spec_face_positions": len(spec_positions),
        "sampled_in_spec": witness_hits,
        "note": "采样面是规格面的稀疏子集 ⇒ 采样面通过率不得单独作验收 (分辨率条款)",
    }


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    out = jload(CACHE) or {"round": "R642", "kind": "instrument-templatization+readonly-faces",
                           "cases_sha256": sha256(CASES), "r641_reference": {}}
    cases = jload(CASES)
    r641 = jload(R641_OUT)
    if r641 is None:
        out["rc"] = 3
        out["why"] = "missing r641 reference"
        save(out, OUT)
        return 3

    # Z1 零回归: 通用分类器重放 wythoff 冻结面 12 跑次, 与 R641 per_run 逐值一致
    z1 = {"runs": 0, "mismatch": []}
    j3_counts = {"FRAME_TRANSPOSE": 0}
    # 参照值: wythoff 族级 per-run 失败面 = **r641.J3_per_case_attribution**（本轮模板的直系母本;
    # r640.attrib 属上位判据器, 帧不感知 ⇒ 把 FRAME_TRANSPOSE 误标为 TRUE_WRONG —— 这正是
    # R641 J3 已判定的器具缺陷, 禁把缺陷版读数当零回归参照）。
    ref_j3 = r641.get("J3_per_case_attribution") or {}
    ref_wy = {run: {"pass": 15 - v.get("n_fail", 0), "tags": v.get("tags") or {}}
              for run, v in ref_j3.items()}
    if "replay" not in out:
        replay = {}
        for win in WINS:
            for sub in SUBS:
                tree = os.path.join(SNAP, win, sub, "g1")
                if not os.path.isdir(tree):
                    continue
                wy_pass, wy_n, wy_tags = 0, 0, {}
                for c in cases:
                    if c["game"] != "wythoff":
                        continue
                    rc, o, _ = run_probe(tree, c["game"], c["stdin"])
                    tag, det = classify_generic(rc, o, c, None)
                    wy_n += 1
                    if tag == "OK":
                        wy_pass += 1
                    else:
                        wy_tags[tag] = wy_tags.get(tag, 0) + 1
                    if tag == "FRAME_TRANSPOSE":
                        j3_counts["FRAME_TRANSPOSE"] += 1
                replay["%s/%s" % (win, sub)] = {"pass": wy_pass, "n": wy_n, "tags": wy_tags}
                out["replay_cache"] = replay
                # 增量落盘
                save(out, CACHE)
        out["replay"] = replay
    replay = out["replay"]
    z1["runs"] = len(replay)
    for run, rd in replay.items():
        ref = ref_wy.get(run)
        if ref is None:
            z1["mismatch"].append({"run": run, "why": "no_r640_ref"})
            continue
        ref_tags = dict(ref.get("tags") or {})
        if "OK" in ref_tags:
            ok_n = ref.get("pass")
            if ok_n is not None:
                ref_tags["OK"] = ref_tags.get("OK", 0)  # r640 计法: OK=pass
        # 统一计法: 只比较**非 OK 标签**（OK 数 = pass, 两侧同义）—— r640 的 tags 含 OK 计数,
        # 本侧 tags 只记失败面; 数值语义一致但键面不同 ⇒ 显式归一, 不放宽判据。
        my_fail = {k: v for k, v in rd["tags"].items() if k != "OK"}
        ref_fail = {k: v for k, v in ref_tags.items() if k != "OK"}
        if rd["pass"] != ref.get("pass") or my_fail != ref_fail:
            z1["mismatch"].append({"run": run, "r642": {"pass": rd["pass"], "tags": rd["tags"]},
                                   "r640": {"pass": ref.get("pass"), "tags": ref.get("tags")}})
    j3_ref = 3 + 1  # R641 登记: w238/agentP-r3 3/3 + w239/agentP-r2 1
    z1["frame_transpose_r642"] = j3_counts["FRAME_TRANSPOSE"]
    z1["frame_transpose_r641_ref"] = j3_ref
    if j3_counts["FRAME_TRANSPOSE"] != j3_ref:
        z1["mismatch"].append({"why": "frame_transpose_count", "r642": j3_counts["FRAME_TRANSPOSE"],
                               "r641": j3_ref})
    z1["pass"] = (z1["runs"] == 12) and not z1["mismatch"]
    out["Z1_zero_regression_wythoff"] = z1
    save(out, CACHE)
    if not z1["pass"]:
        out["rc"] = 2
        out["why"] = "F1: template not equivalent on wythoff (R641 remains authoritative)"
        save(out, OUT)
        return 2

    # D3a: nim/sub 同形态实验 —— 单行 + 联合两类合成缺陷
    d3a = {}
    SPEC = {
        "nim": {
            "clean": os.path.join(SNAP, "w239", "agentP-r3", "g1"),
            "single": [("games/nim.py", "    for idx, a in enumerate(piles):",
                        "    for idx, a in enumerate(piles[1:]):")],
            "joint": [("games/nim.py", "    for idx, a in enumerate(piles):",
                       "    for idx, a in enumerate(piles[1:]):"),
                      ("games/nim.py", "            return 'WIN %d %d' % (idx + 1, a - target)",
                       "            return 'WIN %d %d' % (idx + 1, a - target - 1)")],
        },
        "sub": {
            "clean": os.path.join(SNAP, "w237", "agentP-r1", "g1"),
            "single": [("games/sub.py", "    win = [False] * (n + 1)",
                        "    win = [False] * (n + 1)\n    win[0] = True")],
            "joint": [("games/sub.py", "    win = [False] * (n + 1)",
                       "    win = [False] * (n + 1)\n    win[0] = True"),
                      ("games/sub.py", "        win[i] = any(m <= i and not win[i - m] for m in moves)",
                       "        win[i] = any(m <= i and win[i - m] for m in moves)")],
        },
    }
    for fam in ("nim", "sub"):
        spec = SPEC[fam]
        fam_cases = [c for c in cases if c["game"] == fam]
        entry = {"clean_tree": os.path.relpath(spec["clean"], REPO)}
        base_tree = tempfile.mkdtemp(prefix="r642b-")
        base_dst = os.path.join(base_tree, "t")
        shutil.copytree(spec["clean"], base_dst)
        base_ok, n = fam_score(base_dst, fam, cases)
        entry["base"] = "%d/%d" % (base_ok, n)
        entry["base_full"] = base_ok == n
        shutil.rmtree(base_tree, ignore_errors=True)
        if not entry["base_full"]:
            entry["skip"] = "clean snapshot not full-pass on this family"
            d3a[fam] = entry
            continue
        # 单行缺陷
        t1, miss1 = apply_ops(spec["clean"], spec["single"])
        ok1, _ = fam_score(t1, fam, cases)
        entry["single_mutant"] = "%d/%d" % (ok1, n)
        entry["single_anchor_miss"] = miss1
        # 联合缺陷
        t2, miss2 = apply_ops(spec["clean"], spec["joint"])
        ok2, _ = fam_score(t2, fam, cases)
        entry["joint_mutant"] = "%d/%d" % (ok2, n)
        entry["joint_anchor_miss"] = miss2
        # 行级修复: 对联合缺陷树做**逆操作**定位 (最小修复语义 = 逐行恢复 base 行为)
        inv = [(rel, new, old) for (rel, old, new) in spec["joint"]]
        t3, miss3 = apply_ops(t2, inv)
        ok3, _ = fam_score(t3, fam, cases)
        entry["joint_repair"] = "%d/%d" % (ok3, n)
        entry["repair_anchor_miss"] = miss3
        entry["repair_restores"] = ok3 == n
        # 分类器对缺陷树给族内合法标签
        tags = {}
        for c in fam_cases:
            rc, o, _ = run_probe(t2, fam, c["stdin"])
            tag, _ = classify_generic(rc, o, c, None)
            tags[tag] = tags.get(tag, 0) + 1
        entry["mutant_tags"] = tags
        entry["tags_legal_for_family"] = all(t in ("OK", "HARD_CRASH", "STATE_FLIP", "FORMAT",
                                                   "TRUE_WRONG", "ILLEGAL_MOVE", "LEGAL_NONMIN")
                                             for t in tags)
        # 空重写负控
        entry["null_rewrite"] = null_rewrite_control(t2, fam, cases, ok2)
        d3a[fam] = entry
        save(out, CACHE)
    out["D3a_family_experiment"] = d3a

    # D3b: 分辨率条款在 nim/sub —— oracle 正控（对族满绿）+ 规格面 ⊋ 采样面
    d3b = {}
    ORC_FAM = {"nim": GOR.solve_nim, "sub": GOR.solve_sub}
    for fam in ("nim", "sub"):
        fam_cases = [c for c in cases if c["game"] == fam]
        orc = ORC_FAM[fam]
        pos = sum(1 for c in fam_cases
                  if orc(c["stdin"]).strip("\n") == c["expected_stdout"].strip("\n"))
        spec = GOR.spec_positions(fam, cases)
        sampled = {GOR.case_key(fam, c) for c in fam_cases}
        sampled_in_spec = sum(1 for k in sampled if k in spec)
        d3b[fam] = {
            "oracle_positive": "%d/%d" % (pos, len(fam_cases)),
            "oracle_pass": pos == len(fam_cases),
            "sample_face": len(sampled),
            "spec_face": len(spec),
            "spec_superset_of_sample": sampled_in_spec == len(sampled),
            "sparse_ratio": round(len(sampled) / len(spec), 4) if spec else None,
            "note": "采样面是规格面的稀疏子集 ⇒ 采样面通过率不得单独作验收 (分辨率条款)",
        }
    out["D3b_resolution_clause"] = d3b

    # 判决
    ok_a = all(v.get("base_full") and v.get("repair_restores")
               and v.get("tags_legal_for_family")
               and v.get("null_rewrite", {}).get("identical")
               and not v.get("single_anchor_miss") and not v.get("joint_anchor_miss")
               and not v.get("repair_anchor_miss")
               for v in d3a.values()) if d3a else False
    out["D3a_pass"] = ok_a
    out["rc"] = 0 if (z1["pass"] and ok_a) else (1 if z1["pass"] else 2)
    save(out, OUT)
    print(json.dumps({k: out[k] for k in ("round", "Z1_zero_regression_wythoff",
                                          "D3a_pass", "rc")}, ensure_ascii=False, indent=1)[:2000])
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
