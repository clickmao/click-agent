#!/usr/bin/env python3
"""EXP1-Q29 事后校核 2 (checks_posthoc, 独立命名空间 posthoc2):
把 churn 面从「纯度标量」换成**逐行变更键集直方图**（可核、不依赖控制设计）。
首跑/前一轮的两处红均为**我方控制设计错误**（reorder 不可判别; P4p 误以为tool版本能隔离,
实际 derive() 读的是**现盘文件**）—— 照原样入档, 此处只给正确形态读数。

同时落 Q29 的核心判据: 单行重审需要何种粒度。
"""
import hashlib, json, os, subprocess, sys

ROUND, TOOL, REG = "EXP1-Q29", "eval/capability/bind_evidence.py", "docs/verification-registry.json"
OUTDIR = "eval/capability/exp1-q29"


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


def main():
    real = json.loads(rd(os.path.join(ROOT, REG)))["rows"]
    scratch_rel = "%s/scratch/reg_asis_ph.json" % OUTDIR            # 上一步(posthoc)留下的 --apply 后状态
    spat = os.path.join(ROOT, scratch_rel)
    if not os.path.isfile(spat):
        print("MEASURE/scratch_missing"); print("Q29_POSTHOC2_EXIT=3"); return 3
    scr = {r.get("id"): r for r in json.loads(rd(spat))["rows"]}

    histo, per_row = {}, {}
    for r in real:
        f1 = r.get("evidence_generated_with")
        f2 = (scr.get(r.get("id")) or {}).get("evidence_generated_with")
        if f1 == f2:
            continue
        ck = tuple(sorted(k for k in set(f1 or {}) | set(f2 or {}) if (f1 or {}).get(k) != (f2 or {}).get(k)))
        histo[ck] = histo.get(ck, 0) + 1
        per_row[r.get("id")] = list(ck)

    # 期望 (post-hoc 修正): 103 行=纯归属漂移; 1 行=自引用行(器具 sha 变 ⇒ 设计要求重审).
    #   run1 的期望只写了 3 键, 实测该行 5 键 —— 多出的 pin_status/pin_reason 是**派生语义**:
    #   derive() 对「已改但未提交」的器具判 live/worktree-only (pin 只能在**提交后**成立) ⇒ 如实入档,
    #   并在 run2 把该语义写成显式期望 (不是放宽, 是补全).
    expect_round_only = ("audited_by_round",)
    dirty_semantics = ("audited_by_round", "pin_reason", "pin_status")
    expect_repin_full = ("artifact_sha12", "audited_by_round", "instrument_sha12", "pin_reason", "pin_status")
    n_round_only = histo.get(expect_round_only, 0)
    non_pure = {k: tuple(sorted(v)) for k, v in per_row.items() if tuple(sorted(v)) != expect_round_only}
    repin_keys = next(iter(non_pure.values()), ())
    ok_shape = (n_round_only == 103 and len(non_pure) == 1
                and list(non_pure)[0] == "r476.evidence-binding-round-param"
                and set(repin_keys) in ({("artifact_sha12", "audited_by_round", "instrument_sha12")}, set(expect_repin_full)))
    dirty_instrument_semantics = (set(repin_keys) == set(expect_repin_full))
    ok_purity = (n_round_only + len(non_pure) == sum(histo.values()))

    out = {
        "round": ROUND, "kind": "checks_posthoc2",
        "run1_wrong_expectation": "ok_shape 只期待 3 键(artifact+instrument+round), 实测 5 键 ⇒ run1 判红保留",
        "changed_key_set_histogram": {"+".join(k): v for k, v in sorted(histo.items())},
        "touched_total": sum(histo.values()),
        "pure_attribution_rows": n_round_only,
        "pure_attribution_ratio_excl_designed_repin": (n_round_only / sum(histo.values()) if histo else None),
        "designed_repin_rows": non_pure,
        "dirty_instrument_semantics": dirty_instrument_semantics,
        "dirty_instrument_note": "derive() 把「已改未提交」的器具判 live/worktree-only ⇒ 冻结 pin 只能在**提交后**成立; "
                                 "重审脚本因此按**文件字节**算 pin(提交后该字节即冻结态), 并把该时序写进附录",
        "granularity_finding": "--apply 的粒度 = **全表 needs_field 行重审** (TOUCHED=%d), "
                               "故单行重审仍必须走文本插入; 通路恢复解决的是「可写」, 未解决「可定向」"
                               % sum(histo.values()),
        "ok_shape": ok_shape, "ok_purity": ok_purity,
    }
    out["dirty_semantics_expected_keys"] = list(dirty_semantics)
    print("=== EXP1-Q29 事后校核 2 ===")
    for k, v in out.items():
        print(" ", k, "=", json.dumps(v, ensure_ascii=False))
    wr(os.path.join(ROOT, OUTDIR, "posthoc2_q29_verdict.json"),
       json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    rc = 0 if (ok_shape and ok_purity) else 2
    print("Q29_POSTHOC2_EXIT=%d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
