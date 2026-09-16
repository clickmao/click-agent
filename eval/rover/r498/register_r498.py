#!/usr/bin/env python3
"""R498 登记器: 把本轮六条能力写进 docs/verification-registry.json (幂等: 先删 r498.* 旧行再加)。

用法: python3 eval/rover/r498/register_r498.py [--apply]
不带 --apply 时只打印将要写入的行 (dry-run)。
读入一律 utf-8-sig (仓内 json 带 BOM 的历史遗留)。

**R2e/R2f 契约 (勿手写)**: `evidence_generated_with` 必须是由
`eval/capability/bind_evidence.py --only <id,...> --round R498 --apply` **派生**的对象
(kind/pin_status/pin_reason/artifact_sha12/instrument/instrument_sha12/binding/audited_by_round)。
手写字面量会被 pre-commit 闸判红 (R2e: 非对象) —— 本轮即由该闸拦下一次。
故本脚本**不写**该字段: needs_field 行 (evidence_path 前缀 eval/ 或 docs/reports/) 交给器具填。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REG = Path("docs/verification-registry.json")

ROWS = [
    {
        "id": "r498.local-paraphrase-channel",
        "level": "L2",
        "owner_round": "R498",
        "capability": (
            "**R413 主线补口: 内容承载的本地生成通道**。R497 遗留缺口 = 本地消化只有「模板 ack」与「原样回放」"
            "两条零生成通道, 「同义改写族」(换个说法) 因无生成能力无法吸收 (吸收即退化成回放/模板 = R488 退化)。"
            "R498 补上第三条: 用 r1 对上一条**实质答复**做改写, 与复述族互斥 (IsPureParaphrase 内含 ¬IsPureRepeat), "
            "历史只取一次 (R466 单源纪律)。闸 AGENTFRAMEWORK_LOCAL_PARAPHRASE 默认关 (只有字面 \"1\" 算开) ⇒ "
            "默认行为逐位不变; 闸关时接线处与单测读同一个 ShouldAbsorb (闸关零吸收可机检, 非口头承诺)。"
            "结算类新增 ContinuationBrief.SettleLocalParaphrase 并并入 IsLocalSettled ⇒ 本地改写正文不被兜底横幅覆盖。"
            "降级面全部有计数器 (GuardRejected/DegradedNoSource/DegradedNoPort/DegradedEngine/AccountingViolations) "
            "⇒ 「接了通道」与「通道恒被拒」在读数上可分。"
        ),
        "evidence_cmd": ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test "
                         "src/agent.tests/agentframework.tests.csproj -c Release --filter \"FullyQualifiedName~R498LocalParaphraseTests\""),
        "evidence_path": "src/agent.tests/R498LocalParaphraseTests.cs",
        "covers": ["src/agent.modelqueue/LocalParaphraseChannel.cs", "src/agent.modelqueue/ModelQueueRouter.cs",
                   "src/agent/IndustrialAgentV2.cs", "src/agent/context/ContinuationBrief.cs",
                   "src/agent.modelqueue/LocalGenerationPort.cs"],
        "negative_control": ("闸关负控: ShouldAbsorb(x, enabled:false)==false (默认行为不变); 族互斥负控: 「换个说法说下部署进度」等"
                             "含内容字/数字/ASCII/问号/超长 8 例逐项必须 false; 与复述族两两不相交。"),
    },
    {
        "id": "r498.paraphrase-guard-invariants",
        "level": "L2",
        "owner_round": "R498",
        "capability": (
            "**改写结果的结构不变量守卫 (fail-closed)**: ①标识符守恒 —— 原文中「长度≥2 且含数字」或「长度≥4」的 ASCII 词元"
            "必须在改写输出中逐字出现 (丢失即拒); ②标识符禁增 —— 输出中出现原文没有的同类词元即拒 (防 R488 类幻觉); "
            "③动作宣称禁增 —— 输出含原文没有的动作声明 (已完成/已部署/已运行…) 即拒 (承 R489: 本地确定性答复不得声称做了事); "
            "④长度带 0.4~2.5 双向越带即拒; ⑤反问/问号即拒; ⑥思考链与围栏泄漏即拒。任一条破即**降级远端** ⇒ 失败方向是安全的。"
            "抽取规则语言无关 (只按字符类, 无后缀/关键词表)。"
            "诚实边界: 守卫检的是**结构不变量**, 不是语义等价 —— 语义正确性只由真机人工质量细读取证, 本轮未做。"
        ),
        "evidence_cmd": ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test "
                         "src/agent.tests/agentframework.tests.csproj -c Release --filter \"FullyQualifiedName~R498LocalParaphraseTests\""),
        "evidence_path": "src/agent.tests/R498LocalParaphraseTests.cs",
        "covers": ["src/agent.modelqueue/LocalParaphraseChannel.cs"],
        "negative_control": ("六个方向各一条负控 (标识符丢失/新增、动作声明新增、长度越带两个方向、问号、思考链) 全部必须拒; "
                             "同时一条正控必须过 (合法改写通过) ⇒ 守卫不是「恒拒」。"),
    },
    {
        "id": "r498.telemetry-pending-ring-fifo",
        "level": "L4",
        "owner_round": "R498",
        "capability": (
            "**真缺陷 88 (遥测 pending 环满环丢最新) 修复 + 存量并发竞态收口**。旧策略 `if (Count < 256) Add(...)` 在环满时"
            "丢弃的是**最新**一条 —— 而「Configure 紧前发出的那条」(启动路径探针) 恰是环里最新的 ⇒ R121「不静默丢失」的语义"
            "被上限反向破掉: 越接近 Configure 的点越容易被丢。修复 = 满环 FIFO **淘汰最旧** + 单列 PendingEvictions 让淘汰可见; "
            "同时把 DroppedTotal 与「已缓存」口径拆开 (新增 PendingBuffered)。"
            "竞态收口: AgentTelemetry 是进程级静态面 (writer/_configured/pending 环全局单例), 任何并行测试类都在与之争用同一份状态。"
            "新增 [CollectionDefinition(DisableParallelization=true)] 的 agent-telemetry-static 集合, 把 5 个触碰 AgentTelemetry 的"
            "测试类全部并入 (不与任何其它集合并行), 并加 internal ResetForTests 接缝让每条用例从已知初态起跑。"
        ),
        "evidence_cmd": ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test "
                         "src/agent.tests/agentframework.tests.csproj -c Release --filter \"FullyQualifiedName~R498TelemetryRingTests\" "
                         "| tee /tmp/ring.txt; cat eval/rover/r498/telemetry-ring-before-after.txt"),
        "evidence_path": "eval/rover/r498/telemetry-ring-before-after.txt",
        "covers": ["src/agent.config/AgentTelemetry.cs", "src/agent.tests/AgentTelemetryStaticCollection.cs",
                   "src/agent.tests/R498TelemetryRingTests.cs", "src/agent.tests/TelemetryPendingTests.cs"],
        "negative_control": ("**注入臂 (R4 级)**: 把环策略注回旧形态 (满环丢最新) ⇒ R498TelemetryRingTests 必红 (实测 Failed 1/2, "
                             "探针缺席于 flush 落盘文件); 恢复 FIFO 淘汰 ⇒ 绿 (实测 78/78)。无此注入则该断言与机制无因果绑定。"),
    },
    {
        "id": "r498.file-face-boundary-positive-control",
        "level": "L4",
        "owner_round": "R498",
        "capability": (
            "**文件面「越界必拒」的结构正控 (P1 边界)**。R497 遗留: 文件面越界拒绝是无闸常量 (Resolve 无条件拒) ⇒ 该断言只能被"
            "断言成恒真, 把整段检查删掉后旧的负样本用例仍会因「文件不存在」而红 (红因与被测行为无因果绑定 = 无判别力)。"
            "R498 把 Resolve 接到命令面**同一个**闸常量 AGENTFRAMEWORK_ACTION_BOUNDARY (默认开) ⇒ 得到缺陷注入臂: "
            "闸=1 越界读必须拒绝且**不得回显字节**; 闸=0 同调用必须成功并回显 ⇒ 上一条断言被证明是活的。默认行为逐位不变。"
        ),
        "evidence_cmd": ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test "
                         "src/agent.tests/agentframework.tests.csproj -c Release --filter \"FullyQualifiedName~R498BoundaryPositiveControlTests\""),
        "evidence_path": "src/agent.tests/R498BoundaryPositiveControlTests.cs",
        "covers": ["src/agent/action/WorkspaceActionPort.cs"],
        "negative_control": ("注入臂闸=0 必**成功且回显** canary (证明拒绝断言非恒真); 反向负控: 闸=1 时区内读/区内写必须照常工作 "
                             "(防「一刀切全拒」同时骗过前两条)。"),
    },
    {
        "id": "r498.mount-cost-fixed-vs-behavior-leg",
        "level": "L2",
        "owner_round": "R498",
        "capability": (
            "**挂载成本的定长腿 vs 行为腿归因 (离线, 读 R497 同窗产物)**: T2→T1 只动挂载轴, 读数 calls 13→12 (−7.69%) / "
            "tokens 62536→71511 (**+14.35%**)。分解: 挂载块自身 (定长腿) 逐调用 168.5 字符 / est 84.36 tok, 11 条挂载调用合计 "
            "est 928 (占 est 增量 3044 的 30.5%); 按逐调用实测比例折算上界 1123 real tok ⇒ **占 real 增量 8975 的 12.5%**; "
            "**行为腿 (残差) = 7852 real tok = 87.5%** (其中 prompt +4248 / completion +4727)。"
            "结论: 挂载轴的正向 token 增量**主要不是挂载块本身的长**, 而是模型行为改变 (输出变长)。"
            "覆盖事实: 12 条 T1 调用中 11 条带挂载, 1 条 (seq=5, est=49) 是隔离通道调用不带挂载 —— 归因按**实际覆盖**计, 不按调用总数计。"
        ),
        "evidence_cmd": "python3 eval/rover/r498/mount_attrib_r498.py",
        "evidence_path": "eval/rover/r498/mount-attrib-r498.txt",
        "covers": ["eval/rover/r497/calls-T1.jsonl", "eval/rover/r497/calls-T2.jsonl",
                   "eval/rover/r497/usage-T1.jsonl", "eval/rover/r497/usage-T2.jsonl"],
        "negative_control": ("est 口径复算与落盘值逐调用比对 (n=12) 必须一致 —— 不一致则分解基数不可信 (checks.est_recompute_parity)。"
                             "另: 定长腿只对**实际带挂载**的 11 条调用计入, 不做 12 条外推。"),
    },
    {
        "id": "r498.mcp-absent-registered",
        "level": "L1",
        "owner_round": "R498",
        "capability": (
            "**候选⑥ (MCP 链级 E2E) 的缺席登记**: 全仓 src/**/*.cs 检索 `mcp|Mcp|MCP` 命中 **0** 处 (排除 /obj/ /bin/) ⇒ "
            "仓内不存在 MCP 面, 该候选无被测对象。与用户既定技术立场一致 (MCP 不做; 前端只暴露接口) ⇒ 本轮登记为「排除项」"
            "而非「未做项」: 需要做 MCP 才谈得上 E2E, 否则是往空面上写用例。"
        ),
        "evidence_cmd": "grep -rln \"mcp\\|Mcp\\|MCP\" src/ --include=*.cs | grep -v \"/obj/\" | grep -v \"/bin/\" | wc -l",
        "evidence_path": "eval/rover/r498/mcp-absent-r498.txt",
        "covers": ["src/"],
        "negative_control": ("无 (缺席登记不构成能力断言) —— 故 level 只给 L1, 不得据此宣称任何 MCP 相关能力。"),
    },
]


def main() -> int:
    apply = "--apply" in sys.argv
    raw = REG.read_text(encoding="utf-8-sig")
    doc = json.loads(raw)
    rows = doc["rows"]
    before = len(rows)
    rows[:] = [r for r in rows if r.get("owner_round") != "R498"]
    removed = before - len(rows)
    rows.extend(ROWS)
    doc["updated_round"] = "R498"
    out = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    print(f"[dry={not apply}] removed_old={removed} added={len(ROWS)} total={len(rows)}")
    if apply:
        REG.write_text(out, encoding="utf-8")
        # 读回自检 (写后必读回, 禁凭写入成功宣称)
        back = json.loads(REG.read_text(encoding="utf-8-sig"))
        ids = [r["id"] for r in back["rows"] if r.get("owner_round") == "R498"]
        assert len(ids) == len(ROWS), f"读回条数不符: {ids}"
        assert back["updated_round"] == "R498"
        print("PASS 读回:", ", ".join(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
