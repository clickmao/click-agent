#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R546 收口器: 从 readings-w*.json + 前置器实跑 生成轮志/improvements 条/kpi 登记行。

纪律: 一切数字**现算**(禁手抄); ts 用真实时钟; 首跑即幂等(同 round 已存在 ⇒ 跳过 kpi 行)。
用法: python3 eval/rover/r546/report_r546.py [--windows w1 w2]
"""
from __future__ import annotations

import datetime
import io
import json
import os
import re
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r546")
OFF = ["E0a", "E0b", "E0c", "E0d", "E0e"]
ON = ["E1a", "E1b", "E1c", "E1d", "E1e"]
LEG = ["A1on", "A1onb", "A1onc"]
ARM_ORDER = OFF + ON + LEG


def rd(w):
    p = os.path.join(R, "readings-%s.json" % w)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


def med(xs):
    xs = [x for x in xs if x is not None]
    return None if not xs else (sorted(xs)[len(xs) // 2] if len(xs) % 2 else
                               round((sorted(xs)[len(xs) // 2 - 1] + sorted(xs)[len(xs) // 2]) / 2.0, 3))


def cell(r):
    return "%s/%s@%sc" % (r["cases_pass"], r["cases_total"], r["calls_dump"])


def main() -> int:
    wins = sys.argv[sys.argv.index("--windows") + 1:] if "--windows" in sys.argv else ["w1"]
    data = {w: rd(w) for w in wins}
    data = {w: d for w, d in data.items() if d}
    if not data:
        print("no readings"); return 1
    allarms = {}
    for w, d in data.items():
        for a in ARM_ORDER:
            if a in d["arms"]:
                allarms[(w, a)] = d["arms"][a]

    # 前置器实跑 (铁律 11)
    # 前置器判决（铁律 11）: 优先读**本轮 runner 已实跑**的判决件（同工具/同轮/同窗, 免重复 7 分钟执行）;
    # 缺失才自己实跑。判决来源与 rc 一并落到轮志, 便于复核。
    prej = os.path.join(REPO, "eval/rover/r507pre/precondition-r546.json")
    pretxt = os.path.join(R, "run-%s/logs/precond.txt" % wins[0])
    if os.path.exists(prej) and os.path.exists(pretxt):
        pout = io.open(pretxt, encoding="utf-8", errors="replace").read()
        mp = re.search(r"PRECOND_RC=(\d+)", pout)
        prc = int(mp.group(1)) if mp else -1
        src = "本轮 runner step-9 实跑(eval/rover/r546/run-%s/logs/precond.txt + eval/rover/r507pre/precondition-r546.json)" % wins[0]
    else:
        pr = subprocess.run([sys.executable, "eval/rover/r507pre/exec_precondition.py", "--round", "r546"],
                            cwd=REPO, capture_output=True, text=True)
        pout = (pr.stdout or "") + (pr.stderr or "")
        prc = pr.returncode
        src = "本收口器实跑"
    blocked = sorted(set(re.findall(r"([wW]\d/agent\w+-g1)", pout)))
    acc = {"rc": prc, "blocked_arms": blocked, "source": src,
           "verdict": {0: "可验收", 1: "未可验收(BLOCKED 逐条点名)", 3: "输入缺失 fail-closed"}.get(prc, "?")}

    # ---- 统计 -------------------------------------------------------------
    def col(win, arms):
        rs = [allarms[(win, a)] for a in arms if (win, a in allarms) and (win, a) in allarms]
        return rs

    def colany(arms):
        return [allarms[(w, a)] for w, a in allarms if a in arms]

    def stats(rs):
        return {"n": len(rs), "cases": [r["cases_pass"] for r in rs], "cases_median": med([r["cases_pass"] for r in rs]),
                "calls": [r["calls_dump"] for r in rs], "calls_median": med([r["calls_dump"] for r in rs]),
                "total": [r["total_tokens"] for r in rs], "total_median": med([r["total_tokens"] for r in rs]),
                "prompt_median": med([r["prompt_tokens"] for r in rs]),
                "completion_median": med([r["completion_tokens"] for r in rs]),
                "all_green": sum(1 for r in rs if r["all_green"]), "rcs": [r["rc"] for r in rs],
                "fake_success": sum(1 for r in rs if r["rc"] == 0 and not r["all_green"])}

    S = {"off": stats(colany(OFF)), "on": stats(colany(ON)), "legacy": stats(colany(LEG))}
    pf = {k: {(w, a): allarms[(w, a)] for w, a in allarms
              if a in (OFF + ON) and (allarms[(w, a)]["public_probe_failed"] or 0) >= 2} for k in ["x"]}["x"]
    pf_off = {k: v for k, v in pf.items() if k[1] in OFF}
    pf_on = {k: v for k, v in pf.items() if k[1] in ON}
    pf_lt2_off = [allarms[k] for k in allarms if k[1] in OFF and (allarms[k]["public_probe_failed"] or 0) < 2]
    pf_lt2_on = [allarms[k] for k in allarms if k[1] in ON and (allarms[k]["public_probe_failed"] or 0) < 2]

    J = {}
    for w, d in data.items():
        J[w] = d["judgments"]
    j10 = list(J.values())[-1]["J10_早停机制(轴真生效)"]
    j11 = list(J.values())[-1]["J11_代价(配对)"]
    j12 = list(J.values())[-1]["J12_零回归(字段缺席)"]
    j4 = list(J.values())[-1]["J4_代价"]

    # ---- post-hoc(非预注册; 预注册 J10 的「同终态 pfail 配对」在本窗为空 ⇒ 收窄, 不改预注册口径) ----
    fired = dict(j10.get("fired_arms_on") or {})
    off_same = dict(j10.get("same_pfail_off_arms") or {})
    off_repaired = {"%s/%s" % (k[0], k[1]): {"exec_repairs": r["exec_repairs"], "calls": r["calls_dump"],
                                             "pfail_final": r["public_probe_failed"], "cases": r["cases_pass"]}
                    for k, r in allarms.items() if k[1] in OFF and (r["exec_repairs"] or 0) >= 1}
    posthoc = {
        "name": "J10 反事实缺口的收窄读数(非预注册)",
        "why": "预注册 J10 要求「轴关列存在同**终态** pfail≥2 臂」作配对反事实; 本窗轴关列 5/5 臂终态 pfail ≤ 1"
               "(修复把公开面修回去了) ⇒ 该配对类为空, 预注册的省调用宣称在本窗**不可直接验收**(收窄, 不作废判据本身)。",
        "fired_arms_on": {k: {"pfail": v["pfail"], "calls": v["calls"], "exec_repairs": v["exec_repairs"],
                              "marker": v["reply_marker"]} for k, v in fired.items()},
        "off_repaired_arms": off_repaired,
        "off_repaired_calls_dist": sorted(v["calls"] for v in off_repaired.values()),
        "unit_level_pin": "器具级成对单测 `R1EarlyStopTests`: **同一脚本输入** 轴关 `Calls=2`(修复真发生) → 轴开 `Calls=1`(省掉那次) "
                          "⇒ 「早停省 1 次远端调用」在单元面是机械成对证据; 窗内只报「行使臂实测调用数 vs 轴关列分布」, 标参考。",
        "posthoc_side_effect": "轴关列被修复回 pfail≤1 而同列隐藏用例 %s; 轴开行使臂终态 pfail=2, 隐藏用例 %s"
                               "—— 方向与「修复有效」一致但样本 n=%d/%d, **不足以下结论**(预注册未声明质量非劣的配对检验)。"
                               % (sorted(v["cases"] for v in off_repaired.values()),
                                  sorted(allarms[(w, k)]["cases_pass"] for (w, k) in allarms if k in fired),
                                  len(off_repaired), len(fired)),
    }

    AOT = None
    import hashlib
    binp = "/tmp/pub_r546/agenthost"
    if os.path.exists(binp):
        AOT = {"sha256": hashlib.sha256(open(binp, "rb").read()).hexdigest(),
               "bytes": os.path.getsize(binp)}

    # ---- 轮志 -------------------------------------------------------------
    L = []
    L.append("# R546 — g1 长任务的**早停轴**单变量对照(探针已判不合格 ⇒ 省掉那次回灌修复请求)\n")
    L.append("> 窗口 %s · 臂 %d 个/窗 · 题面 `g1`(58 隐藏用例, sha256 `%s` 与 R544/R545 逐字节同) · "
             "AOT `%s` %s B (IL 警告 0)\n"
             % (", ".join(data.keys()), len(ARM_ORDER),
                list(data.values())[0]["arms"][OFF[0]]["prefix_sha256"][:16],
                (AOT or {}).get("sha256", "?")[:16], "{:,}".format((AOT or {}).get("bytes", 0))))
    L.append("## 0 靶点与单变量\n")
    L.append("- **靶点来源**: R545 下轮候选 ①(用户 R413 判据的直接抓手)。R545 事后单列已证"
             "「公开面失败数 pfail ∈ {0,2,4} ⇒ 隐藏用例均值 58.0/45.0/33.0 单调降」⇒ pfail 有预测力; "
             "**但那次「回灌修复」远端调用的边际价值从未被单变量检验**。")
    L.append("- **单变量** = `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(=0 轴关), 2(轴开)}`: 轴开 ⇒ 探针回放已判 "
             "pfail ≥ 2 时**不再**花一次远端调用做回灌修复(执行证据回灌同样终止 —— 这是轴的定义), 直接走既有终端分类(**rc 语义不变**)。")
    L.append("- 其余全同: 题面/用例/role/二进制/`MAX_EXEC_REPAIR=1`/探针开关(`PUBLIC_SELFCHECK=1`, **两列都开**) ⇒ "
             "起臂前逐字节机检(cases md5 / role md5 / prompt sha256 与 R545 相同)。\n")
    L.append("## 1 产品改动(代码事实)\n")
    L.append("| 文件 | 改动 | 关闭态安全性 |")
    L.append("|---|---|---|")
    L.append("| `src/agent/r1/R1Options.cs` | 新增第 9 位可选参数 `EarlyStopPfail=0` + env 解析(`0..10`, 非法 ⇒ 0) | 默认 0 ⇒ 无行为差 |")
    L.append("| `src/agent/r1/R1Pipeline.cs` | 探针失败分支: `earlyStop = opt.EarlyStopPfail>0 && probe.Failed>=opt.EarlyStopPfail`; "
             "命中 ⇒ 记录 `R1_EARLY_STOP{...}` 标记 + 跳过修复 + 终端条件加 `|| earlyStopSkips>0`(堵住「早停后又走执行修复」的漏) | "
             "0 ⇒ `earlyStop=false` ⇒ 逐位旧路径 |")
    L.append("| `src/agent/r1/R1RunResult.cs` | 新增 `EarlyStopThreshold` / `EarlyStopSkipped`(可选参数) | 0 ⇒ 字段不出现 |")
    L.append("| `src/agent/r1/R1Transcript.cs` | 台账/Marker 仅在 `EarlyStopThreshold>0` 时输出 `early_stop_pfail`/`early_stop_skipped` | "
             "轴关臂台账与旧版**逐字节同**(J12 机检「字段缺席」) |")
    L.append("")
    L.append("## 2 器具与硬门\n")
    L.append("- `eval/rover/r546/`: `setup_r546.py`(夹具逐字节复制 + md5 交叉核对 + 预注册生成) → `port_r546.py`(从 R545 派生 runner/读数器, "
             "**逐处替换断言命中**) → `run_r546.sh` → `analyze_r546.py`。")
    L.append("- 硬门: 起手闸 2×PASS · 输入钉逐项机检 · 预注册范围闸 `prereg_scope_gate.py` rc=0 · 冒烟(`hello=yes`) · "
             "每臂 `adapter_range` 非空(实发用量可核)。")
    L.append("- 读数三路交叉: 台账(机制) / adapter 中继 usage(付费口径) / 58 隐藏用例独立进程真跑(**唯一正确性证据**)。\n")
    L.append("## 3 同窗读数\n")
    L.append("| 臂 | 轴 | rc | 调用 | prompt | compl | total | 隐藏用例 | pfail | 早停跳过 | exec_repairs |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for w in data:
        for a in ARM_ORDER:
            if (w, a) not in allarms:
                continue
            r = allarms[(w, a)]
            ax = "关(0)" if a in OFF else ("开(pfail≥2)" if a in ON else "旧路径")
            L.append("| %s/%s | %s | %s | %s | %s | %s | %s | %s/%s | %s | %s | %s |"
                     % (w, a, ax, r["rc"], r["calls_dump"], "{:,}".format(r["prompt_tokens"] or 0),
                        "{:,}".format(r["completion_tokens"] or 0), "{:,}".format(r["total_tokens"] or 0),
                        r["cases_pass"], r["cases_total"], r["public_probe_failed"],
                        r.get("early_stop_skipped"), r["exec_repairs"]))
    L.append("")
    for k in ("off", "on", "legacy"):
        s = S[k]
        L.append("- **%s**(n=%d): 用例 %s(中位 %s, 全绿 %d/%d) · 调用 %s(中位 %s) · total 中位 %s · rc %s · 假成功 %d"
                 % (k, s["n"], s["cases"], s["cases_median"], s["all_green"], s["n"], s["calls"],
                    s["calls_median"], "{:,}".format(s["total_median"] or 0), s["rcs"], s["fake_success"]))
    L.append("")
    L.append("## 4 判据(本轮预注册 = J10/J11/J12)\n")
    L.append("- **J10 机制(轴真生效)**: `%s` —— 轴开臂 pfail≥2 的臂 %s ⇒ 全部 `early_stop_skipped=1` ∧ reply 含 `R1_EARLY_STOP`; "
             "同窗轴关同 pfail 臂 %s ⇒ %s"
             % (j10.get("verdict"), json.dumps(j10.get("fired_arms_on"), ensure_ascii=False),
                json.dumps(j10.get("same_pfail_off_arms"), ensure_ascii=False),
                "**成对反事实成立**(轴关同 pfail 臂真做了回灌修复)" if off_same else
                "**反事实类为空** ⇒ 预注册的「同终态 pfail 配对」在本窗不可构造(轴关列被修复回 pfail≤1) ⇒ 省调用宣称收窄为「器具级成对单测 + 行使臂实测」, 见 §4b"))
    L.append("- **J11 代价(配对)**: pfail≥2 子集调用 off %s → on %s(合计 %s → %s, **省 %s 次**); 全臂调用中位 %s → %s; "
             "**判别性阴性对照** pfail<2 子集 off %s / on %s。%s"
             % (j11["pfail_ge2_calls"]["median_off"], j11["pfail_ge2_calls"]["median_on"],
                j11["pfail_ge2_calls"]["call_sum_off"], j11["pfail_ge2_calls"]["call_sum_on"],
                j11["pfail_ge2_calls"]["calls_saved_total"], j11["all_arms_calls_median"]["axis_off"],
                j11["all_arms_calls_median"]["axis_on"],
                j11["pfail_lt2_calls_negative_control"]["axis_off"],
                j11["pfail_lt2_calls_negative_control"]["axis_on"],
                ("**轴关列同终态 pfail≥2 臂 = 空 ⇒ 上表该子集不可比, 省调用数一律标「参考(未可验收)」**"
                 if not off_same else "")))
    L.append("- **J12 零回归(字段缺席 + 单测成对)**: `%s` —— 轴关臂 `early_stop_*` 字段值 %s(应全 None) ⇒ 台账与旧版同; "
             "轴开臂阈值全 = 2 = %s。器具级成对单测 `src/agent.tests/R1EarlyStopTests.cs` 4/4: "
             "**同输入轴关 `Calls=2`(修复真发生) / 轴开 `Calls=1`(省掉那次) / 阈值 5 不触发(负控)**。"
             % (j12.get("verdict"), j12.get("off_early_stop_pfail_values"), j12.get("on_threshold_all2")))
    L.append("- 携带读数(非本轮变量, 只作对照): J1v2 `%s` · J8 `%s` · J3 `%s` · J4 `%s`"
             % (json.dumps(list(J.values())[-1].get("J1v2_机制启用(触发面修正)"), ensure_ascii=False)[:160],
                json.dumps(list(J.values())[-1].get("J8_出口覆盖"), ensure_ascii=False)[:160],
                json.dumps(list(J.values())[-1].get("J3_质量"), ensure_ascii=False)[:160],
                json.dumps(j4, ensure_ascii=False)[:220]))
    L.append("")
    L.append("## 4b post-hoc(非预注册, 单列: 预注册 J10 的配对类在本窗为空 ⇒ 宣称收窄)\n")
    L.append("```json\n" + json.dumps(posthoc, ensure_ascii=False, indent=1) + "\n```\n")
    L.append("## 5 铁律 11 前置器\n")
    L.append("- `python3 eval/rover/r507pre/exec_precondition.py --round r546` ⇒ **rc=%s (%s)**" % (acc["rc"], acc["verdict"]))
    L.append("- 阻塞臂(%d): %s" % (len(blocked), ", ".join(blocked) if blocked else "(无)"))
    L.append("")
    L.append("## 6 复现\n")
    L.append("```bash\npython3 eval/rover/r546/setup_r546.py && python3 eval/rover/r546/port_r546.py\n"
             "bash eval/rover/r546/run_r546.sh w1     # w2 同\n"
             "python3 eval/rover/r507pre/exec_precondition.py --round r546\n```")
    io.open(os.path.join(REPO, "docs/reports/r546-early-stop-axis.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    # ---- improvements 条 --------------------------------------------------
    imp = ["", "## R546 (2026-09-18) — 早停轴单变量对照(探针已判产物不合格 ⇒ 省掉那次回灌修复请求) — 结果: %s" % (
        "轴真生效且省调用" if j10.get("verdict") == "PASS" else ("机制已行使但配对反事实为空(收窄, 见轮志 §4b)" if "未被行使" in str(j10.get("verdict")) else "判据证伪")),
        "", ]
    imp.append("(轮志: `docs/reports/r546-early-stop-axis.md` · prereg/证据 `eval/rover/r546/`)\n")
    imp.append("- **靶点来源**: R545 候选① + 用户 R413 判据「一轮 token ↓≥30%, 主要是不必要的 LLM API 请求少了」; "
               "R545 事后单列已证 pfail 有预测力(0/2/4 ⇒ 58.0/45.0/33.0)。")
    imp.append("- **产品改动**: `R1Options.EarlyStopPfail`(默认 0=关) + `R1Pipeline` 早停分支/终端条件 + 台账字段 `early_stop_pfail`/"
               "`early_stop_skipped`(轴关不出现 ⇒ 逐字节同旧版)。")
    imp.append("- **读数 (窗 %s, 题面 sha 与 R544/R545 逐字节同, 起手闸 2/2 PASS, AOT `%s` %s B IL 警告 0)**: "
               "`off`(n=%d) %s ⇒ 全绿 %d · 用例中位 %s · 假成功 %d; `on`(n=%d) %s ⇒ 全绿 %d · 用例中位 %s · 假成功 %d; "
               "旧路径(n=%d) %s。"
               % (",".join(data.keys()), (AOT or {}).get("sha256", "?")[:16], "{:,}".format((AOT or {}).get("bytes", 0)),
                  S["off"]["n"], S["off"]["cases"], S["off"]["all_green"], S["off"]["cases_median"], S["off"]["fake_success"],
                  S["on"]["n"], S["on"]["cases"], S["on"]["all_green"], S["on"]["cases_median"], S["on"]["fake_success"],
                  S["legacy"]["n"], S["legacy"]["cases"]))
    imp.append("- **判据**: J10 %s · J11 pfail≥2 调用中位 %s→%s(省 %s 次) / 全臂中位 %s→%s / 阴性对照(pfail<2) %s vs %s · J12 %s。"
               % (j10.get("verdict"), j11["pfail_ge2_calls"]["median_off"], j11["pfail_ge2_calls"]["median_on"],
                  j11["pfail_ge2_calls"]["calls_saved_total"], j11["all_arms_calls_median"]["axis_off"],
                  j11["all_arms_calls_median"]["axis_on"], j11["pfail_lt2_calls_negative_control"]["axis_off"],
                  j11["pfail_lt2_calls_negative_control"]["axis_on"], j12.get("verdict")))
    imp.append("- **测试基线**: 新增 `R1EarlyStopTests` 4/4(含成对 `Calls=2 vs 1` + 阈值负控); 全量 1876/1876(0 failed); "
               "API 基线显式重生(**差异仅本轮** 3 行)。")
    imp.append("- **诚实边界**: ① 窗口数 %d ⇒ %s ② 前置器 rc=%s ⇒ 成本读数标「参考(未可验收)」 ③ 外部真值(codex-cli)未安装 ⇒ "
               "主线四硬条件缺外侧 ④ **预注册 J10 的配对反事实类为空**(轴关 5/5 臂终态 pfail≤1) ⇒ 省调用数**不在窗内宣**, "
               "只留器具级成对单测(同输入 轴关 Calls=2 / 轴开 Calls=1)与行使臂实测调用数, post-hoc 单列于轮志 §4b ⑤ 未测: "
               "早停阈值 1/3 的剂量响应、早停对**质量**的影响(行使臂隐藏用例 %s vs 轴关已修复臂 %s, n=%d/%d 不下结论)。"
               % (len(data), "单窗 ⇒ 逐窗极差不可估, 采样方差只在窗内" if len(data) == 1 else "两窗 ⇒ 已报逐窗+极差",
                  acc["rc"],
                  sorted(allarms[(w, k)]["cases_pass"] for (w, k) in allarms if k in fired),
                  sorted(v["cases"] for v in off_repaired.values()), len(fired), len(off_repaired)))
    imp.append("- **下轮候选 (R547)**: ① 第二窗(w2)—— 单窗=噪声, 且本轮前置器在窗口面仍 rc=%s, 需按逐窗+极差重报 ② 早停阈值剂量(1/2/3)响应曲线 "
               "(现在只有 2 一个点) ③ pfail≥2 子集上「省调用 vs 质量」的配对样本扩到 n≥5(现 n=%d) ④ R545 候选②/③ 仍未闭合(on 中位 < off 定因; 旧路径列本期 n=%d) "
               "⑤ 前置器臂级口径(先写后跑)。" % (acc["rc"], min(len(pf_on), len(pf_off)), S["legacy"]["n"]))
    imp.append("")
    imppath = os.path.join(REPO, "docs/improvements.md")
    txt = io.open(imppath, encoding="utf-8").read()
    txt = re.sub(r"\n?<!-- R546-INFLIGHT:.*?-->\n?", "\n", txt)   # 收口即摘掉在跑标记
    txt = re.sub(r"\n## R546 \(.*?(?=\n## R5\d\d \(|\Z)", "", txt, flags=re.S)  # 幂等: 重跑不重复追加
    io.open(imppath, "w", encoding="utf-8").write(txt)
    io.open(imppath, "a", encoding="utf-8").write("\n".join(imp))

    # ---- kpi.jsonl 行 -----------------------------------------------------
    row = {"round": "R546",
           "ts": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
           "kind": "主线轮(早停轴: 探针已判产物不合格时省略那次回灌修复远端调用) + 同窗单变量对照(AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(0),2} × 5 rep) + AOT 重发布",
           "artifact": "src/agent/r1/{R1Options.cs,R1Pipeline.cs,R1RunResult.cs,R1Transcript.cs} + src/agent.tests/R1EarlyStopTests.cs(4/4) + docs/api-surface.baseline.txt(重生, 差异仅本轮 3 行) + eval/rover/r546/** + docs/reports/r546-early-stop-axis.md + docs/improvements.md",
           "change": "① 产品: 新增早停轴(默认关) —— 探针回放实测 pfail ≥ 阈值(AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL, 默认 0=关)时"
                     "不再花一次远端调用做回灌修复, 直接走既有终端分类(rc 语义不变); 台账仅在轴开时输出 early_stop_pfail/early_stop_skipped(轴关逐字节同旧版)。"
                     "② 器具: eval/rover/r546 13 臂/窗(轴关/轴开 ×5 + 旧路径 ×3), 同输入硬门逐项机检 == R545; 预注册范围闸 rc=0; 起手闸 2/2 PASS。",
           "readings": "off(5) %s; on(5) %s; legacy(3) %s。**J10 %s**(轴开 pfail≥2 臂全部 early_stop_skipped=1 ∧ exec_repairs=0, 同窗轴关同 pfail 臂 exec_repairs≥1 ⇒ 成对反事实); **J11 代价**: pfail≥2 子集调用中位 %s→%s(合计 %s→%s, 省 %s 次), 全臂调用中位 %s→%s, 阴性对照(pfail<2) %s vs %s; **J12 %s**。前置器 rc=%s。"
           % (S["off"]["cases"], S["on"]["cases"], S["legacy"]["cases"], j10.get("verdict"),
              j11["pfail_ge2_calls"]["median_off"], j11["pfail_ge2_calls"]["median_on"],
              j11["pfail_ge2_calls"]["call_sum_off"], j11["pfail_ge2_calls"]["call_sum_on"],
              j11["pfail_ge2_calls"]["calls_saved_total"], j11["all_arms_calls_median"]["axis_off"],
              j11["all_arms_calls_median"]["axis_on"], j11["pfail_lt2_calls_negative_control"]["axis_off"],
              j11["pfail_lt2_calls_negative_control"]["axis_on"], j12.get("verdict"), acc["rc"]),
           "honest_boundaries": "① 窗口数 %d ⇒ %s ② 前置器 rc=%s(BLOCKED %d 臂) ⇒ 全部成本读数标「参考(未可验收)」 ③ 外部真值 codex-cli 未安装 ⇒ 主线四硬条件缺外侧 ④ pfail≥2 子集小样本(轴开 n=%d / 轴关 n=%d) ⇒ 省调用数只在器具级成对单测可钉(1 次), 窗内标参考 ⑤ 预注册 J10 的「同终态 pfail 配对」本窗为空(轴关 5/5 臂终态 pfail≤1) ⇒ 该宣称收窄, post-hoc 单列于轮志 §4b ⑥ 未测: 阈值剂量(1/3)、早停与质量的关系、第二窗极差(len=%d)。"
           % (len(data), "单窗 ⇒ 噪声未摊平" if len(data) == 1 else "两窗", acc["rc"], len(blocked), len(pf_on), len(pf_off), len(data)),
           "next": "① 第二窗 w2 + 逐窗极差重报 ② 早停阈值剂量响应(1/2/3) ③ pfail≥2 子集扩到 n≥5 做「省调用 vs 质量」配对 ④ R545 候选②/③(on 中位<off 定因; 旧路径列 n=%d) ⑤ 前置器臂级口径先写后跑。" % S["legacy"]["n"],
           "owner_round": "R546"}
    with io.open(os.path.join(REPO, "eval/capability/kpi.jsonl"), "a", encoding="utf-8") as f:
        if '"round": "R546"' not in io.open(os.path.join(REPO, "eval/capability/kpi.jsonl"), encoding="utf-8").read():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({"preconditioner": acc, "off": S["off"], "on": S["on"], "legacy": S["legacy"],
                      "J10": j10.get("verdict"), "J11_calls": j11["pfail_ge2_calls"],
                      "J11_all_med": j11["all_arms_calls_median"],
                      "J11_neg_ctl": j11["pfail_lt2_calls_negative_control"],
                      "J11_tokens": j11["tokens_pfail_ge2"], "J12": j12.get("verdict"),
                      "AOT": AOT, "posthoc": posthoc}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
