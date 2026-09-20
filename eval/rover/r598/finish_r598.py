#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R598 收尾: ① §7 轮块追加（幂等）② `eval/capability/kpi.jsonl` 追加（幂等，按 tag 去重）。

纪律: 只用**文本插入**（在锚点行之后），禁整份重排；插入后回读断言（新块计数=1、旧轮块未动）。
用法: python3 eval/rover/r598/finish_r598.py [--landing-match TRUE|FALSE|PENDING]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess

REPO = "/home/agentuser/AgentFramework"
PLAN = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
KPI = os.path.join(REPO, "eval/capability/kpi.jsonl")
ANCHOR = "- **下轮候选 (R598)**:"
TAG = "mainline-contrast-windowset6"


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(s)


def block(landing_match: str) -> str:
    lm = {"TRUE": "match=True ⇒ 器具完好（单窗集读法伪影已定因）",
          "FALSE": "match=False ⇒ 器具缺陷，候选④ 本项不入结论",
          "PENDING": "本轮复算件仍在飞（bounded wait），如实登记为未闭合"}[landing_match]
    return ("\n- **R598（真机臂轮: 判据 v3 **第六窗集** w178..w180 × 外部真值 codex + 只读并轮 候选②③④⑤；"
            "零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件同题集）**: "
            "**主判据 v3** set6 **valid=2 / 中位 -0.3333 / 负号窗 2 ⇒ 不达 PASS 形态**"
            "（距阈值 -0.34 差 0.0067；真值 w178 自败 56/58 ⇒ 按 C0 unreliable 不进配对、禁筛窗；"
            "有效窗 2 ⇒ 不作能力结论）；族 all-pass `wythoff` set6=**0.5556**"
            "（set1 0.3889 / set2 0.4444 / set5 0.7778 并列，禁相减）。"
            "**候选②**（真值侧 wythoff 缺口归因，只读普查 r585..r598 共 27 窗）: 真值失败**全部**落 wythoff"
            "（10/27 窗、38 例次；life/nim/sub = 0），失败集合 6 种（非常量）⇒ 判 **真值臂自身漂移**；"
            "「两侧失败集合逐字相同」窗 = 0 ⇒ 题面/夹具嫌疑**未现**；`wythoff#43-public + wythoff#57-hidden` 在 4 窗逐字重复"
            "（r596 w173 / r597 w175、w176 / r598 w178）；控制 NEG-A 确定性=True、NEG-B 非平凡=True、POS 注入 ③→①=True；rc=0。"
            "**候选③** C7 负控选择面改制（器具缺陷修法）: v1（保留不覆写）r1-only 选择面 ⇒ set5/set6 无靶 rc=2；"
            "v2（全产品跑次）靶点 set5 w176 / set6 w178 ⇒ has_teeth True、rc=0，**判定面差异全字段 NONE（6/6 窗集）**；"
            "`checks_posthoc`: rc 与判据判定脱钩（v2 下 set5/set6 rc=0 而 C1.pass=False），本轮不改、留档待下轮预注册。"
            "**候选④** `V_int` 第五窗集: agent 层 {(c)6,(b)3}、桶 {D 14, A 2, B 16}、`v_int_hist` {0:7, 25:1, 35:1}（**阈值化仍未测**）；"
            "codex 桶 {D 2}、层 {(c)3}；份额差 A +0.0625 / B +0.5 / D -0.5625；"
            "零回归=False 属单窗集 scope 伪影（历史全集 r585–r588+r591 复算 " + lm + "）。"
            "**行为面普查** r598: agent 81 跑次 {OK 73, ENTRY_FAIL 2, INTERNAL 4, TIMEOUT 1}、codex 27/27 OK；"
            "ENTRY_FAIL 2 例同报 `games.wythoff has no attribute 'solve'`。"
            "**逐例归因**（27 窗 1566 例次）: {OK 1235, A2 271, E 30, A 22, B 6, C 2}、A 份额 0.0140；交叉校验 6262/0。"
            "**候选⑤** 余量源 r597 实测振幅 83MB ⇒ ceiling 2856 / margin 83 / REQ **2733**（cap_binding=False）⇒ A1/A2 PASS "
            "+ 判别力成对控制 true_discrimination=true；起手前清场（own-tool reap 177MB + drop_caches）已登记。"
            "**成本三列（参考·未可验收）**: 产品 17 调用 / 4293 新算 / 39556 completion vs 真值 48 / 25636 / 20462；"
            "命中率 v_all 0.98/0.95、v_incr 0.96/0.97（口径 = 中继 dump 时间轴）。"
            "**铁律 11 rc=1**（blocked 5 条，全落 wythoff）⇒ 全部读数标「参考（未可验收）」。"
            "轮志 `eval/rover/r598/report-r598.md`。\n"
            "\n- **下轮候选 (R599)**: ① **产品侧处置裁定（待用户放行）**：落点收束到 `wythoff` 冷集构造层（候选④ B 份额 +0.5）"
            "与产物侧入口契约（ENTRY_FAIL 2 例）② **rc 语义收口（预注册）**：把验收面（`C1_task_face_v3.pass`）编入 rc（fail-closed），"
            "配历史判决审计证明「纯收紧、判决中性」 ③ **真值侧弱点面收口**：`wythoff#43-public + wythoff#57-hidden` 文本级定因（真值产出 vs 期望）"
            " ④ `V_int` 第六窗集 + landing 零回归面**钉到可复现 scope**（消除单窗集伪影） ⑤ 起手闸余量按 r598 实测振幅重派生。\n")


