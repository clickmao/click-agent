#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R468 台账收口: registry +2 行 / taskplan 节点 / 计划状态 / improvements 段。"""
import io, json, os

R = "docs/verification-registry.json"
T = "docs/plans/v715_dev_plan.taskplan.json"

# ---------- registry ----------
reg = json.load(io.open(R, encoding="utf-8"))
assert reg["updated_round"] == "R467", reg["updated_round"]
new_rows = [
    {
        "id": "r468.real-traffic-composition-external-validity",
        "level": "L2",
        "capability": "降幅外部效度机检：用产品判据（源码派生端口 + 产品差分校验）在【真实用户轮语料】(state.db 只读; 1,179 真实轮, 剔除 1,406 系统注入) 上复算机械可跳面, 与网格 p12 组成并列。读数: 网格 ack4+repeat2=50% 可跳; 真实 ack 0 + repeat 0 = 0.00% 可跳; 真实面 90.2% 轮必走远端主调用 ⇒ 「≥30% 降幅」只在具备可跳结构的语料上成立, 不外推真实分布",
        "evidence_cmd": "python3 eval/rover/r468/settle_r468.py",
        "evidence_path": "eval/rover/r468/verdict-r468.json",
        "negative_control": "① 注入负控: 向语料注入可跳行(\"好的，明白。\"/\"再讲一遍。\") ⇒ 指标必须变非 0, 实测 labels=[ack,repeat] skip_face=2 (eval/rover/r468/neg-control-r468.json) ⇒ 指标非恒 0; ② 存在性断言: 产品侧测试 RealTraffic_Rows_Have_Zero_Product_SkipFace 只要语料出现认可族/复述族即 FAIL",
        "covers": [
            "eval/rover/r468/settle_r468.py",
            "eval/rover/r468/real_traffic_classify.py",
            "eval/rover/r468/real-traffic.json",
            "eval/rover/r468/neg-control-r468.json",
            "eval/rover/r468/verdict-r468.json",
            "docs/reports/r468-real-traffic-composition.md",
        ],
        "owner_round": "R468",
    },
    {
        "id": "r468.gate-rules-port-diff",
        "level": "L2",
        "capability": "门判规则 Python 端口与产品判据的差分一致性: 端口从 src/agent.modelqueue/LocalGenerationPort.cs 正则派生(7 组规则: AckFamilyChars:304 / RepeatFamilyChars:356 / RepeatMarkers:359 / SubstantiveLengthThreshold:458 / 三信号表:461,469,477 + 源 sha256), 期望值取产品自身测试 InlineData(认可族 13 例 / 纯复述族 15 例); 423 行语料(真实轮+网格 p12+InlineData)逐条标签 ≡ 产品 MechanicalPass|IsPureRepeat|MechanicalAck 组合, 不一致 0; 规则改动即把该测试判红 ⇒ 强制重生语料(证据↔器具版本绑定)",
        "evidence_cmd": "$HOME/.dotnet/dotnet test src/agent.tests/agentframework.tests.csproj -c Release --filter FullyQualifiedName~GateRulesPortDiffTests",
        "evidence_path": "eval/rover/r468/difftest_r468.log",
        "negative_control": "① 端口禁手抄: gate_rules.py --selftest 的期望值取自产品 InlineData(28 例), rc!=0 即失败; ② 语料四族覆盖断言 Corpus_Covers_Archive_And_Repeat_And_Pass_Families(防单族恒真); ③ 差分测试三例均为等值断言, 非同义恒真式",
        "covers": [
            "src/agent.tests/GateRulesPortDiffTests.cs",
            "eval/rover/r468/gate_rules.py",
            "eval/rover/r468/real-traffic-corpus.jsonl",
            "eval/rover/r468/difftest_r468.log",
        ],
        "owner_round": "R468",
    },
]
have = {r["id"] for r in reg["rows"]}
for r in new_rows:
    assert r["id"] not in have, r["id"]
reg["rows"].extend(new_rows)
reg["updated_round"] = "R468"
io.open(R, "w", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False, indent=1) + "\n")
print("registry rows", len(reg["rows"]), "updated_round", reg["updated_round"])

# ---------- taskplan ----------
tp = json.load(io.open(T, encoding="utf-8"))
by_id = {n["Id"]: n for n in tp["Nodes"]}
for nid in ("dev-r462-recall-reality-gate", "dev-r465-repeat-skip"):
    if by_id[nid]["State"] != "done":
        by_id[nid]["State"] = "done"
        print("state->done", nid)
