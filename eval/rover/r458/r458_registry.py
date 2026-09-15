#!/usr/bin/env python3
# R458 registry 追加行 (外科式文本插入: 只补前一行逗号, 保持 2 空格缩进与 EOF 无换行)。
import json, io, sys

P = '/home/agentuser/AgentFramework/docs/verification-registry.json'
row = {
    "id": "r458.humanized-continuation",
    "level": "L2",
    "capability": "承接轮人性化(真机 E2E, 同夹具/同 6 轮/同模型): T5「继续」→ 逐项承接 4 个真实产物 + 「继续什么」反问 + 3 个具体可选项 (固定示例菜单 `(如: 搜索/写文档…)` 消失); T6 内部术语 3 行 → 0 行 (一句人话, 内部理由只进遥测); 承接块仅 T5 触发 1 次 (判定与门同判据: 弱意图 且 置信<0.60), 收口闸 grounded=true; 产物 4/4 不回退, 磁盘伪造 0; 调用 17 (R457 15, codex 冻结 13) —— 增量来自模型自身多用工具, 非承接机制成本",
    "evidence_cmd": "bash /tmp/r458_setup.sh && bash /tmp/r458_run.sh && python3 eval/rover/r458/judge_r458.py",
    "evidence_path": "eval/rover/r458/verdict-r458.json",
    "negative_control": "C1 空工作区负控: 块与兜底反问都不得出现任何文件名 (Block_EmptyState_SaysNone_AndNeverNamesAFile / Fallback_OnlyUsesRealFacts_AndNeverInventsFiles); C2 误判负控: 「当前目录下一共有几个 .py 文件？」(门置信 0.8, 门未发问) 不得判为承接轮 —— run1 真发生过并污染回复, 已机检固化 (Judgement_ConcreteQuestionAtHighConfidence_IsNotContinuation) + 反向正控裸「继续」0.45 必须判真; C3 人话承接句负控: 不得含内部术语 (可选范围/检查点/作废/槽位) 且内部理由不上前台 (HumanizeVoidNotice_IsPlainSpeech_NoInternalJargon); C4 截断负控: 超过上限必须如实标注「共 N 项, 只列最近 M 项」(Block_MarksTruncationHonestly_TotalVsListed); C5 判分只读磁盘产物 (逐字节归一) 不采信回复文本, 承接块证据取遥测 + 实发请求回显 + 引用名与磁盘比对",
    "covers": [
        "eval/rover/r458/judge_r458.py",
        "eval/rover/r458/verdict-r458.json",
        "src/agent/context/ContinuationBrief.cs",
        "src/agent/registry/EvidenceGate.cs",
        "src/agent/intent/PlanResumeService.cs",
        "src/agent/IndustrialAgentV2.cs",
        "src/agent.tests/ContinuationBriefTests.cs",
        "docs/plans/v0.78.0-r458-humanized-continuation.md",
        "docs/reports/humanized-continuation-r458.md"
    ],
    "owner_round": "R458"
}

t = io.open(P, encoding='utf-8').read()
assert t.rstrip().endswith('}'), 'EOF 形态异常'
if '"r458.humanized-continuation"' in t:
    print('已存在, 跳过'); sys.exit(0)
marker = '\n  ],\n  "aot_check_policy"'
i = t.rfind(marker)
assert i > 0, '未找到 rows 收尾'
body = json.dumps(row, ensure_ascii=False, indent=2)
body = '\n'.join(('  ' + ln) if ln.strip() else ln for ln in body.split('\n'))
t = t[:i] + ',\n' + body + t[i:]
t = t.replace('"updated_round": "R457"', '"updated_round": "R458"', 1)
io.open(P, 'w', encoding='utf-8').write(t)

d = json.load(io.open(P, encoding='utf-8'))
print('rows =', len(d['rows']), '| updated_round =', d['updated_round'])
print('last id =', d['rows'][-1]['id'], '| level =', repr(d['rows'][-1]['level']))
print('bytes =', len(io.open(P, 'rb').read()))
