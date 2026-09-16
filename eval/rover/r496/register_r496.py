#!/usr/bin/env python3
# R496 登记: 把本轮证据写入 docs/verification-registry.json (写入后立刻跑形式门禁)。
# 用法: python3 eval/rover/r496/register_r496.py [--dry]
import hashlib, json, os, sys

ROOT = "/home/agentuser/AgentFramework"
REG = os.path.join(ROOT, "docs/verification-registry.json")
D = "eval/rover/r496"


def sha12(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def row(id_, level, cap, cmd, path, instrument, covers, neg, audited="R496"):
    return {
        "id": id_, "level": level, "owner_round": "R496", "capability": cap,
        "evidence_cmd": cmd, "evidence_path": path,
        "evidence_generated_with": {
            "evidence_kind": "artifact", "pin_status": "frozen",
            "pin_reason": "archived-per-round", "artifact_sha12": sha12(path),
            "instrument": instrument, "instrument_sha12": sha12(instrument),
            "binding": "audit-pin", "audited_by_round": audited},
        "covers": covers, "negative_control": neg,
    }


def main(dry=False):
    reg = json.load(open(REG, encoding="utf-8"))
    ids = {r["id"] for r in reg["rows"]}

    r1 = row("r496.ledger-truth-nonrecomputable", "L2",
             "**核对码真值不可复算 (R495 反向诊断的第一半收口)**: 真值 = HMAC-SHA256(进程级 CSPRNG 密钥 32B, "
             "`session|规范行`) 前 12 位, 密钥**只存内存** (源码静态检查: 无 env 通道 / 无文件写 / 不打点); "
             "落盘 (台账 JSONL) 与打点只留单向指纹 `code8 = sha256(码)[:8]` + `key_id = sha256(密钥)[:8]` ⇒ "
             "公开配方 (R495 口径 `sha256(session|canon)[:12]`) 复算 **0 命中** 实发真值。"
             "**宣称已收窄 (负样本诚实)**: 真值仍有**盘上通道** —— `src/agent/IndustrialAgentV2.cs:1728` 的 "
             "`local_decision_ledger` 遥测点仍写 raw `code`, 而遥测落在**臂可读的工作区内** ⇒ 关轴臂用 "
             "`run_command` 读自己的遥测即得真值 (判据 J5 红: t15 回复给出本臂真实码 LCM-fba5543dc9ee, 指纹命中) "
             "⇒ **必错族在 R496 仍不成立**; 收口须枚举全部 Emit 点 (留 R497)。",
             "python3 %s/nonrecompute_check_r496.py --dir %s --arms B,T0,T1 --out %s/nonrecompute-r496.json; "
             "python3 %s/assert_face_r496.py --arm B --dir %s --channel off --mount off" % (D, D, D, D, D),
             "%s/assert-face-B.json" % D, "%s/nonrecompute_check_r496.py" % D,
             ["%s/prereg_r496.json" % D, "%s/ledger-B.jsonl" % D, "%s/flags-B.json" % D,
              "%s/nonrecompute-r496.json" % D, "src/agent.modelqueue/LocalDecisionLedger.cs",
              "src/agent.modelqueue/ModelQueueRouter.cs", "src/agent/IndustrialAgentV2.cs",
              "src/agent.tests/R496NonRecomputableTests.cs"],
             "① 反例复算: `nonrecompute_check_r496.py --selftest` 正控 (台账含 raw code) 必红 / 负控 (仅指纹) 必绿 / "
             "旧配方对同 canon 复算 ≠ 真值 (三条读数见 selftest 输出)。② 判据 J5 在本轮**红**: 关轴臂从工作区遥测 "
             "读出真值 ⇒ 直接证明「只封台账面」不够 (这正是登记行宣称收窄的依据, 不是遮蔽)。")

    r2 = row("r496.ledger-code-restate-authorized", "L2",
             "**挂载文案的授权面 (R495 反向诊断的第二半)**: R495 的挂载尾部口径写「用户无法从别处得到」⇒ 模型读成"
             "金丝雀标记, 被问核对码时**防御性拒答** (治疗向判据 J2/J3 全红)。R496 改为**显式授权复述**"
             " (「该码 = 链自持摘要, 非密钥/非保密标记; 用户问起就按原样直接复述, 不要拒答」), 并以**实发字节**锚机检: "
             "挂载轴上每个会话请求的挂载块必须含 `原样直接复述` 且全局不含旧措辞 `用户无法从别处得到`。",
             "python3 %s/judge_code_r496.py --arm T1 --mount on --turns %s/turns-T1.jsonl --calls %s/calls-T1.jsonl "
             "--tel %s/tel-T1/host.jsonl --ledger %s/ledger-T1.jsonl --grid %s/grid/task-p15-code.json" % (D, D, D, D, D, D),
             "%s/adv-code-T1.json" % D, "%s/judge_code_r496.py" % D,
             ["%s/prereg_r496.json" % D, "%s/calls-T1.jsonl" % D, "%s/turns-T1.jsonl" % D,
              "%s/grid/task-p15-code.json" % D],
             "对照臂 (mount=off) 同一问题上的行为必须**不能**给出真值 (结构上不可得, 见 J5 的诚实边界); "
             "文案锚同时做**负向断言** (旧金丝雀措辞出现即为红) ⇒ 「授权」不是靠判据宽松换来的。")

    r3 = row("r496.tool-face-out-of-root-and-clause-redaction", "L2",
             "**工具面越界收口 (R495 半开通道)**: R495 实证 `run_command` 无边界 —— 越界路径被判「已拒绝」但"
             "**正文照样回显** (12 条请求把链源码行/台账路径/挂载块常量读进上下文)。R496 两处收口: "
             "(a) `WorkspaceActionPort.RunCommandAsync` 结构拒执行: 命令文本里出现工作区外路径 "
             "(绝对路径越界 / `..` 逃逸 / `~`) ⇒ rc=126 **不执行**、不回显任何命令输出 (白名单仅 `/dev/null`, "
             "惯用法 `2>/dev/null` 仍可跑); (b) `RecallRealityGate` 越界子句**正文隐去** (`[越界路径已隐去] <token>` + 标签), "
             "其余分支逐字节不变 (标签位置/分隔符顺序保持)。",
             "python3 %s/assert_face_r496.py --arm B --dir %s --channel off --mount off; "
             "env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test "
             "src/agent.tests/agentframework.tests.csproj -c Release --no-build --filter "
             "\"FullyQualifiedName~R496NonRecomputable\"" % (D, D),
             "%s/assert-face-B.json" % D, "%s/assert_face_r496.py" % D,
             ["src/agent/action/WorkspaceActionPort.cs", "src/agent.core/core/RecallRealityGate.cs",
              "src/agent.tests/R496NonRecomputableTests.cs", "%s/calls-B.jsonl" % D],
             "**诚实边界 (未测到≠通过)**: 实跑三臂的 tool 消息里块头/链源码路径命中 0 (R495 同项 12 条请求命中), "
             "但**拒绝见证 = 0** ⇒ 本轮模型没试越界读 ⇒ 收口在真机上**未被触发**, 增益/代价不可单列。"
             "判定路径的可红性由单测正控锁死 (`FindOutOfRootToken` 越界用例 + `cat /etc/hostname` 必须 rc=126 且输出不含宿主机名)。")

    r4 = row("r496.ledger-telemetry-per-call-merge", "L2",
             "**台账面并入逐调用打点 (候选⑦)**: R495 的台账字段只挂在 `tool_decl_gate` 点上 ⇒ 远端调用轴看不见"
             "「这一调用挂了几条 / 挂了多少字符 / 挂的哪个指纹」, 增益归因只能靠外部比对。R496 把 "
             "`ledger_mount/ledger_n/ledger_chars/ledger_code8/ledger_key_id/ledger_session8/ledger_strategy` 并入 "
             "`llm_call` 行 (逐调用一行内可见), 并把 R495 遗留的 raw `ledger_code` 字段从打点面删除。",
             "python3 %s/assert_face_r496.py --arm T1 --dir %s --channel on --mount on" % (D, D),
             "%s/assert-face-T1.json" % D, "%s/assert_face_r496.py" % D,
             ["src/agent.modelqueue/ModelQueueRouter.cs", "%s/tel-T1/host.jsonl" % D, "%s/flags-T1.json" % D],
             "打点面**不得**再出现 raw 真值 (字段级负控: `ledger_code` 命中即红); 实发面与打点面的 (n, code8) "
             "必须逐对一致 (两路同源不同通道)。")

    r5 = row("r496.remote-call-token-drop", "L2",
             "**同窗同网格的验收读数 (本地通道对远端调用的替代率)**: 三臂 B(全关) → T0(闸/跳轮/声明门/pair_trim) → "
             "T1(=T0+台账挂载) 同二进制同上游同网格, 远端调用数与远端 token 由中继 usage 派生 (禁手抄), "
             "验收口径 = 同窗 B→T1 的 total_tokens 降幅 ≥30%。",
             "python3 %s/analyze_r496.py --dir %s" % (D, D),
             "%s/kpi-r496.json" % D, "%s/analyze_r496.py" % D,
             ["%s/calls-B.jsonl" % D, "%s/calls-T0.jsonl" % D, "%s/calls-T1.jsonl" % D,
              "%s/usage-B.jsonl" % D, "%s/usage-T0.jsonl" % D, "%s/usage-T1.jsonl" % D,
              "%s/flags-B.json" % D, "%s/flags-T0.json" % D, "%s/flags-T1.json" % D],
             "跨轮禁相减 (网格/判据器已改版) ⇒ 只报同窗阶梯; 空正文/隔离调用单列 (R493 归因), 不以分母变化换降幅; "
             "quality 面 (t13-15) 由 judge_code 单列, 不并入 token 降幅。")

    new = [r for r in (r1, r2, r3, r4, r5) if r["id"] not in ids]
    if dry:
        print(json.dumps(new, ensure_ascii=False, indent=1)[:2000]); return 0
    reg["rows"].extend(new)
    reg["updated_round"] = "R496"
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[register] +%d 行 (updated_round=R496) → %s" % (len(new), REG))
    for r in new:
        print("  ", r["id"], r["level"], "artifact_sha12=%s inst=%s" % (
            r["evidence_generated_with"]["artifact_sha12"], r["evidence_generated_with"]["instrument_sha12"]))
    return 0


if __name__ == "__main__":
    sys.exit(main("--dry" in sys.argv))
