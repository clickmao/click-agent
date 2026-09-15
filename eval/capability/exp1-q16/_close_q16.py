#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q16 收口：① 计划文档追加「附录 Q」（幂等 + 文本追加，不重排整档）；② kpi.jsonl 追加一行（幂等）+ 读回校验。"""
import json, pathlib, subprocess, datetime, hashlib, sys

DOC = pathlib.Path('docs/plans/v0.22.0-exp1-local-index-and-code-graph.md')
KPI = pathlib.Path('eval/capability/kpi.jsonl')
TS = datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')

APPENDIX = pathlib.Path('eval/capability/exp1-q16/appendix_q.md').read_text(encoding='utf-8')

# --- ① 附录 Q ---
doc = DOC.read_text(encoding='utf-8')
if '## 附录 Q ·' in doc:
    print('APPENDIX_Q_ALREADY_PRESENT')
else:
    if not doc.endswith('\n'):
        doc += '\n'
    DOC.write_text(doc + APPENDIX, encoding='utf-8')
    back = DOC.read_text(encoding='utf-8')
    assert '## 附录 Q ·' in back, '附录 Q 写入未生效'
    assert back.startswith(doc), '前置内容被改动（应纯追加）'
    print(f'APPENDIX_Q_APPENDED: +{len(APPENDIX)} chars; total={len(back)}')

