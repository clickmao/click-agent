#!/usr/bin/env python3
"""R462 registry 行外科式插入: 只补前一行逗号, 保持 2 空格缩进与 EOF 无换行。"""
import io
import json
import re
import sys

P = '/home/agentuser/AgentFramework/docs/verification-registry.json'
rows = [
    {
        "id": "r462.recall-reality-gate",
        "level": "L2",
        "capability": "召回-现实一致性闸 (机制, 非提示词补丁): 召回块/记忆块/工具回灌面里引用的**路径样事实**由当前工作区文件系统裁决, 不一致即显式标 [核验✗ …] (一致时才标 [核验✓ 现存 N B]; 召回片段走 failOnly ⇒ 一致时零字节注入, 守住 token 预算)。同夹具/同 7 轮/同适配器 E2E, 唯一差异=二进制: P1 11 个实发消息带 ✗ (recall_stale_refs 含 report.md) / P2 [工作区文件 logic.unit] 进面 · [工作区文件 blob.bin] 不进面 / P3 召回片段 0 处 ✓ / P4 7 轮 ok + 四产物正确 + 回复面 0 处契约声明 ⇒ 4/4 PASS",
        "evidence_cmd": "bash /tmp/r462_e2e.sh",
        "evidence_path": "eval/rover/r462/verdict-r462.json",
        "negative_control": "NC1 (判别力): 同判据跑 R461 实发面 ⇒ P1/P2 = false (旧二进制无闸 + 后缀白名单), 见 /tmp/r462_negctl.json; NC2 越界: ../etc/hosts 一律判 ✗ 且不探测 (Verify_TraversalToken_RejectedWithoutProbe) + Probe 层 StartsWith(root) 二次校验; NC3 fail-safe: 无 root/不存在/异常 ⇒ 原样返回, 不丢事实不造事实 (Verify_NoRoot_FailSafe_ReturnsOriginal); NC4 幂等: 已带标签的块二次通过不重复追加 (Verify_Idempotent_NoDoubleTagging); NC5 只打假: 一致的召回片段必须逐字节不变 (Verify_FailOnly_ConsistentClaim_ZeroByteInjection) + 回灌面零字节 (Loop_ToolResult_ConsistentPath_ZeroByteInjection); NC6 结构判定负控: 1.5 / 提升3.2倍 / .. / 空 串不得判为路径 (IsPathLike_Structural_NoSuffixWhitelist)",
        "covers": [
            "src/agent.core/core/RecallRealityGate.cs",
            "src/agent.modelqueue/ActionLoop.cs",
            "src/agent/action/WorkspaceActionPort.cs",
            "src/agent/contextassembler/ContextAssembler.cs",
            "src/agent/IndustrialAgentV2.cs",
            "src/agent.tests/RecallRealityGateTests.cs",
            "src/agent.tests/ActionLoopTests.cs",
            "eval/rover/r462/judge_r462.py",
            "eval/rover/r462/verdict-r462.json",
            "eval/rover/r462/prereg-r462-e2e.json",
            "docs/plans/v0.81.0-r462-recall-reality-gate.md",
            "docs/reports/recall-reality-gate-r462.md"
        ],
        "owner_round": "R462",
        "checks_posthoc": [
            "P1 在 v1/v2/v3 三轮为**未行使** (通道未覆盖: 陈旧引用只出现在工具回灌面), v4 起接通该通道后才可行使 ⇒ 前三轮的 false 不得当作产品缺陷, 也不得当作通过 (prereg amendment_v4 留档)",
            "判据修订留档: v1 (召回窗口被运行期 data/ 占满) / v2 (P4 误判 system prompt 契约说明; P2 被 list_dir 结果污染) / v3 (P1 通道缺失) ⇒ 全部记器具/口径缺陷"
        ],
    },
    {
        "id": "r462.language-agnostic-recall",
        "level": "L2",
        "capability": "语言无关召回探针 (承 R447 用户令「管道内一律标通用代码逻辑」): 删 ContextAssembler 工作区召回的**硬编码后缀白名单** (源码逐字列语言后缀), 改结构+内容探针 WorkspaceTextProbe (空文件/NUL/二进制 ⇒ 弃; 后缀集只在 AGENTFRAMEWORK_TEXT_SUFFIX_ALLOWLIST 显式配置时生效); 语言标签集外置为数据文件 config/base/language-tags.txt, 机检只读数据 ⇒ 换语言/新增语言零改码。读数: 非白名单后缀文本 logic.unit 进召回面, 含 NUL 的 blob.bin 不进",
        "evidence_cmd": "bash /tmp/r462_e2e.sh && python3 eval/rover/r462/judge_r462.py",
        "evidence_path": "eval/rover/r462/verdict-r462.json",
        "negative_control": "NC1 判别力: R461 实发面同判据 ⇒ logic.unit 不进面 (旧白名单拒非白名单后缀) = false; NC2 二进制负控: 含 NUL 的文件必须被判非文本 (TextProbe_BinaryAndEmptyRejected_TextAccepted); NC3 空文件负控: 0 字节不得进召回; NC4 源码机检: 闸源码与 ContextAssembler 不得出现语言标签数据文件里的任何后缀字面量 (RecallRealityGate_Source_HasNoLanguageSuffixLiteral / TextProbe_ContextAssemblerPipeline_HasNoSuffixWhitelistLiteral); NC5 白名单语义负控: 未配置 ⇒ 全允许, 配置后按集过滤 (TextProbe_SuffixAllowlistOnlyWhenConfigured)",
        "covers": [
            "src/agent/context/WorkspaceTextProbe.cs",
            "src/agent/contextassembler/ContextAssembler.cs",
            "config/base/language-tags.txt",
            "src/agent.tests/RecallRealityGateTests.cs",
            "eval/rover/r462/r462_setup.sh",
            "eval/rover/r462/judge_r462.py"
        ],
        "owner_round": "R462",
    },
]

s = io.open(P, encoding='utf-8').read()
marker = '\n  ],\n  "aot_check_policy"'
i = s.rfind(marker)
if i < 0:
    print('VOID: marker 未命中'); sys.exit(1)
block = ',\n'.join(json.dumps(r, ensure_ascii=False, indent=2) for r in rows)
block = '\n'.join('  ' + l for l in block.split('\n'))
new = s[:i] + ',\n' + block + s[i:]
new2 = re.sub(r'"updated_round": "R\d+"', '"updated_round": "R462"', new, count=1)
io.open(P, 'w', encoding='utf-8').write(new2)
d = json.load(io.open(P, encoding='utf-8'))
print('rows:', len(d['rows']), 'last:', d['rows'][-1]['id'], 'updated_round:', d.get('updated_round'))
