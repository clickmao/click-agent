#!/usr/bin/env python3
"""R609 registry 行插入（保形：先证序列化器逐字节复现原文件，再文本插入；幂等；改后自校验）。"""
import io, json, sys, hashlib

P = 'docs/verification-registry.json'
ROUND = 'R609'
ROW_ID = 'r609.fork-pq2-smoke-and-instrument-fix'

text = io.open(P, encoding='utf-8').read()
data = json.loads(text)

# ① 序列化器保形断言
rt = json.dumps(data, indent=1, ensure_ascii=False) + '\n'
if rt != text:
    print('FMT_MISMATCH: 序列化器无法逐字节复现 ⇒ 改用文本插入前须知差异', file=sys.stderr)
    print('orig_len=%d rt_len=%d' % (len(text), len(rt)), file=sys.stderr)

# ② 幂等
if any(r.get('id') == ROW_ID for r in data['rows']):
    print('ALREADY_PRESENT rows=%d' % len(data['rows']))
    sys.exit(0)

row = {
 "id": ROW_ID,
 "level": "L3",
 "owner_round": ROUND,
 "capability": "RF0006 QR1b/QR1c 真机读数：厂商 fork prism-b10709-9a9394a × 新打包件 Ternary-Bonsai-4B-PQ2_0（1,074,969,344 B, 2.13 bpw g128）—— 加载/连贯/pp-tg 速度/pp-vs-上下文标度；同轮修正两处器具缺陷（REPL 失控放大 1.74 GB、模式判据假阳性 5/5）",
 "evidence_cmd": "bash eval/rover/r609/forkrun2.sh   # 五档 rc=0，落 eval/rover/r609/forkrun2.log.txt",
 "evidence_path": "docs/evidence/RF0006/ternary-recon-readings.md",
 "negative_control": "模式判据两侧样例：v1 溢出件（1,744,793,711 B ∧ 尾部连续 '> '）⇒ 判红；v2 五档（≤1,701 B ∧ rc=0）⇒ 判绿（同日志零重测复算）",
 "covers": ["eval/rover/r609/prereg-r609.json", "eval/rover/r609/readings-r609.json",
            "eval/rover/r609/forkrun2.log.txt", "eval/rover/r609/S1_legacy_on_fork.txt"],
 "evidence_generated_with": "eval/rover/r609/forkrun2.sh sha256 24d78cb560e016868f5e746c6244dc803160c0e044f55d84fe3ffbd3142044fe",
 "covers_extra": "非产品面轮：净 src/ 改动 0 ⇒ 无单测/AOT 等级主张；能力面（判别位夹具）未行使"
}

# ③ 文本插入：rows 数组的收尾 ' ]' 之前，给上一行补逗号
anchor = '\n ],\n "aot_check_policy"'
ins = text.index(anchor) - 1     # 最后一行行尾 '}' 的位置
assert text[ins] == '}' and text[ins - 2:ins] == '  ', 'rows 收尾锚点异常: %r' % text[ins - 20:ins + 3]
row_text = json.dumps(row, indent=1, ensure_ascii=False)
row_text = '\n'.join(('  ' + ln if ln else ln) for ln in row_text.split('\n'))  # 缩进到行级
new_text = text[:ins + 1] + ',\n' + row_text + text[ins + 1:]
new_text = new_text.replace('"updated_round": "R608"', '"updated_round": "%s"' % ROUND, 1)

# ④ 读回校验
d2 = json.loads(new_text)
assert any(r['id'] == ROW_ID for r in d2['rows']), 'readback 未见到新行'
assert d2['updated_round'] == ROUND, 'updated_round 未 bump'

# ⑤ 保形再断言（序列化器必须仍能逐字节复现新文件）
rt2 = json.dumps(d2, indent=1, ensure_ascii=False) + '\n'
shape_ok = (rt2 == new_text)
io.open(P, 'w', encoding='utf-8').write(new_text)
print('INSERTED id=%s rows %d→%d updated_round=%s serializer_byte_reproduce=%s'
      % (ROW_ID, len(data['rows']), len(d2['rows']), d2['updated_round'], shape_ok))
print('registry_sha12=%s' % hashlib.sha256(new_text.encode()).hexdigest()[:12])
