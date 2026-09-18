#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R546 装配器 —— 复用 R545 的同题同输入夹具(逐字节同), 只改**被测开关的语义面**。

R546 单变量 = `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(0=关), 2}`(R545 之后新增的**早停轴**)。
  动因(R545 同窗读数): 探针回放把「产物已在盘」的臂全部触达(触发面 v2 生效), 但 pfail≥2 的臂
  「再花一次远端调用做回灌修复」的**边际价值**从未被单变量检验过 —— 而 R413 的用户判据正是
  「一轮任务总 token ↓≥30%(主要是不必要的 LLM API 请求少了)」。早停轴把该假设做成可证伪:
  轴开 ⇒ pfail ≥ 阈值时**不再**花那次调用, 直接走既有终端分类(rc 语义不变)。
本装配器保证: 题面/用例/role 与 R545/R544 **逐字节相同**(否则跨窗读数不可比), 且全部数字现算。

产出(全部落在 eval/rover/r546/):
  cases/run_cases_r521.py, cases/cases-r521.json   ← 从 r545 复制(逐字节校验 md5)
  role-r546.txt                                    ← 从 r545 复制(逐字节校验 md5)
  taskset-r546.json, input-pins-r546.json          ← 依 r545 现盘重算, 禁手抄数字
  prereg-r546.json                                 ← 预注册(起臂前落盘; 含臂清单/判据/阴性对照)
用法: python3 eval/rover/r546/setup_r546.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
R545 = os.path.join(REPO, "eval/rover/r545")
R546 = os.path.join(REPO, "eval/rover/r546")
FAIL = []
REPS = ["a", "b", "c", "d", "e"]


def md5(path: str) -> str:
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def note(ok: bool, what: str, got: str, exp: str) -> None:
    print("  %-34s got=%s exp=%s ok=%s" % (what, got[:24], exp[:24], ok))
    if not ok:
        FAIL.append(what)


