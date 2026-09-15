#!/usr/bin/env python3
"""R460 registry 行外科式插入: 只补前一行逗号, 保持 2 空格缩进与 EOF 无换行。"""
import io, json, sys

P = '/home/agentuser/AgentFramework/docs/verification-registry.json'
row = {
    "id": "r460.brevity-menu-cache",
    "level": "L2",
    "capability": "承接轮精炼 + 菜单单源 + 命中率/token 归因 (真机 E2E, 同夹具/同 6 轮/同模型, 唯一差异=二进制): T5 回复 241→160 字 (-33.6%), 承接注入块 288→163 字 (-43.6%, MaxArtifacts 8→3 + 紧凑两行 + 截断诚实标注); 门问句与兜底反问同源 (BuildAsk/BuildMenu) ⇒ 空态不再给通用示例菜单 (搜索资料/写文档/…), 有事实时 Choices=3 真实名+「另有新任务」; T5 实发 3 项编号菜单 (①②③) 且首项接地真实产物; prompt ∑ 54,927→39,863 (-27.4%), 调用 17→13 (=codex); 稳态 miss 均价 301.9 tok (R458 310, codex 236), 稳态 hit 90.2% —— 命中率未达标根因 = [SessionMemory] 注入块逐轮膨胀 308→836 字符 (实发全量文本归因, ADAPTER_DUMP_FULL=1)",
    "evidence_cmd": "bash /tmp/r460_setup.sh && bash /tmp/r460_run.sh && python3 eval/rover/r460/judge_r460.py",
    "evidence_path": "eval/rover/r460/verdict-r460.json",
    "negative_control": "C1 空态负控: 空工作区时承接块/反问都不得出现任何文件名 (Block_EmptyState_SaysNone_AndNeverNamesAFile); C2 菜单单源 + 空态无示例菜单负控: 门 Choices 必须逐项等于 ContinuationBrief.BuildMenu 输出, 且空态不得出现「搜索资料/写文档」类通用示例 (EvidenceGate_VagueQuestion_IsGroundedInRealFacts, 含 Assert.Equal(ContinuationBrief.BuildMenu(facts), choices)); C3 精炼负控: 3 项态块 ≤ MaxBlockChars(200) 且菜单 ≤3 项且每项 ≤ MaxMenuItemChars(24) 且首项接地 (R460_BlockAndMenuAndAsk_RespectBrevityCaps); C4 人话负控: 承接句不得含内部术语且 ≤ MaxNoticeChars(48) (HumanizeVoidNotice_IsPlainSpeech_NoInternalJargon); C5 判分器具自检: 首跑把实发「①②③」菜单漏判为 0 项 (器具缺陷, 已修并留痕); 判分只读磁盘产物 + 实发全量文本 (ADAPTER_DUMP_FULL=1), 不采信回复自述",
    "covers": [
        "eval/rover/r460/judge_r460.py",
        "eval/rover/r460/verdict-r460.json",
        "eval/rover/r460/prereg-r460.json",
        "eval/rover/r460/attr_r460.py",
        "src/agent/context/ContinuationBrief.cs",
        "src/agent/registry/EvidenceGate.cs",
        "src/agent/intent/PlanResumeService.cs",
        "src/agent/IndustrialAgentV2.cs",
        "src/agent.tests/ContinuationBriefTests.cs",
        "docs/plans/v0.79.0-r460-brevity-menu-cache.md",
        "docs/reports/brevity-menu-cache-r460.md"
    ],
    "owner_round": "R460",
    "checks_posthoc": [
        "合同标记上前台 (T4 裸 clickproof/premise/goal 5 行, T6 no_formal 1 行) —— 首跑后新发现, 未列入预注册判据, R461 靶点",
        "T4 无 tool_call 却宣称 stats.txt 已写入 chars=15 (磁盘 0 B) —— 产物 3/4, 属模型侧方差 + 链未拦截宣称; 承接块过滤 0 B 文件使模型改用记忆假值"
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
io.open(P, 'w', encoding='utf-8').write(new)
d = json.load(io.open(P, encoding='utf-8'))
print('rows:', len(d['rows']), 'last:', d['rows'][-1]['id'], 'updated_round:', d.get('updated_round'))
