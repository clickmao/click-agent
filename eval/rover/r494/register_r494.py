#!/usr/bin/env python3
# R494 登记: 向 docs/verification-registry.json 追加 3 行 (本轮归属), updated_round=R494。
# 读改写在一次进程内完成; 追加后回读校验 (行数 +3, id 唯一)。pin 目标 = 器具 (analyze/audit), 与 r490/r491 同惯例。
import json, hashlib, os, sys

ROOT = "/home/agentuser/AgentFramework"
REG = os.path.join(ROOT, "docs/verification-registry.json")
D = "eval/rover/r494"

def sha12(rel):
    p = os.path.join(ROOT, rel)
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]

inst_analyze = sha12(f"{D}/analyze_r494.py")
inst_audit = sha12(f"{D}/audit_capability_face_r494.py")
art_kpi = sha12(f"{D}/kpi-r494.json")
art_audit = sha12(f"{D}/audit-capability-face.json")

rows = [
 {
  "id": "r494.isolated-channel-tool-decl",
  "level": "L2",
  "owner_round": "R494",
  "capability": "**声明面通道轴**: 隔离通道 (微步骤隔离问询 / 一次性隔离子任务) 结构上无工作区 ⇒ 恒不下发工作区工具。结构字段 IsolatedChannel 贯穿 Prompt → QueuePrompt → ActionLoop.Clone → 判据 (环内第 2 次起不丢判据); 新 env AGENTFRAMEWORK_TOOL_DECL_CHANNEL 默认关 ⇒ 生产行为不变; 打点 tool_decl_gate 新增 isolated_channel / channel_gate / 原因短名 isolated_channel_drop。9 条门禁 (含结构锁: SystemPrompt 赋值行命中隔离声明 ⇒ 同文件必须置位, 产品源反向计数=2) + AOT 0 IL 警告。",
  "evidence_cmd": f"env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 {D}/analyze_r494.py",
  "evidence_path": f"{D}/kpi-r494.json",
  "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
    "artifact_sha12": art_kpi, "instrument": f"{D}/analyze_r494.py", "instrument_sha12": inst_analyze,
    "binding": "audit-pin", "audited_by_round": "R495"},
  "covers": ["src/agent.modelqueue/ToolDeclGate.cs", "src/agent/modelqueue/ModelQueueAdapter.cs",
             "src/agent.modelqueue/ModelQueueRouter.cs", "src/agent.modelqueue/ActionLoop.cs",
             "src/agent/templates/IPromptBuilder.cs", "src/agent/IndustrialAgentV2.cs",
             "src/agent/subagent/IsolatedTaskRunner.cs", "src/agent.tests/R494IsolatedChannelToolDeclTests.cs",
             f"{D}/assert_face_r494.py"],
  "negative_control": "通道轴**关**的臂复现泄漏 (B/T0 隔离调用带工具=1, assert-face-B.json / assert-face-T0.json); 通道轴关时判据与 R490 逐位同 (单测 byte-identity); IL 负控在 V0 形态闸被拒 (prov-*.json)。",
 },
 {
  "id": "r494.isolated-channel-realmachine-ladder",
  "level": "L2",
  "owner_round": "R494",
  "capability": "**同窗三臂真机阶梯** B/T0/T1 (同网格逐字节同 R493、同上游 api.deepseek.com deepseek-flash、三臂 host_sha 一致) + 逐臂实发面 fail-closed 收口 (assert_face)。验收读数: B→T1 远端调用 18→7、total_tokens 86,474→29,273 (**−66.15%**, 达标 ≥30%); 隔离通道带工具 1→0。",
  "evidence_cmd": f"python3 {D}/assert_face_r494.py --arm <B|T0|T1> --dir {D} --channel <off|on>; python3 {D}/analyze_r494.py",
  "evidence_path": f"{D}/kpi-r494.json",
  "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
    "artifact_sha12": sha12(f"{D}/kpi-r494.json"), "instrument": f"{D}/analyze_r494.py", "instrument_sha12": inst_analyze,
    "binding": "audit-pin", "audited_by_round": "R495"},
  "covers": [f"{D}/prereg_r494.json", f"{D}/run_arm_real_r494.sh", f"{D}/grid/task-p12-adv.json",
             f"{D}/kpi-r494.json", f"{D}/tables-r494.md", f"{D}/assert-face-T1.json", f"{D}/adv-T1.json",
             f"{D}/evidence-r494.json"],
  "negative_control": "**预注册 P2 被证伪**: T0→T1 的 token 24,728→29,273 (**+18.4% 上升**) ⇒ 本轮**不**宣称通道轴的 token 增益 (宣称收窄为结构面闭合 + 未引入新红), 单列于报告 §三/§五。",
 },
 {
  "id": "r494.capability-face-readonly-audit",
  "level": "L1",
  "owner_round": "R494",
  "capability": "能力自检面**只读**复核 (产品不双写): A1 正控面每条 instrument 必须 pass / A2 各负控面必须全红 / A3 面文件内声明的 `manifest_sha12` 必须等于 instruments.json 当前字节指纹。现况 34 断言 / 5 红 (1 项指纹漂移 + 4 项正控 rc=2)。",
  "evidence_cmd": f"python3 {D}/audit_capability_face_r494.py",
  "evidence_path": f"{D}/audit-capability-face.json",
  "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
    "artifact_sha12": art_audit, "instrument": f"{D}/audit_capability_face_r494.py", "instrument_sha12": inst_audit,
    "binding": "audit-pin", "audited_by_round": "R495"},
  "covers": ["eval/capability/instruments.json", "eval/capability/instruments-check.json",
             "eval/capability/instruments-check-scoped.json", "eval/capability/instruments-check-drift.json",
             f"{D}/audit_capability_face_r494.py", f"{D}/audit-capability-face.json"],
  "negative_control": "4 项正控在面文件里记 rc=2, 但**外写** (--out /tmp) 复跑 rc=0 (15/15 检查) ⇒ 差异归因**未闭合**; 该面属对侧会话线, 本轮只记读数不代跑 (写入即双写)。",
 },
]

doc = json.load(open(REG, encoding="utf-8"))
before = len(doc["rows"])
have = {r["id"] for r in doc["rows"]}
add = [r for r in rows if r["id"] not in have]
upd = 0
for r in rows:
    for i, old in enumerate(doc["rows"]):
        if old["id"] == r["id"]:
            doc["rows"][i] = r; upd += 1; break
doc["rows"].extend(add)
doc["updated_round"] = "R494"
json.dump(doc, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

chk = json.load(open(REG, encoding="utf-8"))
ids = [r["id"] for r in chk["rows"]]
print(f"[register] rows {before} -> {len(chk['rows'])} (新增 {len(add)}, 更新 {upd}); updated_round={chk['updated_round']}")
print(f"[register] 唯一性: {len(ids) == len(set(ids))}; 本轮 id 在位: {all(r['id'] in ids for r in add)}")