add = [
    ("dev-r466-repeat-priority", "复述回放 vs 承接反问优先级（修 R465 C3 FAIL）+ 结算类口径单源",
     "R466", "docs/plans/v0.83.1-r466-repeat-priority.md", "docs/reports/r466-repeat-priority.md",
     "R465 遗留 C3 FAIL: 纯复述轮 skip 层已逐字回放, 但 R458 承接反问收口面无条件覆盖 ⇒ 用户可见答复 46 字反问。修法: ContinuationBrief.SettleRepeatVerbatim 口径单源 + ShouldApplyFallback(settleKind, reply, facts) + 主链写 _localSettleKind(打点/收口同源) + 逐轮清零; 开关 AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY(默认 on, 置 0 = R465 行为 ⇒ 同二进制负控)。读数: Arole 13/32,097; R 6/14,529(−54.73%); NC(off) 6/14,531 且 t6 复现 46 字反问; R2 6/14,531 逐位同; 全量 1411/1411。"),
    ("dev-r467-denominator-pinning", "分母固化：远端调用分解台账 + 臂可比性闸 + 同二进制判官标志复现裁决",
     "R467", "docs/plans/v0.84.0-r467-denominator-pinning.md", "docs/reports/r467-denominator-pinned.md",
     "R466 遗留「Arole 分母跨轮漂移(21/33,323 ↔ 13/32,097)」无字段无机检。定因: 产品里真发远端判官的唯一路径 = RelationJudgeEnabled != true ⇒ 臂定义漂移。四臂串行真跑: Arole 13/32,097(rj on) vs Aroff 21/33,323(rj off) 差 8 调用/1,226 tok 与桩侧逐位吻合; R 6/14,529(−54.73%); R2 6/14,531。新器具 settle_r467.py(calls_class/judge_route) + denominator_gate.py(G1–G5, 自检 3/3), registry +2 行(L2/L4)。"),
    ("dev-r468-real-traffic-composition", "真实流量组成 vs 网格组成：门判降幅的外部效度机检",
     "R468", "docs/plans/v0.85.0-r468-real-traffic-composition.md", "docs/reports/r468-real-traffic-composition.md",
     "把「降幅外部效度」变机检判据: 源码派生规则端口(gate_rules.py, 双源自检 13+15 例) + 产品差分测试 GateRulesPortDiffTests(423 行 0 不一致) + state.db 真实用户轮组成复算。读数: 网格 ack4+repeat2 = 50% 可跳(降幅 −54.7%/−56.4%); 真实 1,179 轮 ack 0 + repeat 0 = 0.00% 可跳, driver 116(9.8%)/pass 890/other 173 ⇒ 90.2% 轮必走远端; 注入负控 skip_face=2; 全量单测 ×3 连续 1414/1414。"),
]
for nid, title, rnd, doc, ev, summ in add:
    if nid in by_id:
        continue
    tp["Nodes"].append({"Id": nid, "Title": title, "State": "done", "Round": rnd,
                        "DocRef": doc, "Evidence": ev, "Summary": summ})
    print("node+", nid)
io.open(T, "w", encoding="utf-8").write(json.dumps(tp, ensure_ascii=False, indent=2) + "\n")
print("nodes", len(tp["Nodes"]))

# ---------- 计划状态 ----------
def set_state(path, line, anchor_first=True):
    s = io.open(path, encoding="utf-8").read()
    if "状态:" in s:
        print("state-exists", path)
        return
    ls = s.split("\n")
    ls.insert(1, line)
    io.open(path, "w", encoding="utf-8").write("\n".join(ls))
    print("state+", path, line)

set_state("docs/plans/v0.83.1-r466-repeat-priority.md", "- 状态: 已收口（R466）")
set_state("docs/plans/v0.84.0-r467-denominator-pinning.md", "- 状态: 已收口（R467）")

# ---------- improvements ----------
imp = "docs/improvements.md"
sec = u"""

## R468（2026-09-16）真实流量组成 vs 网格组成：门判降幅的**外部效度**机检

- **因**: R465/R466 的 −56.40%/−54.73% 分子分母同取一张 12 轮网格（4 认可 + 2 复述 + 6 其他 = **50% 可跳面**）；该组成系为族覆盖而设计，从未机检是否代表真实分布。R449/R452 的「真实 ack = 0/1542」是**旧规则**结论，未在新规则（Ack 主闸 + 纯复述直跳 + MechanicalPass 优先）上复验。
- **法**: `eval/rover/r468/gate_rules.py` 从 `LocalGenerationPort.cs` **正则派生**规则（`:304`/`:356`/`:359`/`:458`/`:461`/`:469`/`:477`，记源 sha256），期望值取产品自身 `InlineData`（认可族 13 / 纯复述族 15）⇒ `--selftest` PASS；新测试 `GateRulesPortDiffTests`（3 例）在 **423 行**语料（真实轮 + 网格 p12 + InlineData）上断言端口标签 ≡ 产品三判组合。
- **读数（机检）**: 真实语料 = `state.db` `role='user'` 2,585 行 − 1,406 系统注入 = **1,179 真实轮**；`pass 890 (75.5%) / other 173 (14.7%) / driver 116 (9.8%) / ack 0 / repeat 0` ⇒ **机械可跳面 0.00%**，需远端主调用 **90.2%**。对照网格 **50.0%** 可跳。
- **结论**: 「≥30% 降幅」绑定**具备可跳结构的语料**，在唯一可得的外部真值通道上出现率 0 ⇒ 不外推真实用户面；真实分布 90.2% 轮必走远端 ⇒ 撬动真实 KPI 的杠杆是**单次调用 token 量**（前缀按需注入/缓存命中），列为 R469 首选。
- **负控**: 注入「好的，明白。」/「再讲一遍。」⇒ `skip_face=2`（指标非恒 0）；产品侧存在性断言「真实行可跳面 == 0」存在即 FAIL。
- **形式校验**: 全量单测 **×3 顺序隔离连续 1414/1414**（`Failed 0` ×3，执行数一致）；定向差分 3/3；零产品行为改动、零 llama-server、零远端、未 push。
- **边界**: 判据落盘晚于探索性首跑（C1–C6 为复现跑，首跑读数单列 posthoc）；端口 ≡ 产品仅覆盖 423 行；「系统注入剔除」前缀规则本身未机检；真实语料 ≠ 产品最终用户分布（待确认）。
"""
io.open(imp, "a", encoding="utf-8").write(sec)
print("improvements bytes", os.path.getsize(imp))
