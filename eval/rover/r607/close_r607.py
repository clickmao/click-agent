#!/usr/bin/env python3
"""R607 收口登记（幂等）: registry 行 + kpi 行。

纪律（EXP1-Q39 / R409）:
  ① 改写前先断言「序列化器逐字节复现原文件」（indent=1 / ensure_ascii=False / 尾 LF）——断言不过就改文本插入；
  ② 幂等（按 id / round 去重）；③ 只做加法；④ 写后读回校验（不只看返回）。
"""
import hashlib
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REG = ROOT / "docs/verification-registry.json"
KPI = ROOT / "eval/capability/kpi.jsonl"


def sha12(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]


def ser_assert(path):
    raw = path.read_text(encoding="utf-8")
    obj = json.loads(raw)
    again = json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
    assert again == raw, "序列化器未逐字节复现原文件 ⇒ 改用文本插入"
    return obj, raw


EV = "docs/evidence/RF0001/R607-telemetry-inventory-and-discriminating-power.md"
cap = (
 "RF0004.0 **三面打点盘点 + 打点面判别力真机行使**（零产品源码改动；提交面 `src/` = 0）。"
 "① **盘点件** `eval/rover/r607/inventory_r607.py`（--write/--check）：3 面 × 15 键，逐键记发射点（file:line **由现盘 grep 派生，禁手打**）、独立发射点计数、全史现读数（`data/telemetry/host.jsonl`）、面/键缺口；缺口的判据 = `emit_count_sites == 0`（编排面 = `ActionLoopRunner.cs` 的 `Emit(` 计数）而非「我觉得没有」。实测缺口三条：**开放域识别出口** 无统一 `{标签|abstain, 依据}` 打点（RF0004.1 前置）· **生成类档** `TaskKindHint` 五档**无 Generation** ⇒ 结构性无档（RF0004.3 前置）· **多轮工具编排** `ActionLoopRunner.cs`/`ActionLoopGate.cs` 的 `Emit(` 计数 = 0 ⇒ 编排面**零专用打点**（RF0004.2 前置）。"
 "② **判别力真机行使**（单变量 = `AGENTFRAMEWORK_GATE_REPEAT_SKIP`：T = 未设/产品缺省（重复轮直 Skip）· C = 显式 `off`；同二进制 sha256 `fe1fb720…820dd3` = **从现盘 src 重建后与 R583 登记值逐位相同**（重建可复现、与 HEAD `f8128c6b` 同源）· 同夹具（`data/nlp/gate-shapes.txt` ← `eval/rover/r583/fixture-shapes-line1.txt` 逐字 sha `c98f8ab3…05a8d`，跑后复元为 absent 且回读断言）· 同轮序（复用 `turns-S0.txt`）· reps=3/臂 · 严格串行 · 6/6 rc=0）: **P1 治疗>0 PASS**（T×3 三键 [1,1,1]）**P2 对照==0 PASS**（C×3 三键 [0,0,0]）**P3 闸前置 PASS**（6/6 `local_turn_gate_config{turn_gate_enabled=真 ∧ role=skeptic}`）**P4 冻结恒前缀 PASS**（`F_env.prefix.chars`=15291 ∧ sha `f1280f71…4d4a`；命中率项如实记**未测**）**P5 有牙 PASS**（负控注入 + 非平凡互异）⇒ `verdict=PASS, rc=0`。"
 "③ **轴归因（`checks_posthoc`，不入 verdict）**: 两臂 turn2 输入指纹逐位相同（`msg_sha16=147757f75f39bd44`）而 `basis` 互斥（T `mechanical:repeat→local` / C `mechanical:nonack→remote`）⇒ 差异只来自门轴。"
 "④ **器具缺陷 v1→v2 披露式重注册**: v1（保留 `verdict-r607-v1-RED-boolexact.json`）判 `VOID(rc=3)`，根因 = 读数口径错（`turn_gate_enabled` 以 .NET `\"True\"` 落盘而判据按字面 `true` 比较 ⇒ 前置判 False ⇒ 连带 P1/P2/P5 失败）= **器具缺陷而非被测失效**；v2 只加读数归一 `_boolish()`（`\"True\"/\"true\"/1`⇒真，缺失/其它⇒None fail-closed），**阈值与判据集一字未改**、原始遥测与偏移未变 ⇒ 同一跑次复判（非重跑），并把两侧形态写入头部**影子自检**（assert 不过即 rc=2）防回归；v1 判定**未翻案**。"
 "⑤ 跳步（各一行原因，见证据文档 §6）: AOT 面（零产品改动 + publish 会抬高同窗 `PREV_SWING`）· C1 codex 臂（打点面盘点轮无质量对照项）· 恒前缀命中率 ≥97%（REPL 面不产该口径，无中继 dump）· 三面能力收益（三面未接线，只行使打点面，禁作能力宣称）。"
)

