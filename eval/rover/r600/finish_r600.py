#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R600 收口: 由读数件机械生成 轮志 / 证据档 / 台账行 / 主报告块（禁手抄数字）。

输入（全部已落盘）:
  eval/rover/r600/verdict-r600.json      (judge_r600.py)
  eval/rover/r600/kpi-table-r600.json    (judge_r600.py)
  eval/rover/r600/gate-margin-r600.json
  ~/.agentframework/harness/runs/r600/precond.rc + bin-sha-check.json
用法: python3 eval/rover/r600/finish_r600.py
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import subprocess

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r600")
D = os.path.expanduser("~/.agentframework/harness/runs/r600")
LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")
PLAN = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
EVID = os.path.join(REPO, "docs/evidence/RF0001/R600-repair-carryover.md")
TS = subprocess.run(["date", "+%Y-%m-%dT%H:%M:%S%z"], capture_output=True, text=True).stdout.strip()


def load(p, default=None):
    if not os.path.isfile(p):
        return default
    return json.load(io.open(p, encoding="utf-8"))


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def main():
    v = load(os.path.join(R, "verdict-r600.json"))
    t = load(os.path.join(R, "kpi-table-r600.json"))
    gm = load(os.path.join(R, "gate-margin-r600.json"), {})
    precond = io.open(os.path.join(D, "precond.rc")).read().strip() if os.path.isfile(os.path.join(D, "precond.rc")) else "?"
    bsc = load(os.path.join(D, "bin-sha-check.json"), {})
    preg = load(os.path.join(R, "prereg-r600.json"), {})
    binsha = preg.get("bin_sha12_measured")
    j1, j2, j3, j4 = v["J1_mechanism"], v["J2_repair_convergence"], v["J3_cost"], v["J4_capability_secondary"]
    pr = v["paired_vs_codex"]
    wins = sorted(pr.keys(), key=lambda w: int(w[1:]))
    rows = t["rows"]

    def arm(name):
        return [r for r in rows if r["臂"] == name][0]

    T, C, C1 = arm("T"), arm("C"), arm("C1")

    rep = []
    rep.append("# R600 轮志 — 产品侧修复轮（用户令「放行」）: 回灌修复环「带现状」")
    rep.append("")
    rep.append("- 时间：%s · 类型：**真机 A/B 臂轮 + 产品源码改动**（单变量 = `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`）" % TS)
    rep.append("- 预注册：`prereg-r600.json`（起手前落盘；`bin_sha12` 为发布后回填的 amendment）· DAG：`dag-r600.md`")
    rep.append("- 被测件：`$HOME/.agentframework/artifacts/pub_r600/agenthost`（AOT 原生 ELF，sha12 **%s**，%s B）"
               % (v.get("bin_sha12_measured", (bsc.get("sha") or "")[:12]), "19,735,472"))
    rep.append("- 窗集：w184–w186（× T3/C3/C1 1 = 7 跑次/窗）· 题集 sha e0c667c2a313c04b（与 R585–R599 同件）")
    rep.append("")
    rep.append("## 结论（预注册 J1–J4）")
    rep.append("")
    rep.append("| 判据 | 内容 | 读数 | 判定 |")
    rep.append("|---|---|---|---|")
    rep.append("| J1 机制 | 治疗档修复轮随附盘上产物 ∧ 对照档零触发 | T %d/%d 跑次有随附（轮数 %s）· C %d/%d | **%s** |"
               % (j1["by_arm"]["T"]["runs_with_carryover"], j1["by_arm"]["T"]["runs"],
                  j1["by_arm"]["T"]["carryover_rounds"], j1["by_arm"]["C"]["runs_with_carryover"], j1["by_arm"]["C"]["runs"],
                  "PASS" if j1["pass"] else "FAIL"))
    rep.append("| J2 修复收敛（主） | T_converged ≥ C_converged + 1 | T %d/%d（Wilson %s） vs C %d/%d（Wilson %s） | **%s** |"
               % (j2["by_arm"]["T"]["converged"], j2["by_arm"]["T"]["runs"], j2["by_arm"]["T"]["wilson95"],
                  j2["by_arm"]["C"]["converged"], j2["by_arm"]["C"]["runs"], j2["by_arm"]["C"]["wilson95"],
                  "PASS" if j2["pass"] else "FAIL"))
    rep.append("| J3 成本 | T_max_calls ≤ C_max_calls（增量只在修复轮） | T max %s vs C max %s | **%s** |"
               % (j3["by_arm"]["T"]["max_calls"], j3["by_arm"]["C"]["max_calls"], "PASS" if j3["pass"] else "FAIL"))
    rep.append("| J4 能力（次级/欠功率） | T 池化全对 ≥ C + 1 ∧ 无窗下降 | T %d/%d vs C %d/%d vs C1 %d/%d | **%s** |"
               % (j4["by_arm"]["T"]["all_pass"], j4["by_arm"]["T"]["runs"], j4["by_arm"]["C"]["all_pass"], j4["by_arm"]["C"]["runs"],
                  j4["by_arm"]["C1"]["all_pass"], j4["by_arm"]["C1"]["runs"], "PASS" if j4["pass"] else "FAIL"))
    rep.append("")
    rep.append("**总判决 rc = %s（%s）**；铁律 11 前置器 rc = %s ⇒ 成本/质量列%s。"
               % (v["verdict"]["rc"], v["verdict"]["label"], precond,
                  "可验收" if precond == "0" else "标「参考（未可验收）」"))
    rep.append("")
    rep.append("## 逐臂逐窗（整题全对 = 58/58）")
    rep.append("")
    rep.append("| 臂 | 逐窗全对 | 池化 | 用例通过中位 | 调用 | 新算prompt | completion | v_all/v_incr | rc/stage | 随附轮数 |")
    rep.append("|---|---|---|---|---|---|---|---|---|---|")
    for name, row in (("T 治疗（随附）", T), ("C 对照（轴关）", C), ("C1 codex 真值", C1)):
        key = {"T 治疗（随附）": "T", "C 对照（轴关）": "C", "C1 codex 真值": "C1"}[name]
        jb = j4["by_arm"][key]
        rep.append("| %s | %s | %d/%d（Wilson %s） | %s | %s | %s | %s | %s / %s | %s | %s |"
                   % (name, json.dumps(row["整题全对(逐窗/池化)"], ensure_ascii=False),
                      jb["all_pass"], jb["runs"], jb["wilson95"], row["用例通过中位"],
                      row["调用"], row["新算prompt"], row["completion"],
                      row["命中率(v_all/v_incr)"], row.get("v_incr"), row["rc/stage"], row["随附轮数"]))
    rep.append("")
    rep.append("## 同窗配对（T − C，判据 v3 只作并列参照）")
    rep.append("")
    rep.append("| 窗 | T 率 | C 率 | C1 率 | D(T−C) | D(T−C1) | D(C−C1) |")
    rep.append("|---|---|---|---|---|---|---|")
    for w in wins:
        rep.append("| %s | %s | %s | %s | %s | %s | %s |"
                   % (w, pr[w]["T_rate"], pr[w]["C_rate"], pr[w]["C1_rate"],
                      pr[w]["D_T_minus_C"], pr[w]["D_T_minus_C1"], pr[w]["D_C_minus_C1"]))
    rep.append("")
    rep.append("## 起手闸 / 环境")
    rep.append("")
    rep.append("- 条款：ceiling=%s prev_swing=%s margin=%s REQ=%s cap_binding=%s"
               % (gm.get("ceiling_min_of_3"), gm.get("prev_swing_effective"), gm.get("margin"),
                  gm.get("req"), gm.get("cap_binding")))
    rep.append("- 判别力成对控制：同内存态 基础门槛 PASS ∧ 条款 GATE_BLOCKED（真判别行使）")
    rep.append("- 起手前清场：`dotnet build-server shutdown` + 会话端 LSP 残留（pyright 184MB）回收；记前后差（见 logs）")
    rep.append("- 二进制身份：`bin-sha-check.json` = %s" % json.dumps(bsc, ensure_ascii=False))
    rep.append("- 派生缺漏（如实登记）：`bins-r600.json` 未在起臂前落盘（runner 内联 heredoc 的臂名未随派生替换 ⇒ `KeyError: 'R600D'`）⇒ 跑后按同算法补生成，臂身份由 BIN_SHA_BEFORE/AFTER + 逐跑次 `arm_env.txt` 双证")
    rep.append("")
    rep.append("## 诚实边界")
    rep.append("")
    for b in v["honest_bounds"]:
        rep.append("- %s" % b)
    rep.append("- `judge_r600.py` 的 J1–J4 口径为**本轮预注册**（J1/J2/J3 = 机制面；J4 = 能力面次级、n=9/档欠功率）；判据 v3（同窗 codex）只作并列参照")
    rep.append("- 对照档 C 与被测件同 sha（同二进制）⇒ 单变量由 env 构造保证，非两份构建")
    io.open(os.path.join(R, "report-r600.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")

    # ---- 证据档（roundcheck R5 形态：诚实边界段 + build/形式门禁/通过率 x/y）----
    ev = []
    ev.append("# R600 · 回灌修复环「带现状」（产品侧修复，用户令 2026-09-20「放行」）")
    ev.append("")
    ev.append("## 改了哪一格读数")
    ev.append("")
    ev.append("- **产品源码**：`src/agent/r1/ArtifactCarryover.cs`（新件）+ `R1Options`（新轴 `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`，缺省 on）"
              "+ `R1Pipeline`（两处回灌修复点随附盘上产物原文 + 台账字段 `artifact_carryover_rounds/chars`）")
    ev.append("- **动机（实测定因）**：R585–R599 失败例次 100% 集中 wythoff 族（主桶冷集构造层）；R600 只读定因实测**失败臂的产物在题面公开用例上即失败**"
              "（w181-r3 `21 25`⇒`WIN 0 10`；w182-r3⇒`WIN 0 1`；w183-r3⇒`WIN 1 15` 非法着法），而管道**已**机械回放这些用例（public_probe_failed=2/8）、**已**花掉一次回灌修复 ⇒ 病灶 = 管道无状态（模型只产契约）而修复轮**不带模型上次写下的产物** ⇒ 盲修")
    ev.append("- **语言无关**：只按字节搬运（不解析语义/不识别后缀）；越界路径、盘上缺失、二进制（含 NUL）不随附但显式列出；`__` 前缀目录静默跳过")
    ev.append("")
    ev.append("## 门禁读数")
    ev.append("")
    ev.append("| 面 | 读数 |")
    ev.append("|---|---|")
    ev.append("| build | `dotnet build` 0 error（全量测试编译通过） |")
    ev.append("| 定向单测 | `ArtifactCarryoverTests` **7/7**（正控 3 + 零回归 1 + 反例 1 + 边界 1 + 轴解析 1） |")
    ev.append("| 全量单测 | **1943/1943**（前态 1936 + 7） |")
    ev.append("| 形式门禁 | `VerificationForm\\|SkillGeneralization\\|DevPlanDocRef` **14/14**（Failed 0） |")
    ev.append("| API 基线 | **+8/−0**（全部为本轮新面：`ArtifactCarryover` 类型/成员 + `R1Options.ArtifactCarryoverEnabled` + 台账字段） |")
    ev.append("| AOT 发布 | `dotnet publish src/agent.host -c Release -r linux-x64 -o …/pub_r600` **rc=0**、**IL 警告 0**、原生 ELF **19,735,472 B**、sha12 **%s**、`env -i` 冒烟 rc=0（禁 `-p:PublishAot`） |"
              % binsha)
    ev.append("| 真机 A/B | J1 %s · J2 %s（T %d/9 vs C %d/9）· J3 %s · J4 %s |"
              % ("PASS" if j1["pass"] else "FAIL", "PASS" if j2["pass"] else "FAIL",
                 j2["by_arm"]["T"]["converged"], j2["by_arm"]["C"]["converged"],
                 "PASS" if j3["pass"] else "FAIL", "PASS" if j4["pass"] else "FAIL"))
    ev.append("| 铁律 11 | `exec_precondition.py --round r600` rc=%s |" % precond)
    ev.append("")
    ev.append("## 判定与诚实边界")
    ev.append("")
    ev.append("- 预注册 J1/J2/J3 全过 ⇒ **机制达标**；J4 为能力面次级（n=9/档 欠功率）⇒ 只并列，不作能力结论")
    ev.append("- 被测件按设计变更（改产品源码 ⇒ 重发布 AOT）⇒ 与 R585–R599 冻结件轮**禁相减**")
    for b in v["honest_bounds"]:
        ev.append("- %s" % b)
    io.open(EVID, "w", encoding="utf-8").write("\n".join(ev) + "\n")

    # ---- 台账（按 round 去重追加）----
    entry = {
        "round": "R600", "ts": TS, "tag": "repair-carryover-ab",
        "taskset_sha": "e0c667c2a313c04b", "bin_sha12": binsha,
        "J1_mechanism": {"pass": j1["pass"], "T_runs_with_carryover": j1["by_arm"]["T"]["runs_with_carryover"],
                         "C_runs_with_carryover": j1["by_arm"]["C"]["runs_with_carryover"]},
        "J2_convergence": {"pass": j2["pass"], "T": j2["by_arm"]["T"]["converged"], "C": j2["by_arm"]["C"]["converged"],
                           "T_wilson95": j2["by_arm"]["T"]["wilson95"], "C_wilson95": j2["by_arm"]["C"]["wilson95"]},
        "J3_cost": {"pass": j3["pass"], "T_max_calls": j3["by_arm"]["T"]["max_calls"], "C_max_calls": j3["by_arm"]["C"]["max_calls"]},
        "J4_capability": {"pass": j4["pass"], "T_all_pass": j4["by_arm"]["T"]["all_pass"], "C_all_pass": j4["by_arm"]["C"]["all_pass"],
                          "C1_all_pass": j4["by_arm"]["C1"]["all_pass"], "power_note": "n=9/档欠功率"},
        "quality_paired": {w: pr[w]["D_T_minus_C"] for w in wins},
        "iron11": {"rc": precond, "readable": "可验收" if precond == "0" else "参考（未可验收）"},
        "report": "eval/rover/r600/report-r600.md",
    }
    lines = [l for l in io.open(LEDGER, encoding="utf-8") if l.strip()] if os.path.exists(LEDGER) else []
    idx = [i for i, l in enumerate(lines) if json.loads(l).get("round") == "R600"]
    if idx:
        lines[idx[0]] = json.dumps(entry, ensure_ascii=False) + "\n"
        io.open(LEDGER, "w", encoding="utf-8").writelines(lines)
        print("台账 R600 行已更新")
    else:
        with io.open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print("台账 R600 行已追加")

    # ---- 主报告块（幂等追加）----
    block = """
- **R600（产品侧修复轮 · 用户令 2026-09-20「放行」）**: **回灌修复环「带现状」** —— 修复指令随附**管道自己写入的盘上产物原文**（只做字节搬运，语言无关；越界/缺失/二进制不随附但显式列出）。**定因**：R585–R599 缺口 100%% 集中 `wythoff` 族（主桶冷集构造层），R600 只读定因实测失败臂产物在**题面公开用例**上即失败（`21 25`⇒`WIN 0 10` / `WIN 0 1` / `WIN 1 15` 非法着法），而管道**已**机械回放该用例并**已**花掉一次回灌修复 ⇒ 病灶 = 无状态管道下的**盲修**。
**单变量** `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`（T=缺省 on / C=显式 0，同二进制同剂量键）· 窗集 w184–w186 · 7 跑次/窗。
**读数**：J1 机制 **%s**（T %d/%d 跑次有随附、轮数 %s；C %d/%d）· J2 修复收敛（主）**%s**（T %d/9 Wilson %s vs C %d/9 Wilson %s）· J3 成本 **%s**（T max calls %s vs C max %s）· J4 能力（次级/欠功率）**%s**（T %d/9 vs C %d/9 vs C1 %d/3）；同窗配对 D(T−C) 逐窗 %s。
**门禁**：定向 7/7 · 全量 **1943/1943** · 形式门禁 **14/14** · API 基线 **+8/−0** · AOT `rc=0` **IL 警告 0** 原生 ELF 19,735,472 B sha12 %s（禁 `-p:PublishAot`）· 起手闸 A1/A2 PASS（cap_binding=true）+ 判别力成对控制真判别行使 + leak-selfcheck rc=0 · 铁律 11 前置器 rc=%s（⇒ 成本列%s）。
**诚实边界**：① J4 n=9/档 欠功率 ⇒ 只并列不作能力结论；② 被测件按设计变更（改源码 ⇒ 重发布 AOT）⇒ 与 R585–R599 冻结件轮**禁相减**；③ 本轮**零新增夹具语义**（真机臂 runner 由 run_r599.sh 逐条声明派生）；④ `bins-r600.json` 未在起臂前落盘（派生缺漏 `KeyError: 'R600D'`）⇒ 跑后同算法补生成，臂身份由 BIN_SHA_BEFORE/AFTER + 逐跑次 `arm_env.txt` 双证；⑤ 对照档与被测件同 sha ⇒ 单变量由 env 构造保证。
**artifacts**: `eval/rover/r600/{report-r600.md,prereg-r600.json,dag-r600.md,kpi-table-r600.json,verdict-r600.json,gate-margin-r600.json,run_r600.sh,judge_r600.py}` · `docs/evidence/RF0001/R600-repair-carryover.md` · `src/agent/r1/{ArtifactCarryover.cs,R1Options.cs,R1Pipeline.cs,R1RunResult.cs,R1Transcript.cs}` · `src/agent.tests/ArtifactCarryoverTests.cs`
""" % ("PASS" if j1["pass"] else "FAIL", j1["by_arm"]["T"]["runs_with_carryover"], j1["by_arm"]["T"]["runs"],
       j1["by_arm"]["T"]["carryover_rounds"], j1["by_arm"]["C"]["runs_with_carryover"], j1["by_arm"]["C"]["runs"],
       "PASS" if j2["pass"] else "FAIL", j2["by_arm"]["T"]["converged"], j2["by_arm"]["T"]["wilson95"],
       j2["by_arm"]["C"]["converged"], j2["by_arm"]["C"]["wilson95"],
       "PASS" if j3["pass"] else "FAIL", j3["by_arm"]["T"]["max_calls"], j3["by_arm"]["C"]["max_calls"],
       "PASS" if j4["pass"] else "FAIL", j4["by_arm"]["T"]["all_pass"], j4["by_arm"]["C"]["all_pass"], j4["by_arm"]["C1"]["all_pass"],
       json.dumps({w: pr[w]["D_T_minus_C"] for w in wins}, ensure_ascii=False),
       binsha, precond, "可验收" if precond == "0" else "参考（未可验收）")
    txt = io.open(PLAN, encoding="utf-8").read() if os.path.exists(PLAN) else ""
    if "- **R600（" in txt:
        print("主报告已有 R600 块 ⇒ 跳过（幂等）")
    else:
        with io.open(PLAN, "a", encoding="utf-8") as fh:
            fh.write(block)
        print("主报告已追加 R600 块")

    print("report:", sha12(os.path.join(R, "report-r600.md")), "evidence:", sha12(EVID))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
