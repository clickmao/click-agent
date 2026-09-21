#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R620 派生成 (RF0004.2 · M3 第四刀 = **回退分支真机行使**)。

派生源 = eval/rover/r619/{run_r619.sh,judge_r619.py,selftest_judge_r620.py,taskset-r619.json,cases/}
派生方式 = **逐条声明的文本替换 + 三处结构化补丁**（补丁内容写在下方 PATCHES，逐条可核）。
纪律: 不改判据阈值（只改**语义面**：本轮判据问的是「回退是否被行使」，R619 问的是「候选面是否被驱动」）；
      禁手抄判据；生成后跑 `--check` 断言生成物与替换规则一致。
用法: python3 eval/rover/r620/derive_r620.py [--check]
"""
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r619")
DST = os.path.join(REPO, "eval/rover/r620")
LEGACY_ANCHOR = "a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e"
R617_T_PIN = "25c97befa2124549b52991c0338324ceee7f7702a6348641ed917d3b7b658052"

# ---- 具名替换 (顺序敏感；逐条声明) ------------------------------------------
REPL = [
    ("R619", "R620"),                       # 轮号
    ("r619", "r620"),                       # 命名空间/路径
]
# 例外: 被测件**同件**（R620 零产品源码改动 ⇒ 复用 R619 的 AOT 发布件逐字节）
RESTORE_AFTER = [("pub_r620", "pub_r619")]

# ---- 结构化补丁 (逐条 id；old 必须唯一命中) ---------------------------------
PATCHES = [
    # P1: 臂表环境 —— 两臂**同值**注入 held-constant 提示尾块档 legacy
    ("P1_arm_env_legacy", """
                 "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE")""",
     """
                 "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE"
                 "AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy")  # R620 held-constant 上下文（非被测变量；两臂同值）"""),
    # P2: 预注册机检 —— 提示尾块是 held-constant（两臂必须同值 legacy），不再断言「两臂皆缺省」
    ("P2_prereg_gate", """for k, arm in (("AGENTFRAMEWORK_R1_ACTION_CANDIDATES", "T"), ("AGENTFRAMEWORK_R1_ACTION_CANDIDATES", "C"),
               ("AGENTFRAMEWORK_R1_ACTION_PROMPT", "T"), ("AGENTFRAMEWORK_R1_ACTION_PROMPT", "C"),
               ("AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR", "T"), ("AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR", "C"),
               ("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "T"), ("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "C")):
    assert k not in d["arms"][arm]["env"], "%s 本轮不是被测变量（两臂皆缺省: %s）" % (k, arm)""",
     """assert d["arms"]["T"]["env"]["AGENTFRAMEWORK_R1_ACTION_PROMPT"] == "legacy" and \\
       d["arms"]["C"]["env"]["AGENTFRAMEWORK_R1_ACTION_PROMPT"] == "legacy", \\
    "R620: 提示尾块 = held-constant 上下文（非被测变量）⇒ 两臂必须同值 legacy"
for k, arm in (("AGENTFRAMEWORK_R1_ACTION_CANDIDATES", "T"), ("AGENTFRAMEWORK_R1_ACTION_CANDIDATES", "C"),
               ("AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR", "T"), ("AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR", "C"),
               ("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "T"), ("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "C")):
    assert k not in d["arms"][arm]["env"], "%s 本轮不是被测变量（两臂皆缺省: %s）" % (k, arm)"""),
    # P3: 窗集断言 (211..213 -> 214..216)
    ("P3_windows_assert",
     """assert sorted(d["windows"]["set"]) == ["w211", "w212", "w213"], d["windows"]["set"]""",
     """assert sorted(d["windows"]["set"]) == ["w214", "w215", "w216"], d["windows"]["set"]"""),
    ("P4_win0", "WIN0=${WIN0:-211}", "WIN0=${WIN0:-214}"),
    # P5: 前提闸（adapter 就绪后、起臂前）：legacy 档必须让候选键**未到达** ⇒ 回退触发面成立
    ("P5_premise_gate", """# --- 4 逐窗逐重复 -----------------------------------------------------------""",
     """# --- 3b 前提闸 (fail-closed, 起臂前 1 跑次; 不计入臂表) ----------------------
#   R620 语义: held-constant 提示尾块 = legacy ⇒ 模型不给候选字段 ⇒ 采纳面为空
#   ⇒ `ActionExecPlan.Decide` 应走 **回退** 支。前提不成立 ⇒ 零臂起跑（rc=5），不烧 21 跑次。
mkdir -p "$D/premise/g1/work"
env AGENTFRAMEWORK_WORKSPACE="$D/premise/g1/work" AGENTFRAMEWORK_R1_CONTRACT=1 \\
    AGENTFRAMEWORK_R1_TRANSCRIPT="$D/premise/g1/transcript.json" AGENTFRAMEWORK_R1_TAG=premise-r620 \\
    AGENTFRAMEWORK_R1_ROLE_FILE="$ROLE" AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy AGENTFRAMEWORK_R1_ACTION_EXEC=1 \\
    timeout "$AMAXT" "$BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \\
    --session-id "premise-r620" > "$D/premise/g1/reply.txt" 2> "$D/premise/g1/stderr.txt"
echo "$? " > "$D/premise/g1/cli_rc.txt"
python3 - "$D/premise/g1/transcript.json" "$PDIR/premise-r620.json" "$LEGACY_ANCHOR_PLACEHOLDER" <<'PY'
import io, json, sys
tp, out, anchor = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    t = json.load(io.open(tp, encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    print("[前提闸] 缺 transcript: %s" % str(e)[:120]); raise SystemExit(5)
present = t.get("action_candidates_present")
sha = t.get("prefix_sha256")
src = t.get("exec_source")
fb = t.get("exec_fallback")
plan_n = t.get("plan_steps_total")
ok_state = (src == "plan_fallback" and fb == "candidates_absent" and (plan_n or 0) > 0)
ok_ctx = (sha == anchor)
rec = {"premise": "legacy 提示尾块 ⇒ 候选键未到达 ⇒ 回退支（plan_fallback / candidates_absent）",
       "action_candidates_present": present, "prefix_sha256": sha, "legacy_anchor": anchor,
       "exec_source": src, "exec_fallback": fb, "plan_steps_total": plan_n,
       "state_gate": bool(ok_state), "context_gate": bool(ok_ctx),
       "rc": 0 if (ok_state and ok_ctx) else 5}
json.dump(rec, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[前提闸] present=%s sha=%s src=%s fb=%s plan=%s rc=%d"
      % (present, (sha or "")[:12], src, fb, plan_n, rec["rc"]))
raise SystemExit(rec["rc"])
PY
_prc=$?; [ "$_prc" -eq 0 ] || { log "[致命] 前提闸未过 rc=$_prc ⇒ 零臂起跑（fail-closed）"; exit 5; }
log "前提闸 PASS: 回退触发面成立 (plan_fallback / candidates_absent)"

# --- 4 逐窗逐重复 -----------------------------------------------------------"""),
]


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def main():
    check = "--check" in sys.argv
    os.makedirs(os.path.join(DST, "snapshots"), exist_ok=True)
    os.makedirs(os.path.join(DST, "evidence/windows"), exist_ok=True)

    # 1) 逐字节复制件: cases/ + taskset
    src_cases = os.path.join(SRC, "cases")
    dst_cases = os.path.join(DST, "cases")
    if not check:
        if os.path.isdir(dst_cases):
            shutil.rmtree(dst_cases)
        shutil.copytree(src_cases, dst_cases)
        shutil.copyfile(os.path.join(SRC, "taskset-r619.json"), os.path.join(DST, "taskset-r620.json"))
    ts_src = sha12(os.path.join(SRC, "taskset-r619.json"))
    ts_dst = sha12(os.path.join(DST, "taskset-r620.json"))
    assert ts_src == ts_dst, "题集复制件必须逐字节同源 (%s vs %s)" % (ts_src, ts_dst)

    # 2) run_r620.sh
    txt = io.open(os.path.join(SRC, "run_r619.sh"), encoding="utf-8").read()
    for a, b in REPL:
        txt = txt.replace(a, b)
    for a, b in RESTORE_AFTER:
        txt = txt.replace(a, b)
    txt = txt.replace("# R620 驱动器（RF0004.2 · M3 **第二刀 = 执行面接线**）——",
                      "# R620 驱动器（RF0004.2 · M3 **第四刀 = 回退分支真机行使**）——")
    applied = []
    for pid, old, new in PATCHES:
        assert txt.count(old) == 1, "补丁 %s old 命中数 != 1 (%d)" % (pid, txt.count(old))
        txt = txt.replace(old, new)
        applied.append(pid)
    txt = txt.replace("$LEGACY_ANCHOR_PLACEHOLDER", LEGACY_ANCHOR)
    txt = txt.replace("restore_env_r620.py", "restore_env_r620.py")
    out_sh = os.path.join(DST, "run_r620.sh")
    if not check:
        io.open(out_sh, "w", encoding="utf-8").write(txt)
        os.chmod(out_sh, 0o755)
    assert "AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy" in txt, "P1 未落地"
    assert "前提闸" in txt and "exit 5" in txt, "P5 未落地"
    assert "pub_r620" not in txt, "被测件必须**同件**（pub_r619 逐字节）"

    # 3) judge_r620.py (P6..P11)
    j = io.open(os.path.join(SRC, "judge_r619.py"), encoding="utf-8").read()
    for a, b in REPL:
        j = j.replace(a, b)
    JP = [
        ("P6_legacy_anchor_const",
         '    R617_T_PIN = "%s"' % R617_T_PIN,
         '    R617_T_PIN = "%s"\n'
         '    # R620 held-constant 上下文 = 提示尾块 legacy 档（R610–R614 块逐字节）⇒ 生效前缀 sha\n'
         '    #   必须 == F_env.prefix.legacy_anchor（P1 的机检面）。不成立 ⇒ 前提不成立 ⇒ 整轮 VOID。\n'
         '    R620_LEGACY_ANCHOR = "%s"' % (R617_T_PIN, LEGACY_ANCHOR)),
        ("P7_j0_pin",
         '    j0["C_prefix_shared"] = bool(sT and sT == sC)   # 轴**零前缀改动**（两臂同源前缀）',
         '    j0["C_prefix_shared"] = bool(sT and sT == sC)   # 轴**零前缀改动**（两臂同源前缀）\n'
         '    j0["F_held_constant_legacy_block"] = bool(bool(sT) and sT == sC and sT == {R620_LEGACY_ANCHOR})\n'
         '    j0["F_note"] = ("R620 前提面：两臂前缀必须 == legacy 锚（F_env.prefix.legacy_anchor）"\n'
         '                    " ⇒ 证明 held-constant 上下文真生效（legacy 档不给候选字段 ⇒ 回退触发面成立）")'),
        ("P8_j0_pass",
         '    j0_pass = bool(j0["A_T_exec_source_in_allowed_faces"] and j0["B_C_new_fields_absent"]\n'
         '                   and j0["C_prefix_shared"] and j0["E_telemetry_coverage"])',
         '    j0_pass = bool(j0["A_T_exec_source_in_allowed_faces"] and j0["B_C_new_fields_absent"]\n'
         '                   and j0["C_prefix_shared"] and j0["E_telemetry_coverage"]\n'
         '                   and j0["F_held_constant_legacy_block"])'),
        ("P9_cons_scope",
         '            cons = None\n'
         '            if None not in (acc, unm, exe, inh):',
         '            cons = None\n'
         '            # R620: 守恒式**只在 candidates 源跑次上有定义**（回退跑次 accepted=0 ⇒ 不等式结构不适用；\n'
         '            #   把回退跑次计入守恒会把**合法回退**记成器具缺陷 ⇒ 判据绑组件真实行为）。\n'
         '            if tr.get("exec_source") == "candidates" and None not in (acc, unm, exe, inh):'),
        ("P10_j1_semantics",
         '    j1_vacuous = bool(j1["T"]["runs_four_fields"] == 0)\n'
         '    j1a_pass = bool(j1["T"]["runs_exec_source_candidates"] >= 1 and j1["T"]["runs_executed_positive"] >= 1)\n'
         '    j1b_pass = bool(not j1_vacuous and j1["T"]["conservation_violations"] == 0)',
         '    # R620 · 主判据 = **回退真机行使**（R619 U1 = 回退 0/9 行使 ⇒ NOT_EXERCISED；本轮以\n'
         '    #   held-constant legacy 尾块把触发前提（候选键未到达）**造出来**）：\n'
         '    #   a1 面覆盖 = candidates 源 + plan_fallback 源 == 总跑次\n'
         '    #   a2 **回退跑次 ≥ 1**（本轮核心）\n'
         '    #   a3 回退跑次 executed>0 **全部**（回退真把活干起来 ⇒ R618 D1 形态清零）\n'
         '    #   a4 守恒: 仅 candidates 源跑次有定义 ⇒ 本轮候选源为 0 时记 **N/A**（不判红、不判 PASS）\n'
         '    j1["T"]["runs_face_covered"] = int(j1["T"]["runs_exec_source_candidates"]\n'
         '                                       + j1["T"]["runs_plan_fallback"])\n'
         '    j1_vacuous = False   # R620: 真空闸改绑「candidates 源跑次」（本轮回退源为正常形态）\n'
         '    j1_cons_applicable = bool(j1["T"]["runs_four_fields"] > 0)\n'
         '    j1a_pass = bool(j1["T"]["runs_face_covered"] == j1["T"]["runs"]\n'
         '                    and j1["T"]["runs_plan_fallback"] >= 1\n'
         '                    and j1["T"]["runs_fallback_executed_positive"] == j1["T"]["runs_plan_fallback"])\n'
         '    j1b_pass = None if not j1_cons_applicable else bool(j1["T"]["conservation_violations"] == 0)'),
        ("P11_j1_pass",
         '    j1_pass = bool(j1a_pass and j1b_pass and j1c_pass and j1d_pass and j1e_pass)',
         '    j1_pass = bool(j1a_pass and (j1b_pass is not False) and j1c_pass and j1d_pass and j1e_pass)'),
        ("P12_vacuous_defect",
         '    if j1_vacuous:\n'
         '        defects.append("J1 真空绿闸: T 档四字段齐备跑次 = 0 ⇒ 守恒式不可判（fail-closed）")',
         '    if not j1a_pass:\n'
         '        defects.append("J1 主判据未过（面覆盖/回退行使/回退执行 三者之一不成立）: covered=%d/%d "\n'
         '                       "fallback=%d fb_exec_pos=%d"\n'
         '                       % (j1["T"]["runs_face_covered"], j1["T"]["runs"],\n'
         '                          j1["T"]["runs_plan_fallback"], j1["T"]["runs_fallback_executed_positive"]))'),
        # J6 零回归等价面（次级）
        ("P13_j6",
         '    # --- J2b 裁选面（机械守恒）：逐条裁定，无未裁定项 ---',
         '    # --- J6 零回归等价面（**次级**：回退 ⇒ 执行面 == plan == 轴关面 ⇒ 应当行为等价）--------\n'
         '    #   语义 = 「回退不改变行为」；不成立 ⇒ 回退**不是**零回归（单列，不改主 rc）。\n'
         '    j6 = {"need": "逐窗 rc 多重集 ∧ 逐窗用例通过数 T == C", "per_window": {}}\n'
         '    _eq = True\n'
         '    for w in wins:\n'
         '        _t = sorted((r["tr"].get("rc") for r in of("T", w)), key=lambda x: (x is None, x))\n'
         '        _c = sorted((r["tr"].get("rc") for r in of("C", w)), key=lambda x: (x is None, x))\n'
         '        _tp = sorted(r["cases_pass"] for r in of("T", w))\n'
         '        _cp = sorted(r["cases_pass"] for r in of("C", w))\n'
         '        _s = bool(_t == _c and _tp == _cp)\n'
         '        j6["per_window"][w] = {"rc_T": _t, "rc_C": _c, "cases_pass_T": _tp,\n'
         '                               "cases_pass_C": _cp, "equal": _s}\n'
         '        _eq = _eq and _s\n'
         '    j6["pass"] = bool(_eq)\n'
         '    if not _eq:\n'
         '        defects.append("J6 等价面不成立：回退面与轴关面逐窗读数不一致（单列，不改主 rc）")\n\n'
         '    # --- J2b 裁选面（机械守恒）：逐条裁定，无未裁定项 ---'),
        ("P14_mechanism_rc",
         '                    "mechanism_rc": 0 if (j0_pass and j1_pass and j2b_pass) else 1,',
         '                    # R620: 声明面在 legacy 档**结构性为空**（候选键未到达）⇒ J2b 记 N/A，\n'
         '                    #   不被读成「通过」也不被读成「失败」（未测到 ≠ 已验收）。\n'
         '                    "mechanism_rc": 0 if (j0_pass and j1_pass\n'
         '                                          and (j2b_pass or j2b_declared_runs == 0)) else 1,\n'
         '                    "j2b_applicable": bool(j2b_declared_runs > 0),'),
        ("P15_verdict_add_j6",
         '        "instrument_defects": defects,',
         '        "J6_zero_regression_equivalence": {"pass": j6["pass"], "note": "次级，不改主 rc", **j6},\n'
         '        "instrument_defects": defects,'),
        ("P16_j0_need",
         '                                 "need": "T 档逐跑次 exec_source 全 == candidates ∧ C 档四新字段全缺席 ∧ 两臂前缀同源 ∧ 每臂非全缺席",',
         '                                 "need": "T 档逐跑次 exec_source ∈ {candidates, plan_fallback} ∧ C 档五字段全缺席 ∧ "\n'
         '                                         "两臂前缀同源 ∧ **两臂前缀 == legacy 锚**（held-constant 生效）∧ 每臂非全缺席",'),
        ("P17_j1_need",
         '                                  "need": "T 有 exec_source=candidates ∧ 有跑次 executed>0 ∧ 逐跑次 unmapped<=accepted ∧ "',
         '                                  "need": "（R620）T 面覆盖 9/9 ∧ **回退跑次 ≥1** ∧ 回退跑次 executed>0 全部 ∧ D1 形态清零 ∧ "\n'
         '                                          "（原 R619 口径，保留备查）T 有 exec_source=candidates ∧ 有跑次 executed>0 ∧ 逐跑次 unmapped<=accepted ∧ "'),
        ("P18_print_j6",
         '                      "J3v2": j3_v2_pass, "J3v1": j3_v1_pass, "J4": j4_pass, "J5": j5_pass,',
         '                      "J3v2": j3_v2_pass, "J3v1": j3_v1_pass, "J4": j4_pass, "J5": j5_pass,\n'
         '                      "J6": j6["pass"], "face_T": j0["A_T_face_set"], "fb_T": j1["T"]["runs_plan_fallback"],\n'
         '                      "fb_reason_T": j1["T"]["fallback_reason_set"],'),
    ]
    for pid, old, new in JP:
        assert j.count(old) == 1, "补丁 %s old 命中数 != 1 (%d)" % (pid, j.count(old))
        j = j.replace(old, new)
        applied.append(pid)
    j = j.replace('"eval/rover/r617/kpi-table-r617.json"', '"eval/rover/r617/kpi-table-r617.json"')
    out_j = os.path.join(DST, "judge_r620.py")
    if not check:
        io.open(out_j, "w", encoding="utf-8").write(j)

    # 4) selftest_judge_r620.py（仅命名空间替换）
    s = io.open(os.path.join(SRC, "selftest_judge_r619.py"), encoding="utf-8").read()
    for a, b in REPL:
        s = s.replace(a, b)
    out_s = os.path.join(DST, "selftest_judge_r620.py")
    if not check:
        io.open(out_s, "w", encoding="utf-8").write(s)

    print(json.dumps({"applied": applied, "taskset_sha12": ts_dst,
                      "run_sha12": sha12(out_sh) if not check else None,
                      "judge_sha12": sha12(out_j) if not check else None,
                      "legacy_anchor": LEGACY_ANCHOR[:12]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