# --- ② kpi.jsonl ---
sha = hashlib.sha256(pathlib.Path('eval/capability/exp1-q16/unit_axis_guard.py').read_bytes()).hexdigest()
line = {
    'round': 'EXP1-Q16', 'ts': TS, 'kind': 'instrument-invariant(exp1-L.8候选③)',
    'artifact': 'eval/capability/exp1-q16/{prereg_q16.json,unit_axis_guard.py,verdict_q16.json,'
                'evidence_q16.txt,zeroregress_q16.json,selftest_q16.json,selftest_q16.log,run_q16.log,'
                'run_q16_v11_preclassify.log,diag_face_rungs.txt}; '
                'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md 附录Q',
    'change': 'L.8 候选③ 只推进一步 = 「循环累加型计数」由笼统不可重放升级为三分：①嵌套累加（外层绑定链）真重放；'
              '②残余落**类型化原因**（闭集 5 条 + 归不进即上抛 fail-closed）；③C1 比较层分离「重放面为空（口径边界）」'
              '与「值不等（硬 mismatch）」。v1.0→v1.3 全在器具侧（probe_v260.py v2.6.0 一字未动）；夹具 10→14 格。'
              '未改 src/、skills/、docs/verification-registry.json、eval/capability/instruments.json、eval/rover/；零 dotnet。',
    'readings': {
        'instrument': f'unit_axis_guard.py v1.3 (EXP1-Q16) sha256={sha[:16]}',
        'zero_regression': {
            'probe_stdout.json': {'exit': '2→2', 'C1_checked': '7→7', 'all_equal': True,
                                  'findings': 'C3=1, C7=1', 'axes_domains_same': True},
            'attribution_q10.json': {'exit': '2→2', 'C1_checked': '10→12', 'C1_all_equal': True,
                                     'C1_n_boundary': 2, 'findings': 'C3=1, C4=3, C7=1',
                                     'axes_domains_same': True}},
        'typed_reasons': {'symbol_face_rungs': 'ARCHIVE_FACE_FIELD_ABSENT',
                          'n_symbol_faces': 'ARCHIVE_FACE_FIELD_ABSENT',
                          'symbol_occurrences': 'PARAM_SCOPE',
                          'stale_like_n': 'SELF_REFERENTIAL_CROSS_ARTIFACT'},
        'boundary_evidence': {'artifact': 'citations.jsonl', 'n_rows': 928,
                              'field_presence': {'symbol_faces': 0},
                              'missing_fields': ['symbol_faces']},
        'untyped_skips': 0,
        'fixtures': {'n_cases': 14, 'n_pass': 14, 'exit': 0,
                     'new': ['FX11_nested_loop_replay', 'FX12_nested_loop_registered_corrupted',
                             'FX14_archive_face_field_absent', 'FX13_untyped_skip_fail_closed']},
        'determinism': {'two_runs_byte_identical': True,
                        'verdict_sha256': '674bb15292e1e11218960bf84ab6cd7aa0b95151e16c586ff9dc6706f103a812'},
        'prereg_verdicts': {'P1_C1_10_to_12': True, 'P2_bitwise_equal': False,
                            'P3_4_to_2_typed': 'count=False(4→4)/quality=True(0 无类型)',
                            'P5_zero_regression': True, 'P6_fixtures': True, 'P7_determinism': True},
    },
    'criterion': 'C11 每个被跳过键必须有闭集内类型化原因（无类型 ⇒ 不上抛即失败）| C1 边界单列 n_boundary 不计入 all_equal '
                 '| FX12 字段在场时值不等仍硬红（边界 ≠ 值不等的判别力）| FX13 非累加型不可解析必须 fail-closed',
    'evidence_level': 'L1-static（真归档语料 928 行 + 真源码 AST 派生 + 14 格夹具 + 两跑逐字节；无编译/测试/AOT ⇒ 不报 L3/L4）',
    'honest': '① 预注册 P2「两键重放值与登记逐位相同」**被否证**（两键只被 C1 达到，随即落口径边界）⇒ 宣称收窄为'
              '「达到面 10→12 且 2 项单列边界」+「4 键全部类型化、零无类型跳过」，**不得**宣称两键已逐位对账。'
              '② 本轮最有价值发现：登记读数 n_symbol_faces=575 / symbol_face_rungs 所计数的字段 `symbol_faces` 在归档语料'
              '928 行中出现 0 次 ⇒ 外部审计者拿归档无法复算该读数（判据可达面 < 语料面，第五型）；归因（落盘丢字段 vs 后填）'
              '与修法**本轮不做**，只落类型化原因与证据。'
              '③ 嵌套累加能力由夹具证明（FX11/FX12/FX14），不得据此宣称真语料可对账。'
              '④ v1.1 首跑抛 MEASUREMENT_FAILURE 的原始日志留档（两类原因被并成一类=测量层归并缺陷），'
              'v1.2/v1.3 属修正而非调参放行（预注册判据未改）。'
              '⑤ 形式校验 10/10 **结转**（对侧 R455 套件真跑中 + 内存闸）；本轮改动面 = eval/capability/exp1-q16/ 新增 + 附录 Q，影响面零。',
    'debt': '(1) 「归档缺字段」归因判定（落盘块字段集 vs judge 返回字段集）| (2) L2 器具登记（对侧空闲 + 全量面复跑）'
            '| (3) 形式校验 10/10 绿仍结转 | (4) 阶段 B 可配语言集（独立预注册轮次）| (5) 对侧 r415 fake_llama 桩孤儿进程仅登记未清',
    'next': 'L.8 剩余候选：①「归档缺字段」归因判定（最前未完成项）→ ② L2 器具登记 → ③ L.7 #4 阈值噪声带/先收尾再读闸落仪器 '
            '→ ④ 阶段 B 独立预注册轮次。',
    'owner_round': 'EXP1-Q16(60m 自检作业; 不占主线轮号)',
    'covers': ['eval/capability/exp1-q16/prereg_q16.json', 'eval/capability/exp1-q16/unit_axis_guard.py',
               'eval/capability/exp1-q16/verdict_q16.json', 'eval/capability/exp1-q16/evidence_q16.txt',
               'eval/capability/exp1-q16/zeroregress_q16.json', 'eval/capability/exp1-q16/selftest_q16.json',
               'eval/capability/exp1-q16/appendix_q.md',
               'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md'],
    'negative_control': 'FX12（同夹具、字段在归档面内、登记值 +1）⇒ 必 exit 3 硬红（证明边界豁免不是放行口袋）；'
                        'FX13（非累加型 + 过滤引用未定义名）⇒ 必 exit 3 fail-closed；'
                        'FX8（缺输入）⇒ exit 3；FX14（字段全缺）⇒ exit 0 且类型化原因可读；'
                        'FX1/FX10（合法，其中 FX10 命名与域与真文件不同）⇒ 零误杀。',
}

raw = KPI.read_bytes()
if b'"EXP1-Q16"' in raw:
    print('KPI_Q16_ALREADY_PRESENT')
else:
    with KPI.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + '\n')
    print('KPI_Q16_APPENDED')

# --- 读回校验（不只信写回执）---
back = KPI.read_text(encoding='utf-8').splitlines()
last = json.loads(back[-1])
assert last['round'] == 'EXP1-Q16', last.get('round')
assert last['readings']['typed_reasons']['symbol_face_rungs'] == 'ARCHIVE_FACE_FIELD_ABSENT'
assert last['readings']['untyped_skips'] == 0
print(f'KPI_READBACK_OK lines={len(back)} last_round={last["round"]} ts={last["ts"]}')
print(f'JSONL_LINES_ALL_PARSE_OK={all(json.loads(l) for l in back if l.strip())}')
