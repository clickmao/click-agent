#!/usr/bin/env python3
"""EXP1-Q25 器具硬化自检 (r444 precheck v3).

判据 D1..D8 见 eval/capability/exp1-q25/prereg_q25.json (预注册优先).
退出码契约: 0=全过 / 2=断言失败 / 3=测量或环境失败 (三态不同码, 见 unattended-job-reliability §3).
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
INSTR = ROOT / "eval/rover/r444/precheck_prefilter.py"
TRUTH = ROOT / "eval/rover/r444/precheck-prefilter.json"
NEG_DEFAULT = ROOT / "eval/rover/r444/runs/precheck-prefilter.neg.json"
Q25 = ROOT / "eval/capability/exp1-q25"
RUNS = Q25 / "runs"

REC = []
FAIL = []
ENV_FAIL = []


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() if pathlib.Path(p).exists() else None


def sha12(p):
    s = sha(p)
    return s[:12] if s else None


def stat(p):
    st = pathlib.Path(p).stat()
    return {"sha256": sha(p), "sha12": sha12(p), "mtime_ns": st.st_mtime_ns, "bytes": st.st_size}


def invoke(args):
    p = subprocess.run([sys.executable, str(INSTR)] + args, capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, (p.stdout + p.stderr)


def load(p):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        ENV_FAIL.append(f"无法解析 {p}: {e}")
        return {}


def chk(cid, cond, detail):
    REC.append({"id": cid, "pass": bool(cond), "detail": detail})
    if not cond:
        FAIL.append(cid)


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    if not INSTR.exists():
        print("[env] 仪器缺失:", INSTR)
        return 3
    instr_sha12 = sha12(INSTR)

    # --- 0) 真值臂默认档重生 (evidence_cmd 原样) ---
    rc0, out0 = invoke([])
    if rc0 != 0:
        ENV_FAIL.append(f"真值臂默认档 rc={rc0} (期望 0): {out0[-300:]}")
    truth = load(TRUTH)
    prov = truth.get("provenance", {})
    crit = truth.get("criteria", {})
    p1 = crit.get("P1_no_counterexample", {}).get("counterexamples")
    chk("D7_provenance",
        prov.get("instrument_sha12") == instr_sha12 and prov.get("arm") == "main",
        f"产物 instrument_sha12={prov.get('instrument_sha12')} vs 源码 {instr_sha12}; arm={prov.get('arm')}")
    chk("D8_main_arm_integrity",
        rc0 == 0 and truth.get("verdict") == "SEPARABLE" and p1 == 0,
        f"rc={rc0} verdict={truth.get('verdict')} P1反例={p1}")
    t_after_main = stat(TRUTH)

    # --- D2 真值产物不受控制臂污染 (缺陷回归断言) ---
    rc_n, out_n = invoke(["--neg-control"])
    neg = load(NEG_DEFAULT)
    neg_prov = neg.get("provenance", {})
    neg_cp = neg.get("criteria", {}).get("P1_no_counterexample", {}).get("counterexamples")
    nch = neg.get("channels", {})
    injected = sum(int(v) for v in nch.values()) if all(isinstance(v, int) for v in nch.values()) else None
    chk("D8_neg_arm_integrity",
        rc_n == 2 and isinstance(neg_cp, int) and neg_cp >= 1,
        f"rc={rc_n} (期望 2) P1反例={neg_cp} (期望 >=1) channels={nch} 串出现={injected}")
    t_after_neg = stat(TRUTH)
    chk("D2_truth_unpolluted",
        t_after_main["sha256"] == t_after_neg["sha256"] and t_after_main["mtime_ns"] == t_after_neg["mtime_ns"],
        f"跑控制臂前 sha12={t_after_main['sha12']} mtime_ns={t_after_main['mtime_ns']} | "
        f"后 sha12={t_after_neg['sha12']} mtime_ns={t_after_neg['mtime_ns']}")

    # --- D1 分臂产物互异 + 身份自证 ---
    chk("D1_arm_partition",
        sha(TRUTH) != sha(NEG_DEFAULT)
        and prov.get("arm") == "main" and prov.get("mode") == "arm-partitioned"
        and neg_prov.get("arm") == "neg_control" and neg_prov.get("mode") == "arm-partitioned",
        f"真值 sha12={t_after_neg['sha12']} arm={prov.get('arm')}/{prov.get('mode')} | "
        f"控制 sha12={sha12(NEG_DEFAULT)} arm={neg_prov.get('arm')}/{neg_prov.get('mode')}")

    # --- D3 确定性: 各臂连跑 2 次逐字节相同 ---
    m1 = RUNS / "main-1.json"
    m2 = RUNS / "main-2.json"
    n1 = RUNS / "neg-1.json"
    n2 = RUNS / "neg-2.json"
    rc_a, _ = invoke(["--out", str(m1)])
    s_m1 = sha(m1)
    rc_b, _ = invoke(["--out", str(m1)])
    s_m2 = sha(m1)
    rc_c, _ = invoke(["--neg-control", "--out", str(n1)])
    s_n1 = sha(n1)
    rc_d, _ = invoke(["--neg-control", "--out", str(n1)])
    s_n2 = sha(n1)
    same_main = (s_m1 is not None) and s_m1 == s_m2
    same_neg = (s_n1 is not None) and s_n1 == s_n2
    chk("D3_determinism", same_main and same_neg,
        f"同路径复跑 main {str(s_m1)[:12]}=={str(s_m2)[:12]} rc={rc_a}/{rc_b} | "
        f"neg {str(s_n1)[:12]}=={str(s_n2)[:12]} rc={rc_c}/{rc_d}")
    if not (rc_a == rc_b == 0 and rc_c == rc_d == 2):
        ENV_FAIL.append(f"分臂 rc 异常: main={rc_a}/{rc_b} neg={rc_c}/{rc_d}")
    invoke(["--out", str(m2)])                       # 异路径产物: 供 D3b 白名单比对
    invoke(["--neg-control", "--out", str(n2)])

    # --- D4 缺陷可复现 (负控): legacy 单槽下两臂共用同一 out ⇒ 后者覆盖前者 ---
    legacy = RUNS / "legacy" / "one_slot.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    t_before_legacy = stat(TRUTH)
    invoke(["--legacy-single-out", "--out", str(legacy)])
    leg_first = load(legacy).get("provenance", {})
    first_sha = sha(legacy) or ""
    invoke(["--neg-control", "--legacy-single-out", "--out", str(legacy)])
    leg_second = load(legacy).get("provenance", {})
    second_sha = sha(legacy) or ""
    siblings = [p for p in legacy.parent.rglob("*.json") if load(p).get("provenance", {}).get("arm") == "main"]
    chk("D4_defect_reproducible",
        leg_first.get("arm") == "main" and leg_second.get("arm") == "neg_control"
        and first_sha != second_sha and len(siblings) == 0,
        f"首跑 arm={leg_first.get('arm')} sha12={first_sha[:12]} ⇒ 次跑 arm={leg_second.get('arm')} "
        f"sha12={second_sha[:12]}; 残留 main 臂产物数={len(siblings)} (期望 0) ⇒ 真值臂身份丢失")
    t_after_legacy = stat(TRUTH)
    chk("D4b_legacy_isolated",
        t_before_legacy["sha256"] == t_after_legacy["sha256"] and t_before_legacy["mtime_ns"] == t_after_legacy["mtime_ns"],
        f"legacy 开关未触碰默认真值路径 (sha12={t_after_legacy['sha12']})")

    # --- checks_posthoc: D3b 异路径产物的差异只在「已声明非语义字段」(provenance.out / argv) 上 ---
    def _mask(obj):
        obj = json.loads(json.dumps(obj))
        p = obj.get("provenance", {})
        for k in ("out", "argv"):
            p.pop(k, None)
        return obj

    mask_main_ok = _mask(load(m1)) == _mask(load(m2))
    mask_neg_ok = _mask(load(n1)) == _mask(load(n2))
    raw_main_differs = sha(m1) != sha(m2)
    POSTHOC = {
        "D3b_path_fields_only": {
            "pass": mask_main_ok and mask_neg_ok and raw_main_differs,
            "detail": f"mask(out,argv) 后 main 相等={mask_main_ok} neg 相等={mask_neg_ok} "
                      f"(未 mask 时逐字节不同={raw_main_differs} ⇒ 差异仅来自已声明路径字段)",
            "posthoc": True,
        }
    }

    # --- D5 fail-closed: 网格缺失 ⇒ rc 3 且不落产物 ---
    fc = RUNS / "failclosed.json"
    if fc.exists():
        fc.unlink()
    rc_e, out_e = invoke(["--grid-dir", "/nonexistent-grid-dir", "--out", str(fc)])
    chk("D5_fail_closed", rc_e == 3 and not fc.exists(),
        f"rc={rc_e} (期望 3) out 存在={fc.exists()} (期望 False) msg={out_e.strip()[:90]}")

    # --- D6 守恒式: Σruns == P3 ---
    runs_rows = sum(int(r.get("n_r1_rows", 0)) for r in truth.get("runs", []))
    runs_avoid = sum(int(r.get("avoidable_r1", 0)) for r in truth.get("runs", []))
    p3 = crit.get("P3_avoidable_r1_calls", {})
    per_row_ok = all(int(r.get("avoidable_r1", 0)) <= int(r.get("n_r1_rows", 0)) for r in truth.get("runs", []))
    chk("D6_conservation",
        runs_rows == p3.get("total_r1_rows") and runs_avoid == p3.get("avoidable") and per_row_ok,
        f"Σ行={runs_rows} vs P3 {p3.get('total_r1_rows')}; Σ可省={runs_avoid} vs P3 {p3.get('avoidable')}; 逐行 ≤ 成立={per_row_ok}")

    # --- checks_posthoc: D9 副作用闸白名单「双侧样例」 (证明白名单是定向的, 不是整体关闸) ---
    try:
        sys.path.insert(0, str(ROOT / "eval/capability"))
        import instruments_check as IC  # noqa: PLC0415
        import side_effect_gate as seg  # noqa: PLC0415

        probe_path = "eval/capability/exp1-q25/runs/d9_probe.json"
        whitelisted = "eval/rover/r444/precheck-prefilter.json"
        gate = seg.SideEffectGate(ROOT, face_outputs=IC.FACE_OUTPUTS, scratch=IC.SCRATCH_PREFIXES)
        gate.begin()
        gate.run("python3 eval/rover/r444/precheck_prefilter.py --out " + whitelisted)
        gate.run("printf d9 > " + probe_path)
        rep = gate.end()
        sids = [w["path"] for w in rep["self_writes"]]
        POSTHOC["D9_whitelist_targeted"] = {
            "pass": (whitelisted not in sids) and (probe_path in sids),
            "detail": f"白名单路径写事件被判脏={whitelisted in sids} (期望 False); "
                      f"非白名单同 scope 路径写事件被判脏={probe_path in sids} (期望 True); "
                      f"verdict={rep['verdict']} self_writes={sids}",
            "posthoc": True,
        }
    except Exception as exc:  # noqa: BLE001
        POSTHOC["D9_whitelist_targeted"] = {"pass": False, "detail": f"探针异常: {exc!r}", "posthoc": True}
        ENV_FAIL.append(f"D9 探针异常: {exc!r}")

    rc = 3 if ENV_FAIL else (2 if FAIL else 0)
    summary = {
        "round": "EXP1-Q25",
        "instrument": "eval/rover/r444/precheck_prefilter.py",
        "instrument_sha12": instr_sha12,
        "rc_contract": {"all_pass": 0, "assert_fail": 2, "measure_or_env_fail": 3},
        "rc": rc,
        "criteria": REC,
        "checks_posthoc": POSTHOC,
        "failed": FAIL,
        "env_failures": ENV_FAIL,
        "artifacts": {
            "truth": {"path": "eval/rover/r444/precheck-prefilter.json", "sha12": sha12(TRUTH),
                      "bytes": stat(TRUTH)["bytes"], "arm": prov.get("arm")},
            "neg_default": {"path": "eval/rover/r444/runs/precheck-prefilter.neg.json", "sha12": sha12(NEG_DEFAULT),
                            "arm": neg_prov.get("arm")},
            "main_runs_sha12": [sha12(m1), sha12(m2)],
            "neg_runs_sha12": [sha12(n1), sha12(n2)],
            "legacy_slot": {"path": "eval/capability/exp1-q25/runs/legacy/one_slot.json",
                            "sha12_after_overwrite": second_sha[:12], "arm_after": leg_second.get("arm")},
        },
        "readings": {
            "truth_P1_counterexamples": p1, "truth_verdict": truth.get("verdict"),
            "truth_total_r1_rows": p3.get("total_r1_rows"), "truth_avoidable": p3.get("avoidable"),
            "truth_saved_ratio": p3.get("saved_ratio"),
            "neg_P1_counterexamples": neg_cp, "neg_rc": rc_n,
        },
    }
    (RUNS / "d9_probe.json").unlink(missing_ok=True)
    (RUNS / "harden_check_q25.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    print("== EXP1-Q25 器具硬化自检 (D1..D8) ==")
    for r in REC:
        print(f"  [{'PASS' if r['pass'] else 'FAIL'}] {r['id']:28s} {r['detail']}")
    for k, v in POSTHOC.items():
        print(f"  [{'PASS' if v['pass'] else 'FAIL'}] {k:28s} (post-hoc) {v['detail']}")
    for e in ENV_FAIL:
        print("  [ENV ]", e)
    print(f"  rc={rc}  failures={FAIL}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