row = {
 "id": "r607.telemetry-inventory-and-discriminating-power",
 "level": "L3",
 "owner_round": "R607",
 "capability": cap,
 "evidence_cmd": ("python3 eval/rover/r607/inventory_r607.py --check && "
                  "bash eval/rover/r607/run_r607.sh && "
                  "python3 eval/rover/r607/judge_r607.py"),
 "evidence_path": EV,
 "negative_control": (
   "① **器具有牙（盘点件，`--check` 内同跑）**: 故意错一格行号 ⇒ 必判红；错键名 ⇒ 必判红；自检或负控不成立 ⇒ rc=2（器具缺陷）。"
   "② **打点面判别性负控（真机同二进制同夹具）**: 对照档 C = 同二进制 + `AGENTFRAMEWORK_GATE_REPEAT_SKIP=off` ⇒ 3/3 跑次三键**逐一 ==0**（机制不得无差别触发）；治疗档 T = 缺省 ⇒ 3/3 跑次三键各 ≥1 ⇒ 治疗>0 ∧ 对照==0 成对。"
   "③ **轴归因（同输入指纹）**: 两臂 turn2 `msg_sha16` 逐位相同而 `basis` 互斥 ⇒ 排除输入/环境差异。"
   "④ **判据器影子自检**: `_boolish` 必须同时吃 `.NET bool.ToString()`（`\"True\"`）与 JSON 布尔两形态，缺失/空 ⇒ None（fail-closed）；该断言正是 v1 读数缺陷（按字面 `true` 比较 ⇒ 假 VOID）的护栏。"
   "⑤ **禁令（防假绿）**: 判定只读 `verdict-r607.json` 的 `verdict` 键（rc 由 verdict 派生，不 grep 文本锚）；P4 的命中率半边如实记**未测**（不计作达标）；能力面**未行使**，不得由打点面 PASS 推出能力结论。"
 ),
 "covers": [
  "eval/rover/r607/inventory_r607.py",
  "eval/rover/r607/judge_r607.py",
  "eval/rover/r607/telemetry-inventory-r607.json",
  "eval/rover/r607/verdict-r607.json",
  "eval/rover/r607/prereg-r607.json",
  EV,
 ],
 "evidence_generated_with": {
  "evidence_kind": "artifact",
  "pin_status": "frozen",
  "pin_reason": "archived-per-round",
  "artifact_sha12": sha12(ROOT / "docs/evidence/RF0001/R607-telemetry-inventory-and-discriminating-power.md"),
  "instrument": "eval/rover/r607/judge_r607.py",
  "instrument_sha12": sha12(ROOT / "eval/rover/r607/judge_r607.py"),
  "binding": "audit-pin",
  "audited_by_round": "R607",
 },
 "covers_extra": {"inventory_instrument_sha12": sha12(ROOT / "eval/rover/r607/inventory_r607.py")},
}

obj, raw = ser_assert(REG)
rows = obj["rows"]
if any(r.get("id") == row["id"] for r in rows):
    print("[registry] id 已存在 ⇒ 幂等跳过")
else:
    rows.append(row)
    obj["updated_round"] = "R607"
    new = json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
    REG.write_text(new, encoding="utf-8")
    # 读回校验
    back = json.loads(REG.read_text(encoding="utf-8"))
    assert any(r.get("id") == row["id"] for r in back["rows"]), "读回缺行"
    assert len(back["rows"]) == len(rows), "读回行数不符"
    print("[registry] +1 行 (共 %d) updated_round=%s sha12=%s" % (len(back["rows"]), back["updated_round"], sha12(REG)))

