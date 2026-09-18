#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R547 装配器 —— **早停阈值的剂量面**(候选②) + **第二窗 w2**(候选①) + 旧路径列扩样(候选④)。

R547 单变量 = `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(=0 轴关), 1, 2, 3}` —— **同一变量的 4 个水平**。
  R546 只验了 {0,2} 两点: 机制"存在与否"被证; 但阈值是**连续可配**的参数, 其响应曲线(剂量-代价)
  从未被单变量检验 ⇒ 本轮把水平轴打开成 {0,1,2,3}。
    点估计(预注册, 先写后跑): δ=1 触发面最宽(pfail≥1) ⇒ 省调用最多; δ=2 次之; δ=3 在实测 pfail 分布上
    从未被跨过 ⇒ 应**逐位等于轴关**(判别性阴性对照 = 阈值真在把关, 而不是别的副作用)。
  其余全同(题面/用例/role/二进制/预算 MAX_EXEC_REPAIR=1/MAX_REPAIR=1/探针开关 PUBLIC_SELFCHECK=1)。

窗口面(w2): R546 的预注册 window_plan.windows 已声明 w1/w2 且臂清单同 ⇒ 本窗 = 该计划的第二窗
  (独立 session, 逐窗报 + 极差; **窗间只并列, 禁相减**)。旧路径列 A1on × 3/窗 ⇒ 两窗合计 n=6(候选④)。

铁律 11: 起臂前落盘本预注册; 收口跑 exec_precondition --round r547, rc≠0 ⇒ 降幅一律标「参考(未可验收)」。
用法: python3 eval/rover/r547/setup_r547.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
R546 = os.path.join(REPO, "eval/rover/r546")
R547 = os.path.join(REPO, "eval/rover/r547")
FAIL = []

REPS = ["a", "b", "c", "d", "e"]
D3_REPS = ["a", "b", "c"]
DOSE = {"E0": 0, "E1": 2, "D1": 1, "D3": 3}


def md5(path: str) -> str:
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def note(ok: bool, what: str, got: str, exp: str) -> None:
    print("  %-34s got=%s exp=%s ok=%s" % (what, str(got)[:20], str(exp)[:20], ok))
    if not ok:
        FAIL.append(what)


