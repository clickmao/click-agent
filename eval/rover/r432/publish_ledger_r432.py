#!/usr/bin/env python3
"""R432 台账发布器（幂等；数值全部取自机检 verdict JSON，不手抄）。臂 1 登记 + 臂 2 裁决。"""
import json, pathlib, subprocess, sys

R = pathlib.Path("/home/agentuser/AgentFramework")
D = R / "eval/rover/r432"
PLAN = R / "docs/plans/v0.53.0-r432-gate-discrimination.md"


def load(name):
    p = D / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


V1 = load("verdict-C-r432dp1.json")
vp = sorted(D.glob("verdict-C-r432dp2*.json"))
if not vp:
    sys.exit("臂 2 verdict 缺失 —— 先跑臂 2")
V = json.loads(vp[-1].read_text(encoding="utf-8"))
verd = V.get("verdict", "?")
ts = subprocess.run(["date", "+%Y-%m-%dT%H:%M:%S%z"], capture_output=True, text=True).stdout.strip()

q = lambda v: {k: v[k] for k in ("verdict", "gate_records_all", "gate_r1", "gate_mechanical", "gated_positions",
                                 "ungated_positions", "r1_decisions", "raw_len_seq", "pattern", "cache_n_seq",
                                 "family_decisions", "C2_details", "alignment_ok", "attribution_ok", "isolation_hits",
                                 "remote_calls", "total_tokens_est") if k in v}
crit = {k: V[k] for k in V if k.startswith("C") and isinstance(V[k], (bool, type(None)))}

# --- 1) kpi.jsonl（并发追加 ⇒ 按 round 字段定位, 禁取末行）---
kf = R / "eval/capability/kpi.jsonl"
rows = [json.loads(l) for l in kf.read_text(encoding="utf-8").splitlines() if l.strip()]
if any(r.get("round") == "R432" for r in rows):
    print("[kpi] R432 行已存在, 跳过")