krow = {
 "round": "R607",
 "ts": __import__("datetime").datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
 "kind": ("RF0004.0 盘点+打点轮（**零产品源码改动**）：三面打点盘点件（可机检、带负控）+ 打点面判别力真机行使"
          "（单变量 = AGENTFRAMEWORK_GATE_REPEAT_SKIP 缺省 vs off，T×3 / C×3，复用 r583 夹具与轮序、新 session 命名空间）"),
 "change": ("① 新增器具 `eval/rover/r607/inventory_r607.py`（3 面 × 15 键盘点 + 现盘核对 + 负控有牙）与 "
            "`eval/rover/r607/judge_r607.py`（打点面判据 P1–P5，判定只读 verdict 键）；② 新增轮工件 "
            "`eval/rover/r607/{dag,prereg,telemetry-inventory,run_r607.sh,offsets,arm-meta,pre-arm-state,gate-pre,"
            "arm-T-r*.log,arm-C-r*.log,verdict-r607.json,verdict-r607-v1-RED-boolexact.json}`；③ 证据文档 "
            "`docs/evidence/RF0001/R607-telemetry-inventory-and-discriminating-power.md`；④ 文献台账追加 "
            "`docs/research/lit-review-ledger.md` §9（1 条候选 + 反幻觉闸）；⑤ **提交面 `src/` = 0**（零产品改动）"),
 "readings": {
  "gate": {"preflight_rc": 0, "min_avail_mb": 285, "mem_before_MB": 2117, "mem_after_MB": 2231},
  "bin": {"sha256": "fe1fb720fb5eedb044014b1c27cd18352e851960102f93920bfb2f57e0820dd3",
          "same_as_R583_registered": True, "rebuilt_from_worktree_src": True},
  "P1_treatment_positive": {"local_turn_gate_Skip": [1, 1, 1],
                            "nlp_shape_shape1_repeat_local_skip": [1, 1, 1],
                            "local_gate_skip_reply_repeat_verbatim": [1, 1, 1]},
  "P2_control_zero": {"local_turn_gate_Skip": [0, 0, 0],
                      "nlp_shape_shape1": [0, 0, 0],
                      "local_gate_skip_reply": [0, 0, 0]},
  "P3_gate_precondition": {"rows": 6, "turn_gate_enabled": "True", "role": "skeptic", "ok": True},
  "P4_frozen_prefix": {"chars": 15291, "sha256": "f1280f71e6fc74c1f14f64adab5a54c6e06083acb18bbf51eb7fdbed30cc4d4a",
                       "check_rc": 0, "hit_rate_ge_097": "unreported(REPL 面无口径)"},
  "P5_teeth": {"negative_control": "inject-Skip->expect-red", "nontrivial": True},
  "arms_secs": {"T": [29, 15, 11], "C": [18, 14, 31]},
  "gaps": {"recognition_outlet": "no unified {label|abstain, basis} telemetry",
           "generation_tier": "TaskKindHint has no Generation kind",
           "orchestration": "ActionLoopRunner/ActionLoopGate Emit() count = 0"},
  "judge_v1": {"verdict": "VOID", "rc": 3, "root_cause": "reading: .NET 'True' vs literal 'true'"},
 },
 "baselines": ["F_env.gate.prev_swing_mb", "F_env.prefix.chars", "F_env.prefix.sha256",
               "F_merge.zero_regression.C_probe_repairs", "F_orch.cost.calls_sum"],
 "verdict": {"mechanism_face": "PASS(P1..P5)", "capability_face": "未行使(零产品改动)",
             "rc": 0, "verdict_file": "eval/rover/r607/verdict-r607.json"},
 "prereg": "eval/rover/r607/prereg-r607.json",
 "evidence": EV,
}
raw_k = KPI.read_text(encoding="utf-8").splitlines()
if any(json.loads(l).get("round") == "R607" for l in raw_k if l.strip()):
    print("[kpi] R607 已存在 ⇒ 幂等跳过")
else:
    with io.open(KPI, "a", encoding="utf-8") as f:
        f.write(json.dumps(krow, ensure_ascii=False) + "\n")
    lines = [l for l in KPI.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = all(json.loads(l) for l in lines)
    last = json.loads(lines[-1])
    print("[kpi] +1 行 (共 %d) 全文件逐行可解析=%s 末行 round=%s" % (len(lines), ok, last.get("round")))
