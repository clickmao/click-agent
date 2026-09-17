#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 R531 预注册 (落盘于任何臂启动之前)。

用法: python3 eval/rover/r531/build_prereg_r531.py [--ts <ISO8601Z>]
缺省 ts = 真实时钟 (date -u); **禁占位简写**。
"""
import argparse, hashlib, io, json, os, subprocess

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r531")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default="")
    ap.add_argument("--out", default=os.path.join(R, "prereg-r531.json"))
    a = ap.parse_args()
    now = a.ts or subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                                 capture_output=True, text=True).stdout.strip()
    ts = json.load(io.open(os.path.join(R, "taskset-r531.json"), encoding="utf-8"))
    tasks = ts["tasks"] if isinstance(ts, dict) and "tasks" in ts else ts
    by = {t["tid"]: t for t in tasks}
    cases_sha = {tid: sha(os.path.join(R, by[tid]["cases"])) for tid in ("g1", "t1", "m1")}
    d = {
        "round": "R531",
        "title": ("第三题族(数学 mathkit-multimodule-v1) + 合批轴(第7条纪律, "
                  "AGENTFRAMEWORK_ACTION_MERGE) 同窗对照 + 预注册窗声明面机读化(fail-closed) "
                  "+ 外部真值侧伪影假设机检证伪"),
        "prereg_sealed_ts": now,
        "sealed_note": ("本文件在任何臂启动之前落盘; 下行 policy_declared_ts 与各窗 artifacts.json 的 mtime "
                        "由前置器机检比对 (后者早于前者 ⇒ 本策略拒绝生效, rc 保持 1)"),
        "single_variable": ("env AGENTFRAMEWORK_ACTION_MERGE (缺省 off/显式 on) —— A2-merge 与 A1-on 的唯一差异即"
                            "第 7 条合批纪律文本; A1-on vs A0-off 为承 R529 的纪律轴 (off = 等价 R521 旧行为)"),
        "families": {
            "F1": {"name": "games-longtask-v1",
                   "role": "可比锚 (58 隐藏用例族; 题面逐字节复用 R519-521)",
                   "prompt_sha256_pin": by["g1"]["prompt_sha256"],
                   "cases_sha256": cases_sha["g1"]},
            "F2": {"name": "toolkit-multimodule-v1",
                   "role": "承 R529 逐字节复用 (题面 prompt 字段与 r529 taskset 同值 ⇒ 同输入)",
                   "prompt_sha256_pin": by["t1"]["prompt_sha256"],
                   "cases_sha256": cases_sha["t1"]},
            "F3": {"name": "mathkit-multimodule-v1",
                   "role": "**新增第三题族 (数学难题, 非游戏/非程序题)**: 5 算子 / 4 模块 CLI, 逐模块可测",
                   "material_source": "eval/probe/tasks.py MATH_FAMILIES (5 族, 每族 ref/check 两条独立实现)",
                   "selection_rule": ("每族 6 隐藏 + 1 公开 (seed 531) ⇒ 隐藏 30 / 公开 5; "
                                      "落盘值仅由 ref 路径产生且与 check 路径逐条比对一致"),
                   "graders": ("双非同源: 前置器侧 cases/run_cases_r531_math.py (落盘列 + tasks.py check 路径重算) / "
                               "冻结期 grade_f3_r531.py (独立重算 5 算子, 不 import tasks.py)"),
                   "prompt_sha256_pin": by["m1"]["prompt_sha256"],
                   "cases_sha256": cases_sha["m1"]}},
        "window_plan": {
            "windows": ["w1", "w2", "w3"],
            "arms": [
                {"run": "A0-off", "side": "agent", "snapdir": "agentA0-off", "tag": "A0-off",
                 "families": ["F1", "F2", "F3"], "env": "AGENTFRAMEWORK_ACTION_DISCIPLINE=off"},
                {"run": "A1-on", "side": "agent", "snapdir": "agentA1-on", "tag": "A1-on",
                 "families": ["F1", "F2", "F3"], "env": "AGENTFRAMEWORK_ACTION_MERGE=off (纪律默认开)"},
                {"run": "A2-merge", "side": "agent", "snapdir": "agentA2-merge", "tag": "A2-merge",
                 "families": ["F1", "F2", "F3"], "env": "AGENTFRAMEWORK_ACTION_MERGE=on"},
                {"run": "C-codex", "side": "codex", "snapdir": "codex", "tag": "codex",
                 "families": ["F1", "F2", "F3"], "env": ""}],
            "tasks_per_arm": ["g1(F1 锚, 58 隐藏用例)", "t1(F2 复用, 30 隐藏用例)", "m1(F3 新增数学, 30 隐藏用例)"],
            "snapshot_layout": "snapshots/w1/<snapdir>/<tid>/**",
            "note": ("快照目录名 = 自报臂标签 ⇒ 前置器 _dir_to_tag 与 report.json 严格对齐; "
                     "windows[] 为机读字段 (prereg_scope_gate v2 在窗计划缺失时 fail-closed rc=3)")},
        "evidence_scope": {"require": ["%s/%s" % (w, s) for w in ("w1", "w2", "w3")
                                       for s in ("agentA0-off", "agentA1-on", "agentA2-merge", "codex")],
                           "nonrequired": []},
        "unreliable_policy": {
            "rule": "truth_arm_window_unavailable", "declared_before_run": True, "policy_declared_ts": now,
            "truth_arm_patterns": ["*/codex"],
            "effect": ("该窗外侧(codex)臂未全对 ⇒ 该窗对照列标 unreliable 并从验收面移出, 只单列; "
                       "验收面剩余部分仍按 require ∪ 未声明 判定"),
            "bars": ["B1 本侧(agent*)臂的任何失败一律不得被本规则吞掉 (始终进 blocked_scoped)",
                     "B2 策略须在起臂前声明: 任一窗 artifacts.json 的 mtime 早于 policy_declared_ts ⇒ 策略整体拒绝生效 rc 保持 1",
                     "B3 规则不得改变 require 中的本侧臂集合"],
            "posthoc_forbidden": "不得事后收窄 evidence_scope / 不得事后追加本键"},
        "codex_artifact_policy": {
            "rule": "codex_cleanup_retry_artifact", "declared_before_run": True,
            "probe": "eval/rover/r531/probe_codex_artifact_r531.py",
            "probe_input": "R529 三窗既有 adapter dump (只读, 不新跑臂)",
            "finding": ("FALSIFIED(证据不存在): 627 dumps / 628 tool_calls, 同一命令最大重复 = 2 (<5), "
                        "无歧义拒绝措辞命中 = 0"),
            "effect": ("本轮不建任何清理/审批干预机制 (禁预防性机制轮); 若本窗实测出现 LOOP_SUSPECT "
                       "(同命令重复 >= 5) 则该窗对照列单列并标 artifact, 不作判据依据"),
            "posthoc_forbidden": "不得事后把该键改写成阈值后置"},
        "predictions": {
            "P1_merge_calls_drop": "A2-merge 相对 A1-on 调用数降 >= 15% (同窗同题聚合)",
            "P2_merge_completion_drop": "A2-merge 相对 A1-on completion 降 >= 15%",
            "P3_quality": "两侧 F3 均 30/30; A2-merge 的 F1/F2 不得低于 A1-on (质量不降)",
            "calls_drop_pct_min": 30, "new_prompt_drop_pct_min": 30, "completion_drop_pct_min": 40},
        "criteria": {
            "J1": "F3 夹具契约机检: 正控 30/30 ∧ 4 变异体全红 ∧ 双判分器红绿集合逐条对齐 (nc_grader_f3_r531.py rc=0)",
            "J2": "双判分器非同源: grade_f3_r531.py 不 import tasks.py (机检 import 面)",
            "J3": "铁律 11 前置器 --round r531 rc=0 (双侧落盘摘要, 三题逐条点名)",
            "J4": "合批轴同窗对照出数 (A2-merge vs A1-on 的 calls/completion, 逐窗 + 极差)",
            "J5": "F1 锚 58/58 ∧ F2 30/30 (本侧臂; 不得低于承继基线)",
            "J6": ("预注册窗声明面: prereg_scope_gate v2 对 r531 预注册 (含 windows[]) rc=0; "
                   "对 R529 无 windows[] 预注册 rc=3 fail-closed (负控)")},
        "kpi_columns": ["calls", "new_prompt(=prompt-cached)", "cached", "hit_pct", "completion",
                        "cases_pass/total"],
        "forbidden": ["跨轮相减", "模型裁判", "事后补记", "事后收窄验收面", "push"],
        "taskset_sha256": sha(os.path.join(R, "taskset-r531.json")),
        "taskset_sha256_r529": sha(os.path.join(REPO, "eval/rover/r529/taskset-r529.json")),
        "prereg_self_sha256_note": "本文件 sha256 在 freeze 时记入 evidence/index-r531.json",
    }
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print("sealed_ts=%s\nwrote %s (%d bytes)\ntaskset_sha=%s" %
          (now, a.out, os.path.getsize(a.out), d["taskset_sha256"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
