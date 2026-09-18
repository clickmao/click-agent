#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 R545 的 runner/analyzer 派生 R546 版本(只改语义面, 逐处替换均断言命中)。

纪律: 生成物禁手改(与本脚本同源); 每个替换都断言命中次数 > 0, 未命中 ⇒ 非零退出。
用法: python3 eval/rover/r546/port_r546.py
"""
from __future__ import annotations
import io, os, sys

REPO = "/home/agentuser/AgentFramework"
R545 = os.path.join(REPO, "eval/rover/r545")
R546 = os.path.join(REPO, "eval/rover/r546")
FAIL = []


def sub(txt, old, new, n=1, label=""):
    got = txt.count(old)
    if got != n:
        FAIL.append("%s: 命中 %d != %d" % (label or old[:30], got, n))
        return txt
    return txt.replace(old, new)


# ============================ runner =======================================
src = io.open(os.path.join(R545, "run_r545.sh"), encoding="utf-8").read()
hdr_old = """# R545 同窗单变量对照 —— g1(随机游戏长任务, 58 隐藏用例) 的 **公开用例回放触发面修正** 轴
#
# 动因 (R544 同窗实测): 预注册 J1 被**证伪** —— 3 个 on 臂只有 1 个走到回放点; 另 2 个在**计划执行阶段**
#   就 rc=5, 而 v1 的触发面是 `exec.Rc==0` ⇒ 机制在多数臂上结构性不可达(「挂上了」≠「生效了」)。
# R545 单变量 = 触发面 v2: **全部「产物已在盘」的出口**(rc 0/5/8) + 公开用例证据优先回灌。
#   v2 触发判据是机械的: 执行器 Steps 里出现过 write_file(唯一落盘工具) ⇒ 产物在盘 ⇒ 回放; 零写盘 ⇒ 弃权并记因。
#   其余全同(题面/用例/role/二进制/预算) ⇒ 与 R544 可比的关键 = 题面与夹具**逐字节同**(起臂前机检)。
#   另: 旧路径基线 A1on × 3 样本(候选③: 该列 R542 4 调用 / R544 34 调用, 8.5× 摆动, 单样本不可判)。
"""
hdr_new = """# R546 同窗单变量对照 —— g1(随机游戏长任务, 58 隐藏用例) 的 **早停轴** 对照
#
# 单变量 = AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(=0 轴关), 2(轴开)}:
#   轴开 ⇒ 探针回放**已经**判定产物在多条题面公开用例上不符(pfail ≥ 2)时, **不再**花一次远端调用
#   做回灌修复, 直接走既有终端分类(rc 语义不变)。动因 = R413 用户判据「一轮 token ↓≥30%, 主要是不必要
#   的 LLM API 请求少了」—— 而那一次回灌调用的边际价值在 R544/R545 从未被单变量检验。
#   其余全同: 题面/用例/role/二进制/预算(MAX_EXEC_REPAIR=1)/探针开关(PUBLIC_SELFCHECK=1) ⇒ 起臂前逐字节机检。
#   另: 旧路径基线 A1on × 3 样本/窗(候选③: 该列 R542 4 调用 / R544 34 调用, 8.5× 摆动, 单样本不可判)。
"""
src = sub(src, hdr_old, hdr_new, 1, "runner header")
src = src.replace("r545", "r546").replace("R545", "R546")
src = src.replace("48992", "48994")
src = sub(src, 'ARMS="P0a P0b P0c P0d P0e P1a P1b P1c P1d P1e A1on A1onb A1onc"',
          'ARMS="E0a E0b E0c E0d E0e E1a E1b E1c E1d E1e A1on A1onb A1onc"', 1, "ARMS")
src = sub(src, '  run_r1 "P0$rep" "off" "$rep"\n  run_r1 "P1$rep" "on" "$rep"',
          '  run_r1 "E0$rep" "early0" "$rep"\n  run_r1 "E1$rep" "early2" "$rep"', 1, "arm loop")
src = sub(src, '  if [ "$SW" = "on" ]; then', '  if [ "$SW" = "early2" ]; then', 1, "run_r1 branch")
# 轴开分支: 探针开 + 早停阈值 2
src = sub(src, '        AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1 \\\n        "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \\',
          '        AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1 \\\n        AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL=2 \\\n        "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \\',
          1, "early2 env")
# 轴关分支: 探针仍开, 只把早停 unset(轴关 ⇒ 台账无 early_stop_* 字段)
src = sub(src, '    env -u AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK "AGENTFRAMEWORK_WORKSPACE=$D/$A/g1/work"',
          '    env -u AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL "AGENTFRAMEWORK_WORKSPACE=$D/$A/g1/work"',
          1, "early0 env head")
src = sub(src, '        AGENTFRAMEWORK_R1_MAX_REPAIR=1 \\\n        "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \\',
          '        AGENTFRAMEWORK_R1_MAX_REPAIR=1 \\\n        AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1 \\\n        "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \\',
          1, "early0 probe on")
# 旧路径臂 + 冒烟: 显式 unset 早停
src = sub(src, '      -u AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK \\\n      python3 "$SIDE_RUNNER"',
          '      -u AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK -u AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL \\\n      python3 "$SIDE_RUNNER"',
          1, "legacy unset")
src = sub(src, 'env AGENTFRAMEWORK_WORKSPACE="$SMOKE/work"',
          'env -u AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL AGENTFRAMEWORK_WORKSPACE="$SMOKE/work"', 1, "smoke unset")
src = sub(src, '  echo "单变量: 触发面 v2(产物在盘的全部出口) — AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK ∈ {off,on} × 5 独立 session; 另 A1on × 3(旧路径)"',
          '  echo "单变量: 早停轴 — AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(0),2} × 5 独立 session × 2 窗; 探针开关两列同为 1; 另 A1on × 3/窗(旧路径)"',
          1, "summary text")
io.open(os.path.join(R546, "run_r546.sh"), "w", encoding="utf-8").write(src)
os.chmod(os.path.join(R546, "run_r546.sh"), 0o755)

# ============================ analyzer =====================================
src = io.open(os.path.join(R545, "analyze_r545.py"), encoding="utf-8").read()
doc_old = src[:src.index('"""', src.index('"""') + 3) + 3]
doc_new = '''"""R546 读数器 —— g1 产物侧 **早停轴** 单变量对照 (AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(0), 2})。

