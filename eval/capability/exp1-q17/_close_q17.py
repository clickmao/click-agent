#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q17 收口：① 生成 evidence_q17.txt（由 verdict JSON 机械派生，手上不抄数字）；
② 计划文档追加「附录 R」（幂等 + 纯文本追加，不重排整档）；③ kpi.jsonl 追加一行（幂等）+ 读回校验。"""
import json, pathlib, datetime, hashlib, sys

DOC = pathlib.Path('docs/plans/v0.22.0-exp1-local-index-and-code-graph.md')
KPI = pathlib.Path('eval/capability/kpi.jsonl')
D = pathlib.Path('eval/capability/exp1-q17')
TS = datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')

verdict = json.loads((D / 'verdict_q17.json').read_text(encoding='utf-8'))
fixtures = json.loads((D / 'selftest_q17.json').read_text(encoding='utf-8'))
r = verdict['readings']

# --- ① evidence 派生（全部数字来自 verdict JSON，不手抄）---
lines = []
A = lines.append
A('EXP1-Q17 evidence — 「归档缺字段」归因判定 (archive_field_provenance.py v1.0)')
A(f"generated: {verdict['generated']}  elapsed_s={verdict['elapsed_s']}  exit={verdict['exit_code']}")
A('')
A('## 复现命令')
A('  python3 eval/capability/exp1-q17/archive_field_provenance.py --selftest --determinism \\')
A('      --out eval/capability/exp1-q17/verdict_q17.json \\')
A('      --fixtures-out eval/capability/exp1-q17/selftest_q17.json | tee eval/capability/exp1-q17/run_q17.log')
A('')
A('## 输入指纹')
for k in ('probe', 'archive', 'registered', 'q16_verdict'):
    A(f"  {k:14s} = {verdict['inputs'][k]}")
A(f"  probe_sha256   = {verdict['inputs']['probe_sha256']}")
A(f"  archive_sha256 = {verdict['inputs']['archive_sha256']}")
A('')
A('## 读数')
for k in ('archive_rows', 'archive_bad_lines', 'archive_key_count', 'rows_with_symbol_faces',
          'domain_live_from_archive', 'domain_edge_field_rows',
          'P_size', 'P1_size', 'P2_size', 'P3_size', 'D_size', 'A_size',
          'universe_size', 'class_conserved_sum', 'early_returns_before_face_assign',
          'face_field_class', 'relocated_face_field_class', 'not_replayable_total'):
    A(f"  {k:34s} = {r[k]}")
A(f"  class_distribution               = {json.dumps(r['class_distribution'], ensure_ascii=False)}")
A(f"  omitted_fields({len(r['omitted_fields'])})            = {json.dumps(r['omitted_fields'], ensure_ascii=False)}")
A(f"  branch_unhit_fields              = {json.dumps(r['branch_unhit_fields'], ensure_ascii=False)}")
A(f"  all_face_dependent_result_keys   = {json.dumps(r['all_face_dependent_result_keys'], ensure_ascii=False)}")
A(f"  face_unblocked_nonreplayable     = {json.dumps(r['face_unblocked_nonreplayable'], ensure_ascii=False)}")
A(f"  not_replayable_typed             = {json.dumps(r['not_replayable_typed'], ensure_ascii=False)}")
A('')
A('## 归因')
A(f"  {r['attribution']}")
A('')
A('## 分类明细（逐键 → 类）')
for k, c in sorted(verdict['readings'].get('class_by_key', {}).items()):
    A(f"  {c:30s} {k}")
A('')
A('## 检查')
for c in verdict['checks']:
    A(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['id']:4s} {'(posthoc)' if c.get('posthoc') else '        '} {c['claim']}")
    A(f"          {c['detail']}")
A('')
A('## 夹具')
for f in fixtures:
    A(f"  [{'PASS' if f['passed'] else 'FAIL'}] {f['id']:5s} {f['claim']} | {f['detail']}")
A('')
A('## 确定性')
A(f"  two_runs_identical = {verdict['determinism']['identical']}  sha_a={verdict['determinism']['sha_a']}")
A(f"  sha_b={verdict['determinism']['sha_b']}")
A('')
A('## 零回归')
A(f"  {json.dumps([c['detail'] for c in verdict['checks'] if c['id'] == 'C14'][0], ensure_ascii=False)}")
A('')
(D / 'evidence_q17.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f"EVIDENCE_WRITTEN lines={len(lines)} bytes={(D / 'evidence_q17.txt').stat().st_size}")

# --- ② 附录 R ---
APPENDIX = (D / 'appendix_r.md').read_text(encoding='utf-8')
doc = DOC.read_text(encoding='utf-8')
if '## 附录 R ·' in doc:
    print('APPENDIX_R_ALREADY_PRESENT')
else:
    before = doc
    if not doc.endswith('\n'):
        doc += '\n'
    DOC.write_text(doc + APPENDIX, encoding='utf-8')
    back = DOC.read_text(encoding='utf-8')
    assert '## 附录 R ·' in back, '附录 R 写入未生效'
    assert back.startswith(before), '前置内容被改动（应纯追加）'
    print(f'APPENDIX_R_APPENDED: +{len(APPENDIX)} chars; total={len(back)}')

# --- ③ kpi.jsonl ---
sha = hashlib.sha256((D / 'archive_field_provenance.py').read_bytes()).hexdigest()
line = {
    'round': 'EXP1-Q17', 'ts': TS, 'kind': 'attribution(exp1-L.8候选①)',
    'artifact': 'eval/capability/exp1-q17/{prereg_q17.json,archive_field_provenance.py,verdict_q17.json,'
                'selftest_q17.json,evidence_q17.txt,run_q17.log}; '
                'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md 附录R',
    'change': 'L.8 候选① 只推进一步 = 「归档缺字段」归因判死：AST 派生 生产者(P=35)/落盘白名单(D=26)/归档(A=24) '
              '三集合 → MECE 五分类（含守恒式 Σ==|P∪D∪A|）⇒ 归因 = ① 落盘块丢字段（白名单漏 9 枚生产者字段，'
              '由 `if k in c` 静默丢弃），② 被否证。器具新建 archive_field_provenance.py v1.0；'
              '未改 src/、skills/、docs/verification-registry.json、eval/capability/instruments.json、eval/rover/、'
              'probe_v260.py；零 dotnet。',
    'readings': {
        'attribution': r['attribution'],
        'class_distribution': r['class_distribution'],
        'class_conserved_sum': r['class_conserved_sum'], 'universe_size': r['universe_size'],
        'set_sizes': {'P': r['P_size'], 'P1': r['P1_size'], 'P2': r['P2_size'], 'P3': r['P3_size'],
                      'D': r['D_size'], 'A': r['A_size']},
        'rows_with_symbol_faces': r['rows_with_symbol_faces'],
        'domain': {'archive_rows': r['archive_rows'], 'live_from_archive': r['domain_live_from_archive'],
                   'edge_field_rows': r['domain_edge_field_rows']},
        'omitted_fields': r['omitted_fields'],
        'branch_unhit_fields': r['branch_unhit_fields'],
        'early_returns_before_face_assign': r['early_returns_before_face_assign'],
        'replay_unblocked': {'face_dependent_registered_keys': r['face_dependent_registered_keys'],
                             'not_replayable_total': r['not_replayable_total'],
                             'unblocked_nonreplayable': r['face_unblocked_nonreplayable'],
                             'claim': '4 -> 2（symbol_face_rungs, n_symbol_faces）'},
        'fixtures': {'n_cases': len(fixtures), 'n_pass': sum(1 for f in fixtures if f['passed']),
                     'exit': verdict['exit_code']},
        'checks': {'n_pass': sum(1 for c in verdict['checks'] if c['passed']), 'n_total': len(verdict['checks'])},
        'determinism': {'identical': verdict['determinism']['identical'],
                        'sha256_a': verdict['determinism']['sha_a']},
        'zero_regression': {'probe_sha256': verdict['inputs']['probe_sha256'],
                            'archive_sha256': verdict['inputs']['archive_sha256']},
    },
    'criterion': 'C4/C5 class(symbol_faces)==C_producer_dump_omission ⇒ 归因① | C10 Σ classes == |P∪D∪A| '
                 '| C6 `if k in c` 守卫在场（静默丢弃机制）| C9 解除面 = 依赖 face 字段 ∩ Q16 not_replayable(4) '
                 '== {symbol_face_rungs, n_symbol_faces} ⇒ 4→2 | FX15 去枢纽规则必使依赖面变宽（28→6，规则承重）',
    'evidence_level': 'L1-static（真源码 AST 派生 + 真归档 945 行/928 live 域 + 15 格夹具 + 两跑逐字节；'
                      '无编译/测试/AOT ⇒ 不报 L3/L4）',
    'honest': '① 本轮只判因不修：把漏字段补进白名单会改变归档可比性（需重跑探针重刷归档）⇒ 独立预注册轮次，'
              '零产品改动。② 9 枚漏字段中**仅 2 枚**被登记读数派生链消费（face 家族），其余 7 枚（raw/pos_start/'
              'pos_end/block_id/path_exists/relocated_lines_ok/relocated_symbols_absent）**不影响任何已登记读数** ⇒ '
              '不得宣称「整体可重放面提升」。③ 器具自曝 4 处缺陷（universe 不含 A 致外来键静默丢弃；flow_deps 经循环'
              '变量枢纽传播致 15 键伪依赖；DictComp key 判定恒假；with_name 链上定位失败），全部由自检/首跑抓出，'
              '残 1 处夹具设计缺陷原位修正。④ 形式校验（VerificationForm|SkillGeneralization|DevPlanDocRef）**结转**：'
              '对侧 R458 AOT publish+ilc 真跑在场，MemAvailable 1441MB < 起手闸 2650MB。',
    'debt': '(1) 落地修法（白名单补 face 字段 + 重跑探针 + 独立复算断言）| (2) L2 器具登记（对侧空闲 + 全量面复跑）'
            '| (3) 形式校验 10/10 结转清账 | (4) 阶段 B 可配语言集（独立预注册轮次）',
    'next': 'L.8 剩余候选：① 落地修法（补白名单 → 归档可独立复算 face 读数，非重放 4→2）→ ② L2 器具登记 → '
            '③ 形式校验结转清账 → ④ 阶段 B 独立预注册轮次。',
    'owner_round': 'EXP1-Q17(60m 自检作业; 不占主线轮号)',
    'covers': ['eval/capability/exp1-q17/prereg_q17.json',
               'eval/capability/exp1-q17/archive_field_provenance.py',
               'eval/capability/exp1-q17/verdict_q17.json',
               'eval/capability/exp1-q17/selftest_q17.json',
               'eval/capability/exp1-q17/evidence_q17.txt',
               'eval/capability/exp1-q17/appendix_r.md',
               'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md'],
    'negative_control': 'FX04（白名单+归档同时补 face ⇒ 类 5，证明两侧读数都真读）| FX05（只改白名单 + 真归档 ⇒ '
                        '离开类 4，证明 D 取自源码而非硬编码）| FX06（白名单插从不产出键 ⇒ 类 2）| FX07（归档插外来键 ⇒ '
                        '类 1）| FX08（归档缺条件分支字段 ⇒ 类 3）| FX10/FX11/FX12（归档缺失/空/源码缺函数 ⇒ 弃权 exit 3，'
                        '缺输入不判红）| FX15（去枢纽规则 ⇒ 依赖面 6→28 变宽）。',
}

raw = KPI.read_bytes()
if b'"EXP1-Q17"' in raw:
    print('KPI_Q17_ALREADY_PRESENT')
else:
    with KPI.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + '\n')
    print('KPI_Q17_APPENDED')

# --- 读回校验（不只信写回执）---
back = KPI.read_text(encoding='utf-8').splitlines()
last = json.loads(back[-1])
assert last['round'] == 'EXP1-Q17', last.get('round')
assert last['readings']['rows_with_symbol_faces'] == 0
assert last['readings']['attribution'].startswith('①')
assert last['readings']['replay_unblocked']['unblocked_nonreplayable'] == ['n_symbol_faces', 'symbol_face_rungs']
assert last['readings']['fixtures']['n_pass'] == last['readings']['fixtures']['n_cases']
doc_back = DOC.read_text(encoding='utf-8')
assert '## 附录 R ·' in doc_back
print(f'KPI_READBACK_OK lines={len(back)} last_round={last["round"]} ts={last["ts"]}')
print(f'DOC_READBACK_OK appendix_R={doc_back.count("## 附录 R ·")} total_chars={len(doc_back)}')
print(f'JSONL_LINES_ALL_PARSE_OK={all(json.loads(l) for l in back if l.strip())}')
print(f'INSTRUMENT_SHA256={sha}')
