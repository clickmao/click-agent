#!/usr/bin/env python3
# R471 台账回灌: 追加 2 行到 docs/verification-registry.json (幂等: 同 id 已存在则替换)
import collections, io, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
P = os.path.join(ROOT, 'docs', 'verification-registry.json')

EV = ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/rover/r471/check_channels_r471.py")

NEW = [
    collections.OrderedDict([
        ("id", "r471.channel-aggregation-emitted"),
        ("level", "L2"),
        ("capability", "分通道命中聚合器读**产品实发字段**: scripts/kpi_cache_hit.py 只读 kv.cache_channel/shared_prefix_hit_tokens/shared_prefix_hit_rate; 缺 cache_channel ⇒ unreported.absent_field(既不算0也不算shared_prefix); 值非法 ⇒ invalid_value; 非 shared_prefix 通道两字段须显式 -1(≥0 ⇒ double_count 判红, 缺失 ⇒ wiring_hole 判红, fail-closed); shared_prefix 内 hit=-1 ⇒ 入 hit_na 不进求和(0命中与未上报可分); 守恒式 emitted.rows+unreported.total==calls 不闭合即判红; legacy 键与 HEAD 逐键零回归, 新增键仅 channels/channel_verdict"),
        ("evidence_cmd", EV),
        ("evidence_path", "eval/rover/r471/asserts-r471.json"),
        ("negative_control", "C5 六例(全部红或必须不冒充): (a)same_session 带非 -1 shared_prefix_* ⇒ double_count 判红 (b)shared_prefix 行 hit=-1 ⇒ hit_tokens 求和 0 且 hit_na=1(非静默当 0) (c)prompt=0 ⇒ unknown 且两字段 -1 且无判红 (d)无字段行 ⇒ unreported.absent_field=1 ∧ emitted.rows=0(不得 0/不得 shared_prefix) (e)归因条件反写 ⇒ derived_recompute 分通道计数改变(判据有判别力) (f)非 shared_prefix 通道缺字段 ⇒ wiring_hole 判红; C4 正控同形夹具 5 行精确读回且 emitted.rows=5>0(rc=0≠绿, 必查执行数>0); C6 零回归逐键比对 HEAD 版脚本"),
        ("covers", [
            "scripts/kpi_cache_hit.py",
            "eval/rover/r471/check_channels_r471.py",
            "eval/rover/r471/channel-fixtures.json",
            "eval/rover/r471/negctl-r471.json",
            "eval/rover/r471/asserts-r471.json",
            "docs/plans/v0.88.0-r471-channel-aggregation.md",
        ]),
        ("owner_round", "R471"),
    ]),
    collections.OrderedDict([
        ("id", "r471.derived-vs-emitted-separation"),
        ("level", "L2"),
        ("capability", "派生 vs 实发分离(诚实面): 真实流 43 条 llm_call 中**含 cache_channel 字段者 0 条(0/43)** ⇒ R470 的「shared_prefix 43/43」是证据脚本**派生值**, 非产品实发; 聚合器输出 emitted(实发)/unreported/derived_recompute(对照, 标注禁止相加)三段, 实发面在真实流上诚实报 0 行而非 43"),
        ("evidence_cmd", EV),
        ("evidence_path", "eval/rover/r471/real-feed-r471.json"),
        ("negative_control", "C2: emitted.shared_prefix 必须 == 0(断言「不得为 43」—— 若聚合器把派生量冒充实发量即判红); C3: 派生命中 == 59518 必须与 R470 记录值一致(证明对照列确实复现 R470 而非恒真); C1: 源 sha256 与 43 条计数机检(utf-8-sig 防 BOM 吞行)"),
        ("covers", [
            "eval/rover/r471/real-feed-r471.json",
            "eval/rover/r471/prereg-r471.json",
            "docs/reports/r471-channel-aggregation.md",
        ]),
        ("owner_round", "R471"),
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
d['updated_round'] = 'R471'
# 台账原文缩进 = 1 空格, 重排会制造全文件 diff 噪声 ⇒ 必须保形写回
io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"added": added, "replaced": replaced, "total_rows": len(rows), "updated_round": d['updated_round']}, ensure_ascii=False))