单变量: 早停阈值 {0(轴关), 2(轴开)} × **5 独立 session** × **2 窗**(w1/w2)
        + 旧路径基线 A1on × **3/窗**(候选③: 该列跨窗 8.5× 摆动, 须多样本定因)。
本轮因果假设(R413 判据抓手): 探针已判产物不合格(pfail≥2)时, 那次「回灌修复」远端调用是**不必要请求**;
  轴开把它省掉 ⇒ 调用数/token 应降而**质量不得降**。轴关臂逐位等于 R545 行为(零回归: 字段缺席可机检)。
读数来源(三路交叉, 与 R542/R544/R545 同口径):
  ① transcript.json (机制断言 + rc/stage + **R546 新增** early_stop_pfail/early_stop_skipped; **不作正确性证据**)
  ② adapter side-agent-* 实发用量 (付费口径唯一来源: 中继 usage)
  ③ 隐藏用例实跑 cases.txt (58 条, **唯一正确性证据**)
  ④ 产物树独立清点 (work 文件数) —— 「产物在盘」的非自报判据。

用法: python3 analyze_r546.py --run-dir <D> --window w1 [--taskset <TS>] [--out <json>]
"""'''
src = sub(src, doc_old, doc_new, 1, "analyzer docstring")
src = src.replace("r545", "r546").replace("R545", "R546")
src = sub(src, 'OFF = ["P0a", "P0b", "P0c", "P0d", "P0e"]\nON = ["P1a", "P1b", "P1c", "P1d", "P1e"]',
          'OFF = ["E0a", "E0b", "E0c", "E0d", "E0e"]\nON = ["E1a", "E1b", "E1c", "E1d", "E1e"]', 1, "OFF/ON")
src = sub(src, '        "public_probe_trigger_rc", "public_probe_reason")',
          '        "public_probe_trigger_rc", "public_probe_reason",\n        "early_stop_pfail", "early_stop_skipped")', 1, "KEYS")
src = sub(src, '           "single_variable": "AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK (触发面=v2: 产物在盘的全部出口)",',
          '           "single_variable": "AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL (0=轴关 / 2=pfail≥2 时省略那次回灌修复调用)",',
          1, "single_variable")
src = sub(src, '            "public_probe_reason": t.get("public_probe_reason"),\n            "artifact_files"',
          '            "public_probe_reason": t.get("public_probe_reason"),\n'
          '            "early_stop_pfail": t.get("early_stop_pfail"), "early_stop_skipped": t.get("early_stop_skipped"),\n'
          '            "artifact_files"', 1, "row fields")
src = sub(src, '            "reply_has_probe_marker": None,\n        }',
          '            "reply_has_probe_marker": None, "reply_has_early_stop_marker": None,\n        }', 1, "row marker field")
src = sub(src, '            out["arms"][arm]["reply_has_probe_marker"] = "R1_PUBLIC_PROBE" in txt',
          '            out["arms"][arm]["reply_has_probe_marker"] = "R1_PUBLIC_PROBE" in txt\n'
          '            out["arms"][arm]["reply_has_early_stop_marker"] = "R1_EARLY_STOP" in txt', 1, "marker detect")
# 不变量: 早停字段面
src = sub(src, '        "nonzero_exit_covered": any(v not in (None, 0) for v in on_trig.values()),\n    }',
          '        "nonzero_exit_covered": any(v not in (None, 0) for v in on_trig.values()),\n'
          '        "early_stop_off_fields_absent": all(out["arms"][k]["early_stop_pfail"] is None\n'
          '                                            and not out["arms"][k]["reply_has_early_stop_marker"] for k in OFF),\n'
          '        "early_stop_on_threshold_all2": all(out["arms"][k]["early_stop_pfail"] == 2 for k in ON),\n'
          '    }', 1, "invariants")
# 判据: 追加 J10/J11/J12 (R546 专有; 不改既有 J1v2..J9 口径)
jblock = '''
    # ---- R546 专有判据 (早停轴; 追加, 不改既有 J1v2..J9 口径) --------------------
    on_es = {k: out["arms"][k] for k in ON}
    off_es = {k: out["arms"][k] for k in OFF}
    fired = {k: r for k, r in on_es.items() if (r["public_probe_failed"] or 0) >= 2}
    off_same = {k: r for k, r in off_es.items() if (r["public_probe_failed"] or 0) >= 2}
    j10 = {
        "scope": "轴开臂 pfail≥2 ⇒ early_stop_skipped=1 ∧ exec_repairs=0 ∧ reply 含 R1_EARLY_STOP; 同窗轴关同 pfail 臂 ⇒ exec_repairs≥1(回灌真发生)",
        "fired_arms_on": {k: {"pfail": r["public_probe_failed"], "skipped": r["early_stop_skipped"],
                              "exec_repairs": r["exec_repairs"], "calls": r["calls_dump"],
                              "reply_marker": r["reply_has_early_stop_marker"]} for k, r in fired.items()},
        "same_pfail_off_arms": {k: {"pfail": r["public_probe_failed"], "exec_repairs": r["exec_repairs"],
                                    "calls": r["calls_dump"]} for k, r in off_same.items()},
        "on_fired_all_skipped": all(r["early_stop_skipped"] == 1 for r in fired.values()),
        "on_fired_no_repair": all(r["exec_repairs"] == 0 for r in fired.values()),
        "on_fired_marker": all(r["reply_has_early_stop_marker"] for r in fired.values()),
        "off_same_repaired": all((r["exec_repairs"] or 0) >= 1 for r in off_same.values()),
    }
    j10["samples_present"] = bool(fired and off_same)
    j10["verdict"] = ("PASS" if (j10["on_fired_all_skipped"] and j10["on_fired_no_repair"] and j10["on_fired_marker"]
                                 and j10["off_same_repaired"] and j10["samples_present"])
                      else ("机制未被行使(某类样本为空, 禁宣称省调用)" if not j10["samples_present"]
                            else "FAIL(判据证伪: 轴未按声明生效)"))
    lo = sorted(r["calls_dump"] for r in on_es.values() if r["calls_dump"] is not None)
    lf = sorted(r["calls_dump"] for r in off_es.values() if r["calls_dump"] is not None)
    pa = [r["calls_dump"] for k, r in fired.items() if r["calls_dump"] is not None]
    pb = [r["calls_dump"] for k, r in off_same.items() if r["calls_dump"] is not None]
    j11 = {
        "pair_rule": "按同 pfail 值配对; 预注册点估计 = 每臂省 1 次调用(那次回灌修复)",
        "all_arms_calls_median": {"axis_off": median(lf), "axis_on": median(lo),
                                  "ratio_on_off": ratio(median(lo), median(lf))},
        "pfail_ge2_calls": {"axis_off": pb, "axis_on": pa,
                            "median_off": median(pb), "median_on": median(pa),
                            "ratio_on_off": ratio(median(pa), median(pb)),
                            "call_sum_off": sum(pb), "call_sum_on": sum(pa),
                            "calls_saved_total": (sum(pb) - sum(pa)) if (pb and pa) else None},
        "pfail_lt2_calls_negative_control": {
            "axis_off": sorted(r["calls_dump"] for k, r in off_es.items()
                               if (r["public_probe_failed"] or 0) < 2 and r["calls_dump"] is not None),
            "axis_on": sorted(r["calls_dump"] for k, r in on_es.items()
                              if (r["public_probe_failed"] or 0) < 2 and r["calls_dump"] is not None),
            "note": "判别性阴性对照: 轴**不应**改变这一子集的调用数(除非修复预算本来就没被用)",
        },
        "tokens_pfail_ge2": {
            "prompt_median": {"off": median([r["prompt_tokens"] for r in off_same.values()]),
                              "on": median([r["prompt_tokens"] for r in fired.values()])},
            "completion_median": {"off": median([r["completion_tokens"] for r in off_same.values()]),
                                  "on": median([r["completion_tokens"] for r in fired.values()])},
            "total_median": {"off": median([r["total_tokens"] for r in off_same.values()]),
                             "on": median([r["total_tokens"] for r in fired.values()])},
        },
    }
    j12 = {
        "scope": "轴关(E0)臂: 台账无 early_stop_* 字段 ∧ reply 无 R1_EARLY_STOP ⇒ 逐位旧行为; 轴开臂: 字段在",
        "off_fields_absent": out["invariants"]["early_stop_off_fields_absent"],
        "on_threshold_all2": out["invariants"]["early_stop_on_threshold_all2"],
        "off_early_stop_pfail_values": [out["arms"][k]["early_stop_pfail"] for k in OFF],
        "suite_evidence": "1876/1876 全绿 + AOT IL 警告 0 + 器具级成对单测(R1EarlyStopTests: 轴关 Calls=2 / 轴开 Calls=1) —— 见轮报告, 非本读数器自报",
    }
    j12["verdict"] = "PASS" if (j12["off_fields_absent"] and j12["on_threshold_all2"]) else "FAIL"
    out["judgments"]["J10_早停机制(轴真生效)"] = j10
    out["judgments"]["J11_代价(配对)"] = j11
    out["judgments"]["J12_零回归(字段缺席)"] = j12

'''
src = sub(src, '    if a.out:\n        io.open(a.out, "w", encoding="utf-8")', jblock + '    if a.out:\n        io.open(a.out, "w", encoding="utf-8")',
          1, "judgments block")
src = sub(src, '    print("readings -> %s" % os.path.relpath(dst, REPO))',
          '    print("J10 %s | J12 %s" % (j10["verdict"], j12["verdict"]))\n'
          '    print("J11 pfail>=2 调用: off %s -> on %s (省 %s 次); 全臂中位 %s -> %s | 阴性对照<2: off %s on %s" % (\n'
          '        j11["pfail_ge2_calls"]["median_off"], j11["pfail_ge2_calls"]["median_on"],\n'
          '        j11["pfail_ge2_calls"]["calls_saved_total"], j11["all_arms_calls_median"]["axis_off"],\n'
          '        j11["all_arms_calls_median"]["axis_on"],\n'
          '        j11["pfail_lt2_calls_negative_control"]["axis_off"], j11["pfail_lt2_calls_negative_control"]["axis_on"]))\n'
          '    print("readings -> %s" % os.path.relpath(dst, REPO))', 1, "prints")
io.open(os.path.join(R546, "analyze_r546.py"), "w", encoding="utf-8").write(src)

print("port 结果: %s" % ("PASS" if not FAIL else "FAIL"))
for f in FAIL:
    print("  " + f)
print("runner=%d bytes analyzer=%d bytes" % (os.path.getsize(os.path.join(R546, "run_r546.sh")),
                                             os.path.getsize(os.path.join(R546, "analyze_r546.py"))))
sys.exit(0 if not FAIL else 3)
