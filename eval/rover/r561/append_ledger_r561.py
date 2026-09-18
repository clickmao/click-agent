#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R561 台账行追加 (键集 == 既有同族行健集; 写后全文件逐行可解析; 幂等)。"""
import io, json, os, sys

LEDGER = "/home/agentuser/AgentFramework/eval/capability/kpi.jsonl"
row = {
 "round": "R561",
 "ts": "2026-09-18T20:52:00+0800",
 "kind": ("判据口径修订 + 剂量轴收口轮 (离线判定轮: 零远端调用 / 零产品源码改动 / 零新增夹具与开关 / 零新臂) —— "
          "对 R559(w104–w106) + R560(w107–w112) 的 27 个冻结臂窗用同一件判分器 (sha a67215a7…) 对副本离线重判; "
          "复算一致性负控 = 27/27 臂窗 cases_pass 与已落盘 report.json 逐窗相等"),
 "artifact": ("eval/rover/r561/{prereg-r561.json,matrix_r561.py,verdict_r561.py,readings_r561.py,percase-matrix-r561.json,"
              "verdict-r561.json,freeze-premise-r561.json,readings-r561.jsonl,kpi-table-r561.json} · "
              "轮志 docs/reports/r561-judge-v2-and-dose-axis-closure.md"),
 "change": ("六格③(回执质量)/⑤(tokens)/④(轮数): 质量判据由 v1「臂中位>=真值中位-2 ∧ 极差<=5」(真值自身极差 11 ⇒ 结构性不可达)"
            "改为 v2「只在真值可靠窗上逐窗配对 (n>=3 ∧ 无窗<=-3 ∧ 配对中位>=-2) + 真值崩窗 unreliable + VOID 臂窗单列 + 影子自检 6 夹具」; "
            "剂量轴按前提机检结果自降一档 (不得封存为「已证无增益」) ⇒ 停用实验轴 + 产品默认不改 + 写死重开条件; "
            "铁律 11 require 口径据宪法原文判定 (含对照臂) 不留待裁"),
 "readings": {
  "主判窗_R560_6窗": [
   {"arm": "C1 codex 真值", "cases": [56, 47, 58, 58, 58, 52], "median": 57.0, "range": 11, "calls": 37,
    "new_prompt": 22303, "completion": 18837, "hitrate_v_all": "0.8943-0.9537", "steps": "未测",
    "note": "真值自身 3 窗有错题 (w107/w108/w112) ⇒ 铁律 11 亦 blocked"},
   {"arm": "R560B0 (exec=0)", "cases": [56, 58, 45, 45, 55, 53], "median": 54.0, "range": 13, "calls": 6,
    "new_prompt": 906, "completion": 14576, "hitrate_v_all": "0.9819", "steps": "67/87",
    "judge_v2": "未过 (配对 med -8.0, 点名 w109/w110/w111)"},
   {"arm": "R560B3 (exec=3)", "cases": [50, 47, 58, 43, 58, 55], "median": 52.5, "range": 15, "calls": 25,
    "new_prompt": 8874, "completion": 51912, "hitrate_v_all": "0.9443-0.9701", "steps": "41/55",
    "judge_v2": "未过 (配对 med -3.0, 点名 w107/w110)", "dose": "exec_repairs=3 6/6 窗"}
  ],
  "次判窗_R559_3窗_交叉校验": [
   {"arm": "R559B3 (exec=3)", "cases": [56, 58, 56], "median": 56, "range": 2, "calls": 9, "new_prompt": 2933,
    "completion": 19699, "judge_v2": "过 (配对 med -2.0, 无点名窗) —— 与旧判据在本窗集的结论一致"},
   {"arm": "R559B0 (exec=0)", "cases": [0, 45, 46], "median": 45, "calls": 3, "new_prompt": 453, "completion": 6191,
    "judge_v2": "未过 (n=2, 配对 med -12.5)", "w104": "arm_void(rc=8 public_probe_unmet) 单列排除"}
  ],
  "真值可靠性分类": "unreliable <=> truth_cases <= median(9窗)-3 (=55) ⇒ w108(47)/w112(52) 排除出红绿, 单列",
  "族分布_9窗口径": {"R560B0": {"wythoff": "59/90", "life": "84/84", "nim": "90/90", "sub": "79/84"},
                    "R560B3": {"wythoff": "53/90", "life": "84/84", "nim": "90/90", "sub": "84/84"}},
  "逐例稳定性": "R560B0 wythoff 15 例中 13 摆动 / 2 恒过 / 0 恒败; R560B3 15 例全摆动",
  "封存前提机检": {"行使": "6/6 ✓", "质量无增益(两轮同向)": "否 (R559 45 vs 56 · R560 54.0 vs 52.5)",
                   "成本劣化": "6/6 窗 >30% ✓", "premise_ok": False,
                   "on_fail": "不得封存为「已证无增益」⇒ 实际裁定自降一档: 停用实验轴 + 产品默认不改 + 写死重开条件"},
  "判据器自检": "影子自检 6/6 (rc 0/1/2/3 各分支) has_teeth=true; 判定 rc=1 (quality_paired_shortfall:R560B0,R560B3)",
  "铁律11": {"rc": 1, "cmd": "eval/rover/r507pre/exec_precondition.py --round r560",
             "blocked": "12 项 (含真值臂 w107/w108/w112), 错题全部落 wythoff"},
  "轮成本": {"remote_calls": 0, "new_prompt": 0, "completion": 0}
 },
 "honest_boundaries": ("本轮零新臂 ⇒ 不宣称任何成本/质量降幅; 离线复判与 R559/R560 窗并列不相减; 判据 v2 的增量是"
                       "「真值崩窗不再产出红」+「VOID 臂窗不再混算」= 测量终于准确, 前后数字不可直接比; "
                       "unreliable 用中位数相对规则对「真值整体性崩塌」不报警 (写入判据注释, 非事后调阈值); "
                       "器具自捕三处 (自检结论从被检对象内部读 ⇒ 6/6 夹具 rc=2 / 臂作用域跨轮伪红 / VOID 臂窗混入配对); "
                       "未做候选: 交付闸与停止条件 (rc=8,rc=5 仍交付) 与 wythoff 契约加厚 v3 均需新增产品分支 ⇒ 用户令禁止, 未放行"),
 "owner_round": "R561",
 "next": ("wythoff 族按族定因 (分布已落盘) / 判据 v2 写进 external-reference-harness 作为正式口径 (v1 声明作废) / "
          "交付闸待放行"),
}

existing = [json.loads(l) for l in io.open(LEDGER, encoding="utf-8") if l.strip()]
if any(r.get("round") == "R561" for r in existing):
    print("ALREADY_PRESENT round=R561 (幂等跳过)")
    sys.exit(0)
assert set(row.keys()) == set(existing[-1].keys()), (sorted(row.keys()), sorted(existing[-1].keys()))
with io.open(LEDGER, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
rows = [json.loads(l) for l in io.open(LEDGER, encoding="utf-8") if l.strip()]
print("APPENDED rows=%d last_round=%s" % (len(rows), rows[-1]["round"]))
