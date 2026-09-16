#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q36 器具: 投影规则表扩容 (新增 drop / drop_by_id 两模式) —— 程序化改写 + 逐字节复现闸。

纪律 (R409): ①改写前先断言「序列化器逐字节复现原文件」; ②只做最小改动;
③幂等; ④改写后读回校验。
"""
import json
import sys

RULE = 'eval/capability/projection_rules.json'
ROUND = 'EXP1-Q36'

raw = open(RULE, 'rb').read().decode('utf-8')
doc = json.loads(raw)
# ① 复现闸: 若用 (indent=1) 重排能逐字节复现原文件 ⇒ 可安全程序化改写; 否则改为文本插入
def ser(d):
    return json.dumps(d, ensure_ascii=False, indent=1) + '\n'
roundtrip_ok = (ser(doc) == raw)
print('ROUNDTRIP_IDENTICAL=%s' % roundtrip_ok)
if not roundtrip_ok:
    print('ABORT: 序列化器不能逐字节复现原文件 ⇒ 改用文本插入 (本脚本拒绝静默重排)')
    sys.exit(2)

rules = doc['rules']
before = len(rules)

# ② pre_existing: array_count → drop (基数逐跑累积增长 ⇒ 保留计数=恒不稳)
for r in rules:
    if r['path'] == 'side_effect_attribution/pre_existing':
        r['mode'] = 'drop'
        r['basis'] = (
            'EXP1-Q36 实测推翻 Q35 的声明: 该族**基数本身**逐跑增长 (T1..T7 实测 51/54/57/66/67/71/72), '
            '因每跑都会把本轮新产物留成下一跑的「窗口前已存在」文件 ⇒ 保留 #n= 计数等于保留一个恒不稳的量。'
            '故由 array_count 改 drop (整子树**含基数**剔除)。成员真值仍完整保留在**原始面记录**里; '
            '环境脏红的判读不依赖本族 (side_effect_attribution.red 与 old_gate_* 仍在投影内)。')

new_rules = [
    {"path": "side_effect_attribution/old_gate_delta", "mode": "array_count",
     "basis": ("EXP1-Q36 实测 (T6 vs T7 投影后仍有差异的唯一非自指叶之一): 成员 = 窗口内**旧闸新报**的"
               "脏路径名 (由窗口内他人/本侧写入派生), 与 foreign_writes 同源。取 array_count: 成员遮蔽, "
               "基数保留 ⇒ 干净窗口下计数恒 0 (pin 稳定), 有外来写入时计数 ≠ 0 (pin 需重取, 已入口径声明)。")},
    {"path": "side_effect_attribution/old_gate_false_reds", "mode": "array_count",
     "basis": ("EXP1-Q36 实测: 同上 (成员名逐跑变, 计数即可判信号)。")},
    {"path": "results[*]", "mode": "drop_by_id",
     "selector": {"path": "results[*]/id",
                  "values": ["bind_evidence.check", "bind_evidence.committed-state"]},
     "basis": ("EXP1-Q36 实测 (自指成员): 这两个成员的真值随**树态**翻转 —— 提交前 rc=2 / 提交后 rc=0 "
               "(T1..T3 与 T4..T7 实测), 且其 l2_fields 会随器具 sha 变化。它们判的是「记录所在树态与 HEAD "
               "是否自洽」, 不是器具行为 ⇒ 不可冻结。修法 = 成员级**按身份**选择性遮蔽 (整成员剔除): "
               "其余 25 个成员 (含 results[*]/rc,pass,sha12,negative_controls) 全部留在投影内, "
               "行为面照旧可判。该两成员的状态由提交态核验器 (check_committed_state_q30.py --selftest) "
               "独立轮次判定, 不以 pin 形式宣称。")},
]
have = {r['path'] for r in rules}
for nr in new_rules:
    if nr['path'] in have:
        print('IDEMPOTENT: %s 已存在, 跳过' % nr['path'])
        continue
    rules.append(nr)

doc['round'] = ROUND
doc['owner_round'] = ROUND
doc['masking_policy'] = (
    '只遮蔽**运行期/环境/身份**读数 (墙钟、随机目录、进程 pid、窗口内他人写入与既有文件成员、由其派生的计数), '
    '绝不遮蔽**器具行为面**: results[*] (逐条裁决/rc/证据 sha/负控)、side_effects (自身脏路径)、'
    'side_effect_attribution.{verdict,red,measurement_ok,reasons}、conservation.ok。'
    'EXP1-Q36 唯一例外 (成员级、按身份枚举): results[*] 中 id ∈ {bind_evidence.check, '
    'bind_evidence.committed-state} 两个**自指成员**整成员剔除 —— 其真值随树态 (记录 vs HEAD) 翻转, '
    '冻结它等于冻结一个非器物量; 该两成员由提交态核验器独立判, 且枚举写死在规则文件里 (不是模式匹配)。')
doc['comparability_break'] = (
    'EXP1-Q36 起 (a) pre_existing 由 array_count 改 drop (含基数) (b) 新增 old_gate_delta / '
    'old_gate_false_reds 两条计数规则 (c) 新增 results[*] 成员级 drop_by_id ⇒ 投影摘要口径再次变更, '
    '与 EXP1-Q35 及以前的投影摘要**不可直接比**; 受影响: r444.instrument-acceptance 的 pin '
    '(本轮由器具派生重取, audited_by_round=EXP1-Q36)。')
doc['clean_window_condition'] = (
    '本投影的不动点宣称**带条件**: 「同一树态 ∧ 窗口内零外来写入 ∧ 窗口内无本侧自写」下, 重跑投影摘要相等。'
    '判据: 面记录里 foreign_writes / old_gate_delta / old_gate_false_reds 任一非空 ⇒ 该 pin **需重取** '
    '(不是缺陷, 是窗口不纯的可见痕迹)。')

out = ser(doc)
if out == raw:
    print('NO_CHANGE')
else:
    open(RULE, 'w', encoding='utf-8', newline='').write(out)
back = json.loads(open(RULE, encoding='utf-8').read())
print('RULES %d -> %d' % (before, len(back['rules'])))
print('MODES=%s' % sorted({r['mode'] for r in back['rules']}))
assert back['round'] == ROUND and len(back['rules']) == before + len(new_rules)
print('READBACK_OK')
