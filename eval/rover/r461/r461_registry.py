#!/usr/bin/env python3
"""R461 registry 行外科式插入: 只补前一行逗号, 保持 2 空格缩进与 EOF 无换行。"""
import io, json, re, sys

P = '/home/agentuser/AgentFramework/docs/verification-registry.json'
row = {
    "id": "r461.contract-not-front-and-hit-budget",
    "level": "L2",
    "capability": "契约声明不上前台 + 零字节产物可见 + 每轮注入预算收口 (真机 E2E, 同夹具/同 6 轮/同模型, 唯一差异=二进制; 夹具两侧 md5 fe1f5530446bd4ceb8be1b944c8ec005): 前台契约声明行 3 处 (37/59/33 字符) → 0 (SplitFacing 剥围栏/裸块/no_formal 行, 只进遥测 contract_declaration_hidden; 剥离为空 fail-safe 返回原文); 记忆写入同剥离 (召回块不再带 no_formal:); 0 字节产物标 (空) 不再静默省略; ForecastRecord 上轮任务预览 ≤24 字; 每轮新内容预算 MemorySourceBudgetTokens 500→120 / SessionMemory 默认 1000→400 / 【已完成】4→2 条, 三处机检回归锁。读数: 稳态 hit 90.2%→91.2%, 稳态 miss 均价 301.9→274.9 tok (-9.0%); T5 152 字 (R458 241) 且 3 项菜单 ①②③; T6 118 字无内部术语; 调用 15 / prompt∑ 46,616 (R460 13/39,863) —— tokens KPI 未达标根因 = 调用数方差 (R458 17 / R460 13 / R461 15), 非前缀长度; 命中 97% 红线算术条件机检 = 平均前缀 3,118 tok ⇒ 每轮新内容须 ≤93.5 tok (实测 ≈275)",
    "evidence_cmd": "bash /tmp/r461_setup.sh && bash /tmp/r461_run.sh && python3 eval/rover/r461/judge_r461.py",
    "evidence_path": "eval/rover/r461/verdict-r461.json",
    "negative_control": "C1 契约剥离负控 (有判别力): 同一判据跑 R460 落盘回复 ⇒ 命中 3 处 (T1/T3 裸 no_formal: 行 + T4 无围栏 clickproof/premise/goal 块), R461 ⇒ 0; C2 fail-safe 负控: 整条回复只有契约声明时, SplitFacing 必须返回非空可见文本 (宁可少剥不给空回复) + 正控: 非本契约内容 (csharp 围栏/普通段落) 一字不动 (SplitFacing_FailSafe_Never_Blanks_The_Reply / SplitFacing_Keeps_Other_Fences_And_Positive_Control); C3 空产物负控: 0 字节文件必须显示 (空) 而非省略 (Empty_Artifact_Is_Marked_Not_Guessed); C4 预算回退负控: MemorySourceBudgetTokens ≤120 ∧ SessionMemory 默认 ∈[200,400] ∧ 里程碑 ≤2 机检 (R461_Injection_Budget_Locks + V714FeatureTests.SessionConfig_MaxMemoryChars_Default400_R461); C5 判分只读磁盘产物与实发全量文本 (ADAPTER_DUMP_FULL=1), 不采信回复自述; 编造判据 = 回复提到的文件名不在工作区目录列举中",
    "covers": [
        "eval/rover/r461/judge_r461.py",
        "eval/rover/r461/verdict-r461.json",
        "eval/rover/r461/prereg-r461.json",
        "src/agent/context/FormalPromptContract.cs",
        "src/agent/context/ContinuationBrief.cs",
        "src/agent/registry/ForecastRecord.cs",
        "src/agent/contextassembler/ContextAssembler.cs",
        "src/agent/session/SessionMemory.cs",
        "src/agent/IndustrialAgentV2.cs",
        "src/agent.tests/FormalPromptContractTests.cs",
        "src/agent.tests/ContinuationBriefTests.cs",
        "src/agent.tests/V714FeatureTests.cs",
        "docs/plans/v0.80.0-r461-contract-and-hitrate.md",
        "docs/reports/contract-and-hitrate-r461.md"
    ],
    "owner_round": "R461",
    "checks_posthoc": [
        "召回块引用「上一会话」存在的文件名 stats.txt, 本轮工作区根本不存在 ⇒ 模型 (T5) 宣称 stats.txt=chars=15 属编造; 机检 recall_stale_refs=[stats.txt] = 被编造的那个名字。未列预注册判据, R462 靶点 (召回-现实一致性闸, 用本地 r1 判真假)",
        "P2 空产物可见性本轮为**空判**: 0 B 文件未进入 top-3 承接块 ⇒ 该判据未被行使 (不得当作通过)"
    ],
}

s = io.open(P, encoding='utf-8').read()
marker = '\n  ],\n  "aot_check_policy"'
i = s.rfind(marker)
if i < 0:
    print('VOID: marker 未命中'); sys.exit(1)
block = json.dumps(row, ensure_ascii=False, indent=2)
block = '\n'.join('  ' + l for l in block.split('\n'))
new = s[:i] + ',\n' + block + s[i:]
new2 = re.sub(r'"updated_round": "R\d+"', '"updated_round": "R461"', new, count=1)
io.open(P, 'w', encoding='utf-8').write(new2)
d = json.load(io.open(P, encoding='utf-8'))
print('rows:', len(d['rows']), 'last:', d['rows'][-1]['id'], 'updated_round:', d.get('updated_round'))
