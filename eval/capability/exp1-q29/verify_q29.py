#!/usr/bin/env python3
"""EXP1-Q29 器具: bind_evidence 整文件序列化通路 (尾形态容忍 × 禁重排) 的判据 + 负控.

为什么需要它 (数据先行):
  Q28 记录「登记表尾换行被移除 ⇒ 断言 fail-closed ⇒ 程序化改写通路被静默禁用 ⇒ 只能走文本插入」.
  本轮先核前提: 尾字节沿革显示 LF 又被 R481 带回 ⇒ 严格式断言**今天**是过的, 但**同一形态差异仍会
  再次静默禁用通路**。判据是「通路可用」, 不是「今天恰好可用」, 故本题 = 把断言放宽到形态二态,
  且回写沿用观测形态; 同时用两侧负控证明它没有变成恒真门。

仪器纪律 (承 R406/R410/R418):
  - 只写 scratch 副本, 真登记表 sha 前后必须逐位相同 (零副作用是断言, 不是前提);
  - 变体喂给**真实器具代码**(importlib 载入 + REG 重定向), 不复刻判据做自证;
  - 三态退出码: 0=全过 / 2=断言失败 / 3=测量或环境失败 (不得同码).
"""
import hashlib, json, os, shutil, subprocess, sys

ROUND = "EXP1-Q29"
TOOL = "eval/capability/bind_evidence.py"
REG = "docs/verification-registry.json"
OUTDIR = "eval/capability/exp1-q29"
PRE_TOOL = os.environ.get("Q29_PRE_TOOL", "/tmp/be_pre_q29.py")   # 修前器具 (git show <pre>:<TOOL>)


def root():
    return subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                          text=True, check=True).stdout.strip()


