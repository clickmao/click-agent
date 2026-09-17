#!/usr/bin/env python3
"""EXP1-Q29 事后校核 (checks_posthoc) —— 首跑两处红**照原样保留**, 此处只做两件事:
  (1) 控制重设计: 首跑的 reorder 负控**结构性不可判别** —— 器具的断言是「load→dump 逐字节复现」,
      而键序由解析顺序自带 ⇒ 任何键序重排都会被忠实复现 ⇒ 该控制恒绿, 测不到「禁重排」。
      真正的可判别面 = **序列化格式漂移** (缩进/转义/行尾/空白). 故补两只真控制:
        NC3b CRLF 行尾、NC3c ensure_ascii=True 转义 —— 二者都应 rc=3.
  (2) churn 纯度归因: 首跑 P4 报出 1 行「非 audited_by_round 差异」= 自引用行 r476.* ——
      用**修前器具**重跑同一副本, 断言该行差异消失且纯度 = 1.0 ⇒ 归因成立 (是本轮器具修复的
      设计要求「器具一改须重审自引用行」引起的, 不是仪器噪声).
独立命名空间: 写 posthoc_q29_verdict.json, 不覆盖首跑 verify_q29_verdict.json。
"""
import hashlib, json, os, subprocess, sys

ROUND = "EXP1-Q29"
TOOL = "eval/capability/bind_evidence.py"
REG = "docs/verification-registry.json"
OUTDIR = "eval/capability/exp1-q29"
PRE_TOOL = os.environ.get("Q29_PRE_TOOL", "/tmp/be_pre_q29.py")


def root():
    return subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                          text=True, check=True).stdout.strip()


ROOT = root()


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def wr(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_tool(tool_abs, reg_rel):
    code = ("import importlib.util,sys\n"
            "spec=importlib.util.spec_from_file_location('be_ph', %r)\n"
            "m=importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "m.REG=%r\n"
            "sys.argv=['be_ph','--apply','--round',%r]\n"
            "sys.exit(m.main())\n") % (tool_abs, reg_rel, ROUND)
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def purity(scratch_rel, real_rows):
    """(touched, pure_round, other_ids)"""
    a = {r.get("id"): r for r in json.loads(rd(os.path.join(ROOT, scratch_rel)))["rows"]}
    t = o = 0
    other = []
    for r in real_rows:
        ra = a.get(r.get("id"))
        f1, f2 = r.get("evidence_generated_with"), (ra or {}).get("evidence_generated_with")
        if f1 != f2:
            t += 1
            if f1 and f2 and set(f1) == set(f2) and all(k == "audited_by_round" or f1[k] == f2[k] for k in f1):
                o += 1
            else:
                other.append(r.get("id"))
    return t, o, other


def main():
    fails, res = [], {}
    real_abs = os.path.join(ROOT, REG)
    raw = rd(real_abs)
    real_sha_before = sha256(real_abs)
    doc = json.loads(raw)
    LF = "\n" if raw.endswith("\n") else ""
    sc = os.path.join(ROOT, OUTDIR, "scratch")

    # --- (1) 控制重设计 ---
    variants = {
        "crlf": raw.replace("\n", "\r\n"),
        "ascii_escape": json.dumps(doc, indent=1, ensure_ascii=True) + LF,
    }
    for name, v in variants.items():
        rel = "%s/scratch/reg_%s.json" % (OUTDIR, name)
        abs_ = os.path.join(ROOT, rel)
        wr(abs_, v)
        before = rd(abs_)
        rc, out = run_tool(os.path.join(ROOT, TOOL), rel)
        after = rd(abs_)
        marker = next((l for l in out.splitlines() if l.startswith("SER_ASSERT=")), None)
        ok = (rc == 3 and after == before)
        res["NC3b_crlf" if name == "crlf" else "NC3c_ascii_escape"] = {
            "rc": rc, "marker": marker, "unchanged_on_fail": after == before, "ok": ok,
            "why": "行尾/转义属格式漂移面 ⇒ 断言必须拒 (首跑 reorder 控制不可判别, 此为替代)"}
        if not ok:
            fails.append((name, "rc=%s(exp 3) marker=%s nowrite=%s" % (rc, marker, after == before)))

    # --- (2) churn 纯度归因 ---
    real_rows = json.loads(raw)["rows"]
    rel = "%s/scratch/reg_asis_ph.json" % OUTDIR
    # 2a: 修前器具
    wr(os.path.join(ROOT, rel), raw)
    rc_pre, out_pre = run_tool(PRE_TOOL, rel)
    t, o, other = purity(rel, real_rows)
    res["P4p_churn_pre_tool"] = {"rc": rc_pre, "touched": t, "pure_round": o, "other": other,
                                 "purity": (o / t if t else None),
                                 "ok": (other == [] and t > 0)}
    if other != []:
        fails.append(("P4p/churn_purity_pre", "仍有非轮号差异: %s" % other[:5]))
    # 2b: 修后器具 (同一副本重跑)
    wr(os.path.join(ROOT, rel), raw)
    rc_new, out_new = run_tool(os.path.join(ROOT, TOOL), rel)
    t2, o2, other2 = purity(rel, real_rows)
    res["P4_churn_new_tool"] = {"rc": rc_new, "touched": t2, "pure_round": o2, "other": other2,
                                "attribution": "差异行 = 自引用行 r476.evidence-binding-round-param 的"
                                               "artifact_sha12/instrument_sha12 重审 (器具 sha 变 ⇒ 设计要求)",
                                "ok": (o2 + len(other2) == t2 and other2 == ["r476.evidence-binding-round-param"])}
    if not res["P4_churn_new_tool"]["ok"]:
        fails.append(("P4/churn_new", "差异行非预期: %s" % other2[:5]))

    # --- 零副作用 ---
    same = sha256(real_abs) == real_sha_before
    if not same:
        fails.append(("NC4/side_effect", "真登记表 sha 变化"))
    res["NC4_real_untouched"] = {"sha12": real_sha_before[:12], "preserved": same}

    print("=== EXP1-Q29 事后校核 (checks_posthoc) ===")
    for k, v in res.items():
        print(" ", k, json.dumps(v, ensure_ascii=False))
    print("FAILS=%d" % len(fails))
    for f in fails:
        print("  FAIL", f[0], f[1])
    out_path = os.path.join(ROOT, OUTDIR, "posthoc_q29_verdict.json")
    wr(out_path, json.dumps({"round": ROUND, "kind": "checks_posthoc", "cases": res,
                            "fails": [{"key": f[0], "detail": f[1]} for f in fails]},
                            ensure_ascii=False, indent=1) + "\n")
    print("POSTHOC_PATH=%s" % out_path)
    print("Q29_POSTHOC_EXIT=%d" % (0 if not fails else 2))
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main())