def main() -> int:
    os.makedirs(os.path.join(R546, "cases"), exist_ok=True)

    # --- 1 夹具逐字节复制 + md5 交叉核对 (同环境同输入硬条件①) -----------------
    pairs = [
        ("cases/run_cases_r521.py", "cases/run_cases_r521.py"),
        ("cases/cases-r521.json", "cases/cases-r521.json"),
        ("role-r545.txt", "role-r546.txt"),
    ]
    for src_rel, dst_rel in pairs:
        s, d = os.path.join(R545, src_rel), os.path.join(R546, dst_rel)
        shutil.copyfile(s, d)
        note(md5(s) == md5(d), "byte-identical " + dst_rel, md5(d), md5(s))

    # --- 2 题面: 从 r545 现盘读, 重算 sha256 (禁手抄) --------------------------
    ts545 = json.load(io.open(os.path.join(R545, "taskset-r545.json"), encoding="utf-8"))
    t545 = [x for x in ts545["tasks"] if x["tid"] == "g1"][0]
    prompt = t545["prompt"]
    psha = sha256_text(prompt)
    pin545 = json.load(io.open(os.path.join(R545, "input-pins-r545.json"), encoding="utf-8"))["g1"]
    note(psha == t545.get("prompt_sha256") == pin545["prompt_sha256"],
         "g1 prompt 跨轮同 (sha256)", psha, pin545["prompt_sha256"])
    note(int(t545["hidden_cases"]) == int(pin545["hidden_cases"]),
         "hidden_cases 跨轮同", str(t545["hidden_cases"]), str(pin545["hidden_cases"]))
    note(t545["cases"] == "cases/run_cases_r521.py", "cases 脚本相对路径同", t545["cases"], "cases/run_cases_r521.py")

    task = dict(t545)
    task["prompt_sha256"] = psha
    ts546 = {"round": "r546", "window": ts545.get("window", "w1"),
             "source": "eval/rover/r545/taskset-r545.json (g1 单题面, 逐字节同)",
             "tasks": [task]}
    json.dump(ts546, io.open(os.path.join(R546, "taskset-r546.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # --- 3 输入钉 (全部现算) --------------------------------------------------
    pins = {"round": "r546", "recomputed_at_make_time": True,
            "g1": {
                "prompt_sha256": psha,
                "hidden_cases": int(t545["hidden_cases"]),
                "cases_script_md5": md5(os.path.join(R546, "cases/run_cases_r521.py")),
                "cases_json_md5": md5(os.path.join(R546, "cases/cases-r521.json")),
                "role_file_md5": md5(os.path.join(R546, "role-r546.txt")),
                "xref": [
                    {"what": "cases/run_cases_r521.py", "same": md5(os.path.join(R546, "cases/run_cases_r521.py"))
                     == md5(os.path.join(R545, "cases/run_cases_r521.py")),
                     "r545_md5": md5(os.path.join(R545, "cases/run_cases_r521.py"))},
                    {"what": "cases/cases-r521.json", "same": md5(os.path.join(R546, "cases/cases-r521.json"))
                     == md5(os.path.join(R545, "cases/cases-r521.json")),
                     "r545_md5": md5(os.path.join(R545, "cases/cases-r521.json"))},
                    {"what": "role-r546.txt", "same": md5(os.path.join(R546, "role-r546.txt"))
                     == md5(os.path.join(R545, "role-r545.txt")),
                     "r545_md5": md5(os.path.join(R545, "role-r545.txt"))},
                    {"what": "g1 prompt", "same": psha == pin545["prompt_sha256"],
                     "r545_sha256": pin545["prompt_sha256"]},
                ],
                "check": "run_r546.sh 起臂前逐项机检 sha256/md5 与上表一致, 不一致 ⇒ fail-closed rc=3 不起臂"}}
    json.dump(pins, io.open(os.path.join(R546, "input-pins-r546.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # --- 4 预注册 (起臂前落盘) ------------------------------------------------
    arms_agent = ["E0" + r for r in REPS] + ["E1" + r for r in REPS]
    arms_leg = ["A1on", "A1onb", "A1onc"]
    arms = arms_agent + arms_leg
    wins = ["w1", "w2"]
    plan_arms = ([{"snapdir": "agent%s-g1" % a, "side": "agent",
                   "switch": "early_stop=0(轴关)" if a.startswith("E0") else (
                       "early_stop=2(轴开)" if a.startswith("E1") else "legacy-path"),
                   "rep": a[-1]} for a in arms_agent]
                 + [{"snapdir": "agent%s-g1" % a, "side": "agent", "switch": "legacy-path", "rep": str(i + 1)}
                    for i, a in enumerate(arms_leg)])
    require = ["%s/agent%s-g1" % (w, a) for w in wins for a in arms]
    prereg = {
        "round": "r546",
        "title": "早停轴单变量对照: AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(0), 2}（g1 随机游戏长任务, 58 隐藏用例）",
        "revision": 1,
        "supersedes": None,
        "made_before_run": True,
        "made_at": "2026-09-18T08:1x+08:00",
        "single_variable": "AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(=0 轴关), 2(轴开)} —— 5 独立 session × 2 列 × 2 窗; 其余(题面/用例/role/二进制/预算 MAX_EXEC_REPAIR=1/探针开关 PUBLIC_SELFCHECK=1)全同",
        "mainline": "主线(用户 2026-09-17 钦定): 真实开发任务 × 机械判分(58 隐藏用例真跑, 非自报) 对本项目做质量自检; R413 的「一轮 token ↓≥30%(主要是不必要的远端调用少了)」是**该主线的判据之一**。本轮的因果假设 = 探针已判产物不合格时的那次回灌修复调用是**不必要请求**。",
        "why_revision": "R545 已把触发面 v2(产物在盘的全部出口)落地 ⇒ 探针在 pfail≥2 的臂上必然可见; 但「再花一次调用修复」的边际价值从未被单变量检验 ⇒ 本轮把「省掉它」做成可证伪轴(而非直接改动默认行为)。",
        "disclosure": [
            "早停轴**默认关**: 只有显式设 EARLY_STOP_PFAIL>0 才生效 ⇒ 轴关臂逐位等于 R545 行为(台账字段缺席可机检)。",
            "早停只跳过「探针证据回灌」的那一次调用; 执行实测(exec)证据回灌预算在轴开臂上同样被终止 —— 这是轴的定义, 不是副作用。",
            "rc 语义不变: 仍由既有终端分类给出; 早停只在 reason 里标注 + 台账新增 early_stop_pfail/early_stop_skipped。",
            "本窗**无外部模型侧(codex-cli 未安装/未起)**: 判分器是题面衍生的 58 条隐藏用例(独立进程真跑), 属机械判分, 但不等于跨模型对照。",
        ],
        "window_plan": {
            "window": "w1", "windows": wins, "reps_per_side": 5, "arms": plan_arms,
            "reason_of_extra_arms": "候选②(采样方差: 5 次/列单窗不够 ⇒ 两窗独立 session, 逐窗 + 极差); 候选③(旧路径列 R542=4 调用/R544=34 调用 8.5× 摆动 ⇒ 每窗 3 样本, 两窗合计 6)。",
        },
        "evidence_scope": {
            "require": require, "nonrequired": [],
            "grader": "eval/rover/r546/cases/run_cases_r521.py (58 隐藏用例, 独立进程真跑, 机械判分; 禁模型裁判)",
            "scorer": "eval/rover/r546/snapshots/<w>/*/g1/work (真实产物树快照)",
            "silent_failure_checks": [
                "rc==0 ∧ 用例未全过 = 假成功(计入 J2)",
                "产物树为空 ⇒ 警告 + 不得当绿",
                "轴关(E0)臂台账出现 early_stop_* 字段或 reply 含 R1_EARLY_STOP ⇒ 零回归破(fail)",
                "轴开(E1)臂 public_probe_failed≥2 但 exec_repairs>0 ⇒ 机制未生效(判据证伪, 不得宣称省调用)",
            ],
        },
        "judgments": {
            "J1_机制(轴真生效, 机械+成对反事实)": "轴开臂中 public_probe_failed ≥ 2 的臂 ⇒ early_stop_skipped=1 ∧ exec_repairs=0 ∧ reply 含 R1_EARLY_STOP; 同窗轴关臂中同 pfail 的臂 ⇒ exec_repairs≥1(回灌真发生) ⇒ 成对反事实成立。两类样本都有臂才判; 某类为空 ⇒ 标「机制未被行使」。",
            "J2_代价(主线判据之一)": "配对比较(pfail≥2 子集, 按同 pfail 值配对): 轴开臂远端调用数 / prompt / completion / total 中位 vs 轴关臂; 预注册点估计 = 每臂少 1 次调用。判别性阴性对照 = pfail<2 子集(轴不应改变其调用数)。",
            "J3_质量(不得降)": "两维非劣: ① 全绿臂数(58/58) ② 用例通过数中位; 收窄 ⇒ 如实报为「代价换来的质量代价」, 不得当增益。",
            "J4_零回归": "轴关臂台账无 early_stop_* 字段 ∧ reply 无 R1_EARLY_STOP ∧ 既有测试 1876 全绿 ∧ AOT IL 警告 0; 另: 器具级成对单测(同输入: 轴关 Calls=2 / 轴开 Calls=1)。",
            "J5_旧路径列": "逐窗 3 样本报极差; **禁跨轮相减**; 质量前提不成立 ⇒ 比值只作参考。",
        },
        "instrument_negative_control": {
            "what": "src/agent.tests/R1EarlyStopTests.cs —— 同一沙盒/同一脚本化 caller/同一题面, 只翻 EARLY_STOP_PFAIL ∈ {0,1,5}: 0 ⇒ Calls=2(修复真发生, 逐位旧行为); 1 ⇒ rc=8/public_probe_unmet ∧ Calls=1 ∧ exec_repairs=0 ∧ 台账含 early_stop_skipped=1; 5 ⇒ pfail=1<5 ⇒ 不触发(Calls=2) ⇒ 负控(阈值语义)。",
            "why_not_model_judge": "全部断言是整数计数与字段缺席, 可机检; 无模型裁判。",
        },
        "acceptance": "① 链真跑通(起手闸 2×PASS + 冒烟 + 全臂 idx 区间非空) ② 同窗读数证明判据(调用数/prompt/completion/total 配对读数 + 质量非劣) ③ 前置器 eval/rover/r507pre/exec_precondition.py --round r546: rc≠0 ⇒ 本轮的降幅一律标「参考(未可验收)」, 禁作验收依据。",
        "forbidden": ["模型裁判", "事后补记(判据/臂清单/阈值起臂后改)", "跨轮相减", "以链自报 rc 当正确性证据", "以本仓内部读数自证(无外部判据时须标注)"],
        "device_spec": "agenthost AOT (IL 警告 0) + eval/rover/r455/adapter_tools.py 计量中继(FULL dump); 串行起臂(2 vCPU); 窗口超时 420s(旧路径 720s)。",
    }
    json.dump(prereg, io.open(os.path.join(R546, "prereg-r546.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n装配结果: %s" % ("PASS" if not FAIL else "FAIL(%s)" % ",".join(FAIL)))
    print("  臂: %s" % " ".join(arms))
    print("  require: %d 键 (窗 %s)" % (len(require), wins))
    return 0 if not FAIL else 3


if __name__ == "__main__":
    sys.exit(main())