else:
    readings = {
        "verdict": verd, "verdict_rule": V["verdict_rule"], "criteria": crit, "arm2": q(V), "arm1": q(V1) if V1 else None,
        "binary_sha256": V["binary_sha256"], "binary": V["binary"],
        "instrument": "门遥测按 telemetry ts 落入轮时间窗对齐（弃 secs>=5 位置启发式）+ 桩侧逐请求时间戳归因",
    }
    row = {
        "kind": "task-step", "branch": "tasks", "round": "R432", "step": "turn-gate-discrimination-pair", "ts": ts,
        "plan_item": "R429 诚实边界 ④（判别力负控落空 ⇒「钉死后门仍能 Pass/Skip 正确」无证据）⇒ 判别力 + 确定性成对判据补证",
        "modification": "新增器具 eval/rover/r432/**（不改产品源码；工作树含对侧在途改动，本臂用 627dd23 提交态 AOT /tmp/pub_r430b/agenthost）；臂 1 露出「可达位偏移」⇒ 读数前预注册臂 2 的偏移无关网格（每族 4 连排 + 负控置可达位）",
        "readings": json.dumps(readings, ensure_ascii=False),
        "evidence": "eval/rover/r432/README-evidence.md",
        "level": "L3", "owner_round": "R432",
        "namespace_collision": "R431 撞号: 对侧（未提交工作树）先占 R431 与 v0.52.0（主题=角色种子挂载形状机检）⇒ 本侧让号至 R432 / v0.53.0；对侧产物未改未 add（登记见 docs/plans/v0.53.0-r432-gate-discrimination.md §0）",
        "honest_boundary": json.dumps([
            "被测二进制 = 提交态 627dd23 的 AOT；工作树含对侧 R431 在途改动，未参与本臂构建",
            "两臂均在安静窗口闸后点火，但未证明整段测量期间与对侧零重叠（判据不含墙钟项）",
            "遥测 raw 截断 120 字符 ⇒ 前缀 sha 仅覆盖前 120（raw_len 170 ⇒ 尾部未逐字节覆盖）",
            "臂 1 判决 FAIL 属**族位错配**（可达位偏移），非仪器失效；其读数按 checks_posthoc 单列",
            "「可达位偏移」未被单独隔离验证；单机单次读数",
        ], ensure_ascii=False),
    }
    with kf.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    rows2 = [json.loads(l) for l in kf.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("[kpi] 追加成功; 行数", len(rows), "->", len(rows2), "| 本侧行索引",
          [i for i, r in enumerate(rows2) if r.get("round") == "R432"])

# --- 2) registry（L3: 必填 negative_control + covers[]）---
rf = R / "docs/verification-registry.json"
reg = json.loads(rf.read_text(encoding="utf-8"))
if any(r.get("owner_round") == "R432" for r in reg["rows"]):
    print("[registry] R432 行已存在, 跳过")
else:
    reg["rows"].append({
        "id": "r432.turn-gate-discrimination-pair", "owner_round": "R432", "level": "L3",
        "capability": "门判**判别力与确定性成对**（残余带内，臂 2 裁决）: ① 判别力 = 机械前置门（零 token）与 r1 判官在同一网格产出不同判决（机械 Pass vs r1 Skip 并存；r1 侧若 Pass/Skip 混存则内层判别力亦成立）; ② 确定性 = 同文重复（ack/cont 各≥2 条）判定与 raw 恒定; ③ 归因 = 门判定按 telemetry ts 落入唯一轮时间窗（顺序分区）+ 桩侧逐请求时间戳交叉校验（Pass ⇔ 窗内远端调用≥1）。臂 2 读数: "
                      + json.dumps(q(V), ensure_ascii=False),
        "evidence_cmd": "AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430b/agenthost R432_NS=-r432dp2 bash eval/rover/r432/run_arm.sh C r432dp2 47930 47931 /home/agentuser/AgentFramework/skeptic.rbin",
        "evidence_path": "eval/rover/r432/README-evidence.md",
        "negative_control": json.dumps([
            "① 机械负控位（`现在的情况如何？`，网格 v2 pos19）: 必落 mechanical 分支且 r1 侧不得出现该位（若落 r1 ⇒ C5 假 ⇒ FAIL）",
            "② 旁路负控: 任何轮回复以 [隔离任务] 开头 ⇒ 该轮作废（C4 假 ⇒ FAIL），防「根本没进门」被当读数",
            "③ 未测到不判通过: 未进门位记 ungated，明确不计入 C1/C2 分子（臂 1 有 9 轮未进门）",
            "④ 归因负控: Pass 必须伴随该轮窗口内远端桩调用 ≥1、Skip 必须为 0（否则 C3 假）",
            "⑤ 族位错配负控（臂 1 实发）: 预注册族落在被 ask 消费位 ⇒ C2/C5 直接判 FAIL，未事后改判据（如实登记 + §3.1 预注册校正臂）",
            "⑥ 对照: R430 fix 臂同文 4 次 raw 同一（127/127/127/127）为该能力的先验正控",
        ], ensure_ascii=False),
        "covers": ["eval/rover/r432/settle_r432.py", "eval/rover/r432/run_arm.sh", "eval/rover/r432/grid/task-r432dp2.json",
                   "src/agent.modelqueue/LocalGenerationPort.cs", "src/agent/IndustrialAgentV2.cs"],
    })
    reg["updated_round"] = "R432"
    rf.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    assert json.dumps(json.loads(rf.read_text(encoding="utf-8")), indent=2, ensure_ascii=False) == rf.read_text(encoding="utf-8")
    print("[registry] 追加成功; rows", len(reg["rows"]), "| roundtrip 逐字节一致 | updated_round R432")

# --- 3) 计划文档状态行 ---
if "状态: 进行中" in PLAN.read_text(encoding="utf-8"):
    s2 = PLAN.read_text(encoding="utf-8").replace("状态: 进行中", f"状态: 已完成 ({verd}; 证据 eval/rover/r432/README-evidence.md)", 1)
    PLAN.write_text(s2, encoding="utf-8")
    print("[plan] 状态行 ->", [l for l in s2.splitlines() if l.startswith("状态:")][0])

# --- 4) improvements.md 顶部插节点（最新在顶; 共享文档 ⇒ 读-改-写 + 回读）---
imf = R / "docs/improvements.md"
txt = imf.read_text(encoding="utf-8")
if "## R432 \u00b7 " not in txt:
    node = (
        "## R432 \u00b7 \u95e8\u5224\u5224\u522b\u529b\u4e0e\u786e\u5b9a\u6027\u6210\u5bf9\uff08\u6b8b\u4f59\u5e26\u5185\uff09\n\n"
        "**\u4e3b\u9898**\uff1a\u8865 R429 \u8bda\u5b9e\u8fb9\u754c \u2463\uff08\u5224\u522b\u529b\u8d1f\u63a7\u843d\u7a7a\uff09\u2014\u2014\u9489\u6b7b\u5224\u5b9a\u8def\u5f84\u540e\uff0c\u95e8**\u8fd8\u80fd\u4e0d\u80fd\u533a\u5206**\u300c\u65b0\u8bc9\u6c42 / \u65e0\u65b0\u8bc9\u6c42\u300d\uff0c\u4e14\u540c\u6587\u91cd\u590d\u9010\u4f4d\u6052\u5b9a\u3002\n\n"
        "**\u5224\u51b3**\uff1a\u81c2 2 = **" + verd + "**\uff08\u89c4\u5219\uff1a" + V["verdict_rule"] + "\uff09\uff1b\u81c2 1 = " + (V1 or {}).get("verdict", "n/a") + "\uff08\u65cf\u4f4d\u9519\u914d\uff0c\u975e\u4eea\u5668\u5931\u6548\uff09\u3002\n\n"
        "**\u81c2 2 \u673a\u68c0\u8bfb\u6570**\uff1a\u95e8\u8bb0\u5f55 " + str(V["gate_records_all"]) + "\uff08r1 " + str(V["gate_r1"]) + " / \u673a\u68b0 " + str(V["gate_mechanical"]) +
        "\uff09\uff1br1 \u5224\u51b3 " + json.dumps(V["r1_decisions"], ensure_ascii=False) + "\uff1braw_len " + json.dumps(V["raw_len_seq"]) +
        "\uff1b\u8fdb\u95e8\u4f4d " + json.dumps(V["gated_positions"]) + "\uff1b\u5f52\u56e0 alignment=" + str(V["alignment_ok"]) + " attribution=" + str(V["attribution_ok"]) +
        "\uff1b\u8fdc\u7aef\u8c03\u7528 " + str(V["remote_calls"]) + " / token_est " + str(V["total_tokens_est"]) + "\n\n"
        "**\u57fa\u7ebf**\uff1aR430 \u540c\u6587 4 \u6b21\u95e8\u5224 raw \u540c\u4e00\uff08127/127/127/127\uff09\u4e14\u5224\u51b3 Skip\u00d74\uff08\u786e\u5b9a\u6027\u5df2\u8bc1\uff09\u3002\n\n"
        "**\u4eea\u5668**\uff1a\u65b0\u589e\u95e8\u5224\u5b9a**\u65f6\u95f4\u7a97\u5bf9\u9f50**\uff08telemetry ts \u843d\u5165\u8f6e\u65f6\u95f4\u7a97\uff0c\u5e9f\u5f03 secs>=5 \u4f4d\u7f6e\u542f\u53d1\u5f0f\uff09\uff1b\u5b9e\u6d4b\u53ef\u8fbe\u4f4d\u504f\u79fb = \u5947\u6570\u4f4d\uff08seed \u8f6e\u95ee\u8be2\u88ab\u4e0b\u4e00\u8f6e ask \u6d88\u8d39\uff09\u3002\n\n"
        "**\u649e\u53f7\u767b\u8bb0**\uff1aR431 \u88ab\u5bf9\u4fa7\u5e76\u53d1\u4f5c\u4e1a\u5148\u5360\uff08\u672a\u63d0\u4ea4\u5de5\u4f5c\u6811\uff09\u21d2 \u672c\u4fa7\u8ba9\u53f7\u81f3 R432 / v0.53.0\u3002\n\n"
        "**\u8bc1\u636e**\uff1a`eval/rover/r432/README-evidence.md`\n\n---\n\n"
    )
    txt2 = txt.replace("## R430 \u00b7 ", node + "## R430 \u00b7 ", 1)
    assert txt2 != txt
    imf.write_text(txt2, encoding="utf-8")
    back = imf.read_text(encoding="utf-8")
    print("[improvements] 插入成功; 行数", back.count(chr(10)) + 1)

# --- 5) digest 重建 ---
r = subprocess.run(["python3", "scripts/dev_return_digest.py"], cwd=str(R), capture_output=True, text=True)
print("[digest]", (r.stdout or "").strip()[-140:], "| rc", r.returncode)
print("[done] 臂2 verdict =", verd)
