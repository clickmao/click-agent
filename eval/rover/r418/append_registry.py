#!/usr/bin/env python3
"""R418 登记: TaskPlan 节点 + verification-registry 行（两处均 roundtrip 校验后写入）。"""
import json
import pathlib

ROOT = pathlib.Path("/home/agentuser/AgentFramework")

# ---------- 1) TaskPlan ----------
TP = ROOT / "docs/plans/v715_dev_plan.taskplan.json"
raw = TP.read_text(encoding="utf-8")
d = json.loads(raw)
assert json.dumps(d, indent=1, ensure_ascii=False) == raw, "TaskPlan roundtrip 失败: 禁止改写"
node = {
    "Id": "dev-probe-process-kpi",
    "Text": ("R418 探针过程/成本维度 KPI: process_metrics 提取器(归属铁律=精确名/时间窗/歧义不猜/n-a不记0) + "
             "回复命名空间(seed) + digest 成本列; 真机 json_mini tokens/题=9151 整题全对 2/3 首次通过率 2/3"),
    "Intent": "code_generation",
    "Level": 1,
    "ParallelGroup": 1,
    "DocRef": "docs/plans/v0.39.0-r418-process-kpi.md",
    "Parameters": [],
    "Confidence": 1.0,
}
ids = [n.get("Id") for n in d["Nodes"]]
if node["Id"] in ids:
    d["Nodes"][ids.index(node["Id"])] = node
else:
    d["Nodes"].append(node)
TP.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
chk = json.loads(TP.read_text(encoding="utf-8"))
assert chk["Nodes"][-1]["Id"] == "dev-probe-process-kpi"
print("TaskPlan nodes=%d last=%s" % (len(chk["Nodes"]), chk["Nodes"][-1]["Id"]))

# ---------- 2) registry ----------
RG = ROOT / "docs/verification-registry.json"
raw = RG.read_text(encoding="utf-8")
r = json.loads(raw)
assert json.dumps(r, indent=2, ensure_ascii=False) + "\n" == raw, "registry roundtrip 失败: 禁止改写"
row = {
    "id": "r418.probe-process-kpi",
    "level": "L4",
    "evidence_cmd": ("bash eval/rover/r418/run1_process_kpi.sh && python3 eval/probe/process_metrics.py --selftest "
                     "&& python3 scripts/dev_return_digest.py"),
    "evidence_path": ("data/probe/process-metrics-r418.json; data/probe/probe-r418-agent.json; "
                      "data/probe/probe-r418-json-mut.json; data/probe/replies/agents20260916-p001.txt; "
                      "data/probe/replies/agents20260916-p002.txt; data/probe/replies/agents20260916-p003.txt"),
    "negative_control": (
        "① **负控成对（判别力）**: 同题集同 seed 的 `mutation:json_loose` 臂整题全对 **0/4**、用例级 0.7324，"
        "而 `oracle` 正控满分（54/54 用例级、2/2 整题全对）⇒ 判分器未失效。"
        "② **成本口径负控**: 负控臂不走 LLM ⇒ 过程指标记 **4×n/a**；若把缺字段记 0 会伪造「零成本」假象（`--selftest` 断言 n/a 排除分母: 1500.0 而非 1000.0）。"
        "③ **反张冠李戴负控（本轮新增，承重）**: 归档回复若不在该 run 的时间窗内 ⇒ **不得归属**，一律 n/a；"
        "窗内多候选 ⇒ 判歧义记 n/a，**绝不取第一个**（实测：修窗前 3 份旧 run 会读到同一批回复 = 静默张冠李戴，修窗后 ambiguous=0、na_sum=61 全部如实标 n/a）。"
        "④ `ts` 不可解析 ⇒ 不做窗匹配（不猜）。"),
    "capability": (
        "探针「过程/成本」维度 KPI（对**饱和题集仍有区分度**，直接对齐用户 KPI 口径：每题 tokens / 轮数 / 首次通过率）："
        "`eval/probe/process_metrics.py` 把**质量（判定器产物，外部真值）与成本（归档回复原文）拼成同一行**；"
        "`run_probe.py` 归档名带 seed 命名空间（`agents20260916-p001.txt`）+ 摘要记 `reply_ns` 供确定性归属。"
        "真机（AOT agenthost，`json_mini` n=3 seed=20260916）读数：整题全对 **2/3 = 0.6667**、用例级 **52/53 = 0.9811**、"
        "**tokens/题 = 9151.0**（prompt 侧）、tokens/满分题 9189.0、墙钟均 **77.7 s/题**、**turn≤1**（零多轮/零追问）、n/a 0、畸形 0。"
        "**口径边界（如实登记）**: 链不落 `completionTokens` ⇒ 只能报 **prompt 侧 + 墙钟**；探针为单轮，故「轮数」主要作异常检测。"
        "**等级依据 = 运行期行为 + 成对正负控 + 外部真值归属**，不是编译校验。"),
    "covers": [
        "eval/probe/process_metrics.py",
        "eval/probe/run_probe.py",
        "scripts/dev_return_digest.py",
        "eval/rover/r418/run1_process_kpi.sh",
        "eval/probe/README.md",
        "docs/plans/v0.39.0-r418-process-kpi.md",
    ],
    "owner_round": "R418",
}
ids = [x.get("id") for x in r["rows"]]
if row["id"] in ids:
    r["rows"][ids.index(row["id"])] = row
else:
    r["rows"].append(row)
r["updated_round"] = "R418"
RG.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
chk = json.loads(RG.read_text(encoding="utf-8"))
print("registry rows=%d updated=%s last=%s" % (len(chk["rows"]), chk["updated_round"], chk["rows"][-1]["id"]))