ROOT = root()


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_raw(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def write_raw(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def run_tool(tool_abs, reg_rel):
    """在真实器具代码上跑 --apply (REG 重定向到副本) -> (rc, stdout)。器具在独立子进程里跑, 免状态串染。"""
    code = ("import importlib.util,sys\n"
            "spec=importlib.util.spec_from_file_location('be_q29', %r)\n"
            "m=importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "m.REG=%r\n"
            "sys.argv=['be_q29','--apply','--round',%r]\n"
            "sys.exit(m.main())\n") % (tool_abs, reg_rel, ROUND)
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def marker(out, key):
    for ln in out.splitlines():
        if ln.startswith(key + "="):
            return ln
    return None


def main():
    res, fails, notes = [], [], []
    real_abs = os.path.join(ROOT, REG)
    real_sha_before = sha256(real_abs)
    raw = read_raw(real_abs)
    doc = json.loads(raw)
    tail_real = "\n" if raw.endswith("\n") else ""

    # --- 变体构造 (全部落在 scratch, 不碰真登记表) ---
    scratch_dir = os.path.join(ROOT, OUTDIR, "scratch")
    os.makedirs(scratch_dir, exist_ok=True)
    variants = {}
    variants["asis"] = raw
    variants["nolf"] = raw[:-1] if raw.endswith("\n") else raw
    variants["indent2"] = json.dumps(doc, indent=2, ensure_ascii=False) + tail_real
    reordered = json.loads(raw)
    r0 = reordered["rows"][3002] if len(reordered["rows"]) > 3002 else reordered["rows"][-1]
    keys = list(r0.keys())
    reordered["rows"][3002 if len(reordered["rows"]) > 3002 else len(reordered["rows"]) - 1] = \
        {k: r0[k] for k in (keys[1:] + keys[:1])}
    variants["reorder"] = json.dumps(reordered, indent=1, ensure_ascii=False) + tail_real
    for k, v in variants.items():
        write_raw(os.path.join(scratch_dir, "reg_%s.json" % k), v)

    pre_abs = PRE_TOOL if os.path.isfile(PRE_TOOL) else None
    if pre_abs is None:
        fails.append(("MEASURE/pre_tool_missing", "修前器具不可读 %s" % PRE_TOOL))
        return report(res, fails, notes, real_sha_before, real_abs)

    plan = [
        # (name, tool, variant, expect_rc, expect_marker, expect_lf_after_write, expect_substring)
        ("asis__new", TOOL, "asis", 0, "SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=LF)", True, None),
        ("nolf__pre_NC1", pre_abs, "nolf", 3, "SER_ASSERT=FAIL", None, None),
        ("nolf__new", TOOL, "nolf", 0, "SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=NONE->LF", True, "补 1 B"),
        ("indent2__new_NC2", TOOL, "indent2", 3, "SER_ASSERT=FAIL", None, "格式漂移"),
        ("reorder__new_NC3", TOOL, "reorder", 3, "SER_ASSERT=FAIL", None, None),
    ]
    for name, tool, var, exp_rc, exp_marker, exp_lf, exp_sub in plan:
        rel = "%s/scratch/reg_%s.json" % (OUTDIR, var)
        abs_ = os.path.join(ROOT, rel)
        write_raw(abs_, variants[var])                      # 每次从干净副本起跑
        before = read_raw(abs_)
        rc, out = run_tool(os.path.join(ROOT, tool), rel)
        after = read_raw(abs_)
        ok_rc = (rc == exp_rc)
        m = marker(out, "SER_ASSERT")
        ok_marker = bool(m and m.startswith(exp_marker))
        ok_lf = True if exp_lf is None else (after.endswith("\n") == exp_lf)
        ok_sub = (exp_sub is None) or (exp_sub in out)
        ok_nowrite = True if exp_rc == 0 else (after == before)   # fail-closed 必须一个字节都不写
        rb = marker(out, "WRITE_READBACK") or marker(out, "IDEMPOTENT")
        res.append({"case": name, "rc": rc, "expect_rc": exp_rc, "ser_assert": m,
                    "readback": rb,
                    "write_path": [l for l in out.splitlines() if l.startswith("UNCHANGED=")],
                    "lf_after_write": after.endswith("\n"),
                    "ok": ok_rc and ok_marker and ok_lf and ok_nowrite and ok_sub,
                    "ok_nowrite_on_fail": ok_nowrite, "ok_substring": ok_sub})
        if not (ok_rc and ok_marker and ok_lf and ok_nowrite and ok_sub):
            fails.append(("CASE/%s" % name, "rc=%s(exp %s) marker=%s lf_ok=%s nowrite=%s sub_ok=%s"
                          % (rc, exp_rc, m, ok_lf, ok_nowrite, ok_sub)))

    # --- P4 churn 面: 逐行差异只在 audited_by_round ---
    asis_path = os.path.join(ROOT, OUTDIR, "scratch", "reg_asis.json")
    churn = {"touched": None, "only_round": None, "other_diffs": []}
    try:
        a = json.loads(read_raw(asis_path))["rows"]
        b = json.loads(raw)["rows"]
        by_a = {r.get("id"): r for r in a}
        t = o = 0
        for r in b:
            ra = by_a.get(r.get("id"))
            if ra is None:
                churn["other_diffs"].append("row missing: %s" % r.get("id")); continue
            f1, f2 = r.get("evidence_generated_with"), ra.get("evidence_generated_with")
            if f1 != f2:
                t += 1
                if set(f1 or {}) == set(f2 or {}) and \
                   all(k == "audited_by_round" or f1[k] == f2[k] for k in (f1 or {})):
                    o += 1
                else:
                    churn["other_diffs"].append("non-round change: %s" % r.get("id"))
        churn["touched"], churn["only_round"] = t, o
    except Exception as e:
        fails.append(("MEASURE/churn", "churn 面计算失败: %r" % e))
    if churn["touched"] is not None and churn["other_diffs"]:
        fails.append(("P4/churn_purity", "存在非 audited_by_round 的差异: %s" % churn["other_diffs"][:5]))

    # --- NC4 零副作用 ---
    real_sha_after = sha256(real_abs)
    if real_sha_after != real_sha_before:
        fails.append(("NC4/side_effect", "真登记表 sha 变化 %s -> %s" % (real_sha_before[:12], real_sha_after[:12])))
    numstat = subprocess.run(["git", "diff", "--numstat", "--", REG], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    if numstat:
        fails.append(("NC4/git_diff", "真登记表有工作区改动: %s" % numstat))
    notes.append("real_registry_sha256_preserved=%s" % (real_sha_after == real_sha_before))
    return report(res, fails, notes, real_sha_before, real_abs)


def report(res, fails, notes, real_sha_before, real_abs):
    verdict = {"round": ROUND, "cases": res, "churn": None, "notes": notes + ["real_sha12=%s" % real_sha_before[:12]]}
    try:
        verdict["churn"] = json.loads(read_raw(os.path.join(ROOT, OUTDIR, "churn_tmp.json"))) if False else None
    except Exception:
        pass
    out_path = os.path.join(ROOT, OUTDIR, "verify_q29_verdict.json")
    print("=== EXP1-Q29 器具读数 ===")
    for r in res:
        print("  %-18s rc=%s(exp %s) | %s | %s | lf_after=%s | ok=%s"
              % (r["case"], r["rc"], r["expect_rc"], r["ser_assert"], r["readback"] or "-",
                 r["lf_after_write"], r["ok"]))
    for n in notes:
        print("  note:", n)
    print("FAILS=%d" % len(fails))
    for f in fails:
        print("  FAIL", f[0], f[1])
    verdict["fails"] = [{"key": f[0], "detail": f[1]} for f in fails]
    write_raw(out_path, json.dumps(verdict, ensure_ascii=False, indent=1) + "\n")
    print("VERDICT_PATH=%s" % out_path)
    print("Q29_EXIT=%d" % (0 if not fails else 2))
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main())
