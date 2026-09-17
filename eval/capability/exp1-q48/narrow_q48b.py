#!/usr/bin/env python3
"""EXP1-Q48b: 把 v1 被否证的普适主张收窄为逐臂可判的机理主张, 并机械裁定。

输入 = v1 落盘的 verdict_q48.json (不重算、不改写 v1)。
输出 = verdict_q48b.json + 人读结论。退出码 0/2。
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
v1 = json.loads((HERE / "verdict_q48.json").read_text())
v1v = v1["verdict"]
v1c = v1v["checks"]
arms = v1["detail"]["arms"]
c1 = v1["detail"]["C1"]
c4 = v1["detail"]["C4"]

TWO_CASE = [0, 14]
checks, notes = {}, []

two_case_arms = {k: v for k, v in arms.items() if v["observed_fail_cases"] and set(v["observed_fail_cases"]).issubset(TWO_CASE) and v["observed_fail_cases"]}
noleg_arms = {k: v for k, v in arms.items() if v["semantics"] == "noleg"}
other_fail_arms = {k: v for k, v in arms.items() if v["observed_fail_cases"] and v["semantics"] != "noleg"}
pass_arms = {k: v for k, v in arms.items() if not v["observed_fail_cases"]}

# B1
b1 = all(v["semantics"] == "noleg"
         and sorted(int(r["case"]) for r in v["rows"] if r.get("legality")) == sorted(v["observed_fail_cases"])
         for v in two_case_arms.values()) and len(two_case_arms) == 3
checks["B1_two_case_signature_is_noleg_with_illegal_cases_equal_to_fails"] = bool(b1)
notes.append(f"two_case_arms={sorted(two_case_arms)} noleg_arms={sorted(noleg_arms)}")

# B2
b2 = all(v["fail_matches_prediction"] for v in noleg_arms.values()) and len(noleg_arms) >= 1
checks["B2_noleg_fail_set_recomputed_not_fitted"] = bool(b2)

# B3
b3 = all(v["n_illegal_moves"] == 0 for v in other_fail_arms.values()) and len(other_fail_arms) >= 1
checks["B3_other_failure_family_has_zero_illegal_moves"] = bool(b3)
for k, v in other_fail_arms.items():
    notes.append(f"{k}: fails={v['observed_fail_cases']} semantics={v['semantics']} illegal={v['n_illegal_moves']}")

# 负控
checks["NC_pass_arms_are_not_noleg_and_have_zero_illegal"] = all(
    v["semantics"] != "noleg" and v["n_illegal_moves"] == 0 for v in pass_arms.values()) and len(pass_arms) >= 1

# B4
checks["B4_public_example_covers_only_one_of_two"] = bool(c4["has_21_25_WIN_15_15"]) and not c4["has_25_25"]

# 正控: 夹具自洽 (v1 的 C1)
checks["PC_fixture_self_consistent_15_15"] = bool(v1c["C1_oracle_reproduces_fixture_15_15"])

verdict = {
    "label": "EXP1-Q48b",
    "v1_falsified_universal_claims": {
        "C2_every_arm_explained_by_one_semantics": v1c["C2_every_arm_explained_by_one_semantics"],
        "C2_fail_set_matches_prediction": v1c["C2_fail_set_matches_prediction"],
        "C3_failing_arms_have_illegal_moves": v1c["C3_failing_arms_have_illegal_moves"],
        "C4_public_example_in_prompt_verbatim": v1c["C4_public_example_in_prompt_verbatim"],
        "v1_rc": v1v["rc"],
        "status": "原样保留, 不翻案 (v1 判 rc=2)"
    },
    "narrowed_readings": {
        "two_case_signature_arms": sorted(two_case_arms),
        "noleg_semantics_arms": sorted(noleg_arms),
        "other_failure_family": {k: v["observed_fail_cases"] for k, v in other_fail_arms.items()},
        "clean_arms_15_15": sorted(pass_arms),
        "fixture_self_consistency": "15/15 (C1 正控) => 夹具缺陷分支不成立",
        "illegal_move_examples": {k: [r for r in v["rows"] if r.get("legality")] for k, v in noleg_arms.items()},
    },
    "checks_posthoc": notes,
    "checks": checks,
    "rc": 0 if all(checks.values()) else 2,
}
(HERE / "verdict_q48b.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=1))
print(json.dumps(verdict, ensure_ascii=False, indent=1))
sys.exit(verdict["rc"])
