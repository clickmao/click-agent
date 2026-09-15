#!/usr/bin/env python3
# R470 台账回灌: 追加 2 行到 docs/verification-registry.json (幂等: 同 id 已存在则替换)
import collections, io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
P = os.path.join(ROOT, 'docs', 'verification-registry.json')

NEW = [
    collections.OrderedDict([
        ("id", "r470.cache-channel-attribution"),
        ("level", "L2"),
        ("capability", "真实流量命中归因通道(跨会话共享前缀)打点: 无同会话前驱的调用命中归因 shared_prefix(否则 -1, 禁双计), 只在既有 -1 之上补通道不回收口径; 三处 data-carrying llm_call 打点全铺 cache_channel/shared_prefix_hit_tokens/shared_prefix_hit_rate; 真实 43 条调用 100% 落入 shared_prefix"),
        ("evidence_cmd", "python3 eval/rover/r470/real_calls.py && env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test src/agent.tests/agentframework.tests.csproj -c Release --filter \"FullyQualifiedName~PromptCacheChannelTests|FullyQualifiedName~VerificationFormTests\""),
        ("evidence_path", "eval/rover/r470/asserts.json"),
        ("negative_control", "real_calls.py 判据 C6: (a)有前驱 ⇒ shared_prefix_* 必须 -1(禁双计) (b)未上报 ⇒ -1 不得 0 (c)prompt=0 ⇒ unknown ∧ -1 (d)归因规则反写 ⇒ 原判据不成立(4/4 true); C# 侧 PromptCacheChannelTests 同语义 8 例含真值回放"),
        ("covers", [
            "src/agent.modelqueue/PromptCacheKpi.cs",
            "src/agent.modelqueue/ModelQueueRouter.cs",
            "src/agent.tests/PromptCacheChannelTests.cs",
            "src/agent.tests/PromptCacheKpiTests.cs",
            "eval/rover/r470/real_calls.py",
            "eval/rover/r470/asserts.json",
            "docs/reports/r470-cache-channel-attribution.md",
        ]),
        ("owner_round", "R470"),
    ]),
    collections.OrderedDict([
        ("id", "r470.real-feed-cache-actuals"),
        ("level", "L2"),
        ("capability", "真实远端调用(非桩)缓存实测: host.jsonl llm_call 43 条 ⇒ 命中占比 45.44%(hit 59518/prompt 130974), 命中量饱和 2048~2304(64 对齐, 例外 2 条 hit=127), K2b effective_hit_rate 43/43 = -1(同会话前驱 0 ⇒ 真实流量上 100% 不适用) ⇒ 判定「97% 红线在真实流量上不可测」并给分档新算量(B 档 1020 / C 档 3320 tok)"),
        ("evidence_cmd", "python3 eval/rover/r470/real_calls.py"),
        ("evidence_path", "eval/rover/r470/real-calls.json"),
        ("negative_control", "同 C6(d) 归因反写; 且断言逐值比对直方图(C3b)与对齐例外(C4)逐条列出 ⇒ 指标非恒真且不得静默过滤"),
        ("covers", [
            "eval/rover/r470/real-calls.json",
            "eval/rover/r470/negctl.json",
            "docs/plans/v0.87.0-r470-cache-channel-attribution.md",
        ]),
        ("owner_round", "R470"),
    ]),
]

d = json.load(io.open(P, encoding='utf-8'), object_pairs_hook=collections.OrderedDict)
rows = d['rows']
ids = {r['id'] for r in rows}
added, replaced = [], []
for n in NEW:
    if n['id'] in ids:
        for i, r in enumerate(rows):
            if r['id'] == n['id']:
                rows[i] = n
        replaced.append(n['id'])
    else:
        rows.append(n)
        added.append(n['id'])
d['updated_round'] = 'R470'
# 台账原文缩进 = 1 空格, 重排会制造 3998 行 diff 噪声 ⇒ 必须保形写回
io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"added": added, "replaced": replaced, "total_rows": len(rows), "updated_round": d['updated_round']}, ensure_ascii=False))