def do_plan(landing_match: str) -> str:
    s = rd(PLAN)
    if "R598（真机臂轮" in s:
        return "plan: 已存在 R598 块 ⇒ 跳过（幂等）"
    i = s.index(ANCHOR)
    j = s.index("\n", i) + 1
    s2 = s[:j] + block(landing_match) + s[j:]
    assert s2.count("R598（真机臂轮") == 1, "插入后 R598 块计数 != 1"
    assert "- **下轮候选 (R599)**" in s2
    assert s.count("- **R597（真机臂轮") == s2.count("- **R597（真机臂轮") == 1, "R597 块被改动"
    wr(PLAN, s2)
    return "plan: 追加 R598 块 + 下轮候选(R599)；R597 块逐字未动"


def do_kpi(landing_match: str) -> str:
    rec = {
        "round": "R598", "ts": "2026-09-20T19:07+0800", "tag": TAG,
        "taskset_sha": "e0c667c2a313c04b", "bin_sha12": "4b70fd7cdb39",
        "judge_v3_set6": {"valid": 2, "median": -0.3333, "neg": 2, "pass": False,
                          "note": "距阈值 -0.34 差 0.0067；真值 w178 自败 56/58 按 C0 unreliable（有效窗 2 ⇒ 不作能力结论）"},
        "family_wythoff_allpass": {"set1": 0.3889, "set2": 0.4444, "set5": 0.7778, "set6": 0.5556},
        "cost_three_columns": {
            "product": {"calls": 17, "new_prompt": 4293, "completion": 39556, "v_all": 0.98, "v_incr": 0.96},
            "truth": {"calls": 48, "new_prompt": 25636, "completion": 20462, "v_all": 0.95, "v_incr": 0.97}},
        "iron11": {"rc": 1, "blocked": 5, "readable": "参考（未可验收）"},
        "candidates": {
            "c2_truth_side_wythoff_gap": {"windows": 27, "truth_fail_windows": 10, "truth_fail_cases": 38,
                                          "distinct_truth_failure_sets": 6, "both_sides_identical_windows": 0,
                                          "state": "② 真值臂自身漂移", "rc": 0},
            "c3_c7_nc_selection_face": {"v1_target": None, "v1_rc": 2, "v2_target_set5": "w176", "v2_target_set6": "w178",
                                        "v2_has_teeth": True, "judgment_face_diff": "NONE"},
            "c3_behav_census": {"agent_runs": 81, "agent_ok": 73, "entry_fail": 2, "codex_ok": 27, "codex_runs": 27},
            "c4_v_int_hist": {"agent": {"0": 7, "25": 1, "35": 1}, "codex": {"0": 3}, "thresholding": "未测"},
            "c4_landing_zero_regression": {"single_window_set": False, "history_recompute": landing_match},
            "c5_margin": {"prev_swing": 83, "req": 2733, "cap_binding": False},
            "c2_percase_A_share": 0.0140},
        "instrument_selfcatch": [
            "C7 负控选择面 r1-only ⇒ set5/set6 无靶 rc=2（v1 保留；v2 修法后判定面差异全字段 NONE）",
            "checks_posthoc: rc 与判据判定脱钩（v2 下 rc=0 而 C1.pass=False）— 本轮不改",
            "landing 零回归=False = 单窗集 scope 伪影",
            "起手闸首采 CEIL 2765 ⇒ CAP 55 < floor 60 fail-closed；清场后 CEIL 2856 窗口开启"],
        "report": "eval/rover/r598/report-r598.md"}
    lines = [l for l in io.open(KPI, encoding="utf-8") if l.strip()]
    for l in lines:
        try:
            if json.loads(l).get("tag") == TAG:
                return "kpi: tag 已存在 ⇒ 跳过（幂等）"
        except Exception:  # noqa: BLE001
            pass
    with io.open(KPI, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    n = sum(1 for l in io.open(KPI, encoding="utf-8") if l.strip())
    assert n == len(lines) + 1, "追加后行数不符"
    return "kpi: 追加 1 行（共 %d 行，此前 %d）" % (n, len(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--landing-match", default="PENDING", choices=["TRUE", "FALSE", "PENDING"])
    a = ap.parse_args()
    print(do_plan(a.landing_match))
    print(do_kpi(a.landing_match))
    subprocess.run(["python3", "-c", "import json,io;"
                    "d=json.load(io.open('%s'));"
                    "print('kpi 尾行 round=',d['round'],'tag=',d['tag'])" % KPI], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