def main() -> int:
    os.makedirs(os.path.join(R547, "cases"), exist_ok=True)

    # --- 1 夹具逐字节复制 + md5 交叉核对 (同环境同输入硬条件①) -----------------
    pairs = [
        ("cases/run_cases_r521.py", "cases/run_cases_r521.py"),
        ("cases/cases-r521.json", "cases/cases-r521.json"),
        ("role-r546.txt", "role-r547.txt"),
    ]
    for src_rel, dst_rel in pairs:
        s, d = os.path.join(R546, src_rel), os.path.join(R547, dst_rel)
        shutil.copyfile(s, d)
        note(md5(s) == md5(d), "byte-identical " + dst_rel, md5(d), md5(s))

    # --- 2 题面: 从 r546 现盘读, 重算 sha256 (禁手抄) -------------------------
    ts546 = json.load(io.open(os.path.join(R546, "taskset-r546.json"), encoding="utf-8"))
    t546 = [x for x in ts546["tasks"] if x["tid"] == "g1"][0]
    prompt = t546["prompt"]
    psha = sha256_text(prompt)
    pin546 = json.load(io.open(os.path.join(R546, "input-pins-r546.json"), encoding="utf-8"))["g1"]
    note(psha == t546.get("prompt_sha256") == pin546["prompt_sha256"],
         "g1 prompt 跨轮同 (sha256)", psha, pin546["prompt_sha256"])
    note(int(t546["hidden_cases"]) == int(pin546["hidden_cases"]),
         "hidden_cases 跨轮同", str(t546["hidden_cases"]), str(pin546["hidden_cases"]))
    note(t546["cases"] == "cases/run_cases_r521.py", "cases 脚本相对路径同", t546["cases"], "cases/run_cases_r521.py")

    task = dict(t546)
    task["prompt_sha256"] = psha
    ts547 = {"round": "r547", "window": "w2",
             "source": "eval/rover/r546/taskset-r546.json (g1 单题面, 逐字节同)",
             "tasks": [task]}
    json.dump(ts547, io.open(os.path.join(R547, "taskset-r547.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # --- 3 输入钉 (全部现算) -------------------------------------------------
    pins = {"round": "r547", "recomputed_at_make_time": True,
            "g1": {
                "prompt_sha256": psha,
                "hidden_cases": int(t546["hidden_cases"]),
                "cases_script_md5": md5(os.path.join(R547, "cases/run_cases_r521.py")),
                "cases_json_md5": md5(os.path.join(R547, "cases/cases-r521.json")),
                "role_file_md5": md5(os.path.join(R547, "role-r547.txt")),
                "xref": [
                    {"what": "cases/run_cases_r521.py",
                     "same": md5(os.path.join(R547, "cases/run_cases_r521.py"))
                     == md5(os.path.join(R546, "cases/run_cases_r521.py")),
                     "r546_md5": md5(os.path.join(R546, "cases/run_cases_r521.py"))},
                    {"what": "cases/cases-r521.json",
                     "same": md5(os.path.join(R547, "cases/cases-r521.json"))
                     == md5(os.path.join(R546, "cases/cases-r521.json")),
                     "r546_md5": md5(os.path.join(R546, "cases/cases-r521.json"))},
                    {"what": "role-r547.txt",
                     "same": md5(os.path.join(R547, "role-r547.txt"))
                     == md5(os.path.join(R546, "role-r546.txt")),
                     "r546_md5": md5(os.path.join(R546, "role-r546.txt"))},
                    {"what": "g1 prompt", "same": psha == pin546["prompt_sha256"],
                     "r546_sha256": pin546["prompt_sha256"]},
                ],
                "check": "run_r547.sh 起臂前逐项机检 sha256/md5 与上表一致, 不一致 ⇒ fail-closed rc=3 不起臂"}}
    json.dump(pins, io.open(os.path.join(R547, "input-pins-r547.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # --- 4 预注册 (起臂前落盘) ----------------------------------------------
    arms = (["%s%s" % (p, r) for p in ("E0", "E1", "D1") for r in REPS]
            + ["D3" + r for r in D3_REPS] + ["A1on", "A1onb", "A1onc"])
    plan_arms = [{"snapdir": "agent%s-g1" % a, "side": "agent",
                  "switch": "early_stop=%d" % (DOSE[a[:2]] if a[:2] in DOSE else 0),
                  "column": {"E0": "d0(轴关)", "E1": "d2", "D1": "d1", "D3": "d3(阴控)"}.get(a[:2], "legacy-path"),
                  "rep": a[-1]} for a in arms]
    wins = ["w2"]
    require = ["%s/agent%s-g1" % (w, a) for w in wins for a in arms]
    prereg = {
        "round": "r547",
        "title": "早停阈值**剂量面**单变量: AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(0), 1, 2, 3}（g1 随机游戏长任务, 58 隐藏用例, 窗 w2）",
        "revision": 1,
        "supersedes": None,
        "made_before_run": True,
        "made_at": "2026-09-18T09:2x+08:00",
        "single_variable": "AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {0(轴关), 1, 2, 3} —— 同一变量的 4 个水平; δ=1/2 各 5 独立 session, δ=3 阴控 3, δ=0 5; 其余(题面/用例/role/二进制/MAX_EXEC_REPAIR=1/MAX_REPAIR=1/PUBLIC_SELFCHECK=1)全同",
        "mainline": "主线(用户 2026-09-17 钦定): 真实开发任务 × 机械判分(58 隐藏用例真跑, 非自报) 对本项目做质量自检; R413 的「一轮 token ↓≥30%(主要是不必要的远端调用少了)」是**该主线的判据之一**。本轮因果假设 = 探针已判产物不合格(pfail≥δ)时的那次回灌修复调用是**不必要请求**, 阈值 δ 决定其触发面。",
        "why_revision": "R546 只做了 {0,2} 两点 ⇒ 只知「机制存在」, 不知「阈值-代价响应」。阈值是可配参数; δ=1 触发面最宽, δ=3 应在实测分布上从不触发 ⇒ 三点定曲线 + 一点判别性阴性对照。",
        "window_plan": {
            "window": "w2", "windows": wins, "reps_per_side": 5, "arms": plan_arms,
            "windows_note": "w2 = R546 预注册 window_plan.windows=[w1,w2] 的第二窗(独立 session, 同臂清单/同输入); "
                            "w1 读数属 R546 轮(run-w1), 本轮**只并列引用**(逐窗报 + 极差), 禁跨轮相减。",
            "reason_of_extra_arms": "候选①(第二窗: 单窗=噪声) + 候选②(剂量曲线 δ=1/2/3) + 候选④(旧路径列 × 3/窗 ⇒ 两窗 n=6)。",
        },
        "evidence_scope": {
            "require": require, "nonrequired": [],
            "grader": "eval/rover/r547/cases/run_cases_r521.py (58 隐藏用例, 独立进程真跑, 机械判分; 禁模型裁判)",
            "scorer": "eval/rover/r547/snapshots/w2/*/g1/work (真实产物树快照)",
            "silent_failure_checks": [
                "rc==0 ∧ 用例未全过 = 假成功",
                "产物树为空 ⇒ 警告 + 不得当绿",
                "δ=0 臂台账出现 early_stop_* 字段或 reply 含 R1_EARLY_STOP ⇒ 零回归破(fail)",
                "δ>0 臂 pfail≥δ 但 early_stop_skipped≠1 ⇒ 机制未行使(判据证伪, 不得宣称省调用)",
                "δ=3 臂若出现 early_stop_skipped=1 ⇒ 阴控破(阈值语义被证伪, 须回前提)",
            ],
        },
        "judgments": {
            "K1_剂量机制(机械, 逐 δ)": "对 δ∈{1,2,3}: 臂 pfail ≥ δ ⇒ early_stop_skipped=1 ∧ exec_repairs=0 ∧ reply 含 R1_EARLY_STOP; pfail < δ ⇒ early_stop_skipped=0 ∧ 无 marker。pfail=None(探针未跑) ⇒ 该臂 VOID 单列, 不计入判据; 某类样本为空 ⇒ 标「该剂量未行使」。",
            "K2_剂量-代价(同窗三列)": "列 δ∈{0,1,2,3}: calls / prompt / completion / total 中位 + 极差。点估计: 行使臂数 δ=1 ≥ δ=2 ≥ δ=3(=0); δ=3 应逐位等于 δ=0(阴控)。",
            "K3_配对反事实(判据性)": "同窗内 pfail≥δ 子集, 按同 pfail 值配对 (δ 臂 vs δ=0 臂); 两类各 n≥5 ⇒ 报 calls 中位差 + total 比; 否则标「样本不足(n=..), 不作降幅宣称」(与 R546 J10 同口径: 未获得证据≠获得证据)。",
            "K4_质量非劣": "两维: ① 全绿臂数(58/58) ② 用例通过数中位 —— 逐 δ vs δ=0, 且行使臂 vs 未行使臂分开报; 收窄 ⇒ 如实报为「代价换质量」, 不得当增益。",
            "K5_零回归": "δ=0 臂台账无 early_stop_pfail/early_stop_skipped 字段 ∧ reply 无 R1_EARLY_STOP ⇒ 逐位旧行为; 既有测试全绿 ∧ AOT IL 警告 0。",
            "K6_窗口面(候选①)": "w2 与 w1(R546 run-w1 已发布读数) 逐列并列报: 每列 calls/用例中位 + 极差; **只在窗内算比值, 窗间只并列读数, 不做相减**。",
            "K7_旧路径列(候选④)": "逐窗 3 样本报极差, 两窗合计 n=6 并列; 质量前提不成立 ⇒ 比值只作参考。",
            "K8_收口(铁律11)": "exec_precondition --round r547 rc 原样记录; rc≠0 ⇒ 本轮一切降幅标「参考(未可验收)」, 禁作验收依据。",
        },
        "instrument_negative_control": {
            "what": "src/agent.tests/R1EarlyStopTests.cs —— 同沙盒/同脚本化 caller/同题面, 只翻 EARLY_STOP_PFAIL ∈ {0,1,5}: 0 ⇒ Calls=2(逐位旧行为); 1 ⇒ rc=8/public_probe_unmet ∧ Calls=1 ∧ 台账 early_stop_skipped=1; 5 ⇒ pfail=1<5 ⇒ 不触发(Calls=2) ⇒ 阈值语义负控。",
            "why_not_model_judge": "全部断言是整数计数与字段缺席, 可机检; 无模型裁判。",
        },
        "acceptance": "① 链真跑通(起手闸 2×PASS + 冒烟 + 全臂 idx 区间非空) ② 同窗读数证明判据(K1 机制逐 δ 机械可判 + K3 配对读数 + K4 质量非劣) ③ exec_precondition --round r547: rc≠0 ⇒ 降幅一律标「参考(未可验收)」。",
        "forbidden": ["模型裁判", "事后补记(判据/臂清单/阈值起臂后改)", "跨轮相减", "以链自报 rc 当正确性证据", "以本仓内部读数自证(无外部判据时须标注)"],
        "device_spec": "agenthost AOT (IL 警告 0, sha256=1224d3f4ec61d267…, 与 R546 同一二进制: 本轮**零产品源码改动**) + eval/rover/r455/adapter_tools.py 计量中继(FULL dump); 串行起臂(2 vCPU); 窗口超时 420s(旧路径 720s)。",
    }
    json.dump(prereg, io.open(os.path.join(R547, "prereg-r547.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n装配结果: %s" % ("PASS" if not FAIL else "FAIL(%s)" % ",".join(FAIL)))
    print("  臂(%d): %s" % (len(arms), " ".join(arms)))
    print("  require: %d 键 (窗 %s)" % (len(require), wins))
    return 0 if not FAIL else 3


if __name__ == "__main__":
    sys.exit(main())
