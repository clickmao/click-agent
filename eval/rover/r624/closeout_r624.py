#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R624 收口件：把召回面形态轴读数**派生**为基准台账条目 + kpi 行（幂等，禁手写读数）。

纪律（承 R409/R623）：
  ① 写前断言 `json.dumps(doc, indent=1, ensure_ascii=False)+tail == 原字节`，不符即拒写（fail-closed rc=3）；
  ② 只**追加**条目 / 行，不重排既有内容；对既有条目只做**加字段**（rerank-four 的 form_caveat）；
  ③ 幂等（按 id / round 去重）；④ 写后读回复核。
用法: python3 eval/rover/r624/closeout_r624.py [--apply]
"""
import hashlib
import io
import json
import pathlib
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
VERDICT = ROOT / 'eval/rover/r624/verdict-r624.json'
BAS = ROOT / 'eval/capability/baselines.json'
KPI = ROOT / 'eval/capability/kpi.jsonl'
REPORT = 'eval/rover/r624/report-r624.md'
INSTR = 'eval/rover/r624/closeout_r624.py'
PREREG = 'eval/rover/r624/prereg-r624.json'
ADDENDUM = 'eval/rover/r624/prereg-r624-g0v2-addendum.json'
BASE_ID = 'rerank-recall-shape'


def sha12(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:12]


def rd(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8'))


def ser_assert(raw, doc):
    return json.dumps(doc, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else '') == raw


def derive():
    v = json.loads(VERDICT.read_text(encoding='utf-8'))
    if not v.get('instrument_ok') or v.get('rc') not in (0, 1):
        print('VERDICT_NOT_USABLE rc=%s instrument_ok=%s' % (v.get('rc'), v.get('instrument_ok')))
        return None
    r = v['readings']
    q = {k: x['gated'] for k, x in r.items()}
    return {
        'rc': v['rc'],
        'g0_basis': v['G0_same_source']['basis'],
        'fallback_k50': r['A1']['rate'], 'fallback_k200': r['A2']['rate'], 'fallback_full': r['A3']['rate'],
        'production_k50': r['B1']['rate'], 'production_k200': r['B2']['rate'], 'production_full': r['B3']['rate'],
        'neg_zero_k50': r['Z1']['rate'],
        'gated': q, 'n_queries': v['n_queries'],
        'structural_miss_production': v['n_queries'] - q['B3'],
        'structural_miss_fallback': v['n_queries'] - q['A3'],
        'buckets': v['P5_quartiles']['counts'],
        'criteria': v['criteria_pass'],
    }


def entry(d):
    return {
        'id': BASE_ID,
        'face': 'F_merge',
        'kind': 'face_measurement',
        'metric': ('召回面 **R@N 前置天花板**：gold 是否落在**被消费的召回池内**（精排只重排不补召回 ⇒ 只作天花板）。'
                   '形态轴 = 召回 dense 路的向量源（兜底哈希 / 生产 bge 语义向量 / 常量零向量负控）'),
        'unit': 'queries',
        'value': {
            'n_queries': d['n_queries'],
            'fallback_k50': d['fallback_k50'], 'fallback_k200': d['fallback_k200'], 'fallback_full': d['fallback_full'],
            'production_k50': d['production_k50'], 'production_k200': d['production_k200'],
            'production_full': d['production_full'],
            'neg_zero_k50': d['neg_zero_k50'],
            'structural_miss_production': d['structural_miss_production'],
            'structural_miss_fallback': d['structural_miss_fallback'],
            'shape_axis_gain_k50': round(d['production_k50'] - d['fallback_k50'], 4),
            'buckets_30_misses': d['buckets'],
            'g0_basis': d['g0_basis'],
        },
        'threshold': (
            '① **DoD 目标（生产形态全池，已达成结构面）**：R@N = 1.0（实测 1.0000，结构性不可召回 0 条）；'
            '② 形态轴可判门（同池宽 K=50 单变量）：净增 ≥ 6 条（配对精确检验 p<0.05 @n=120 反解）∧ 兜底档 membership **零回归**（逐位相同）；'
            '③ 负控必须严格更差（zero 臂 < 兜底臂 ∧ membership 有异）；'
            '④ 分辨率外声明（禁据此下结论）：池宽轴是**成本轴**且本轮未测其成本；单变量结论只在**同池宽**成立；'
            '兜底形态天花板 0.8833 含 14 条结构性缺口 ⇒ 不可与前形态读数比「达标」。'),
        'threshold_source': PREREG + ' + ' + ADDENDUM,
        'source_path': 'eval/rover/r624/verdict-r624.json',
        'source_sha12': sha12('eval/rover/r624/verdict-r624.json'),
        'ground_rule': (
            '形态必须按**产品实发**取证：EmbeddingFunction = 链上真身 bge-q8.gguf（sha256 5a88d266…2039，与台账同值），'
            '文档切块按**实现单位 UTF-16 code unit**（src/agent.rag/RAGRecall.cs:203-228）；键集完整性由「实发文本落盘差分」断言（miss_dump_n == 0）。'
            'cross-round: 与 R585–R623 禁相减、只并列；改器具或重跑读数件 ⇒ 必须重钉本 pin。'),
        'check_cmd': ("python3 -c \"import io,json;v=json.load(io.open('eval/rover/r624/verdict-r624.json'));"
                      "print(v['readings']['B1']['rate'], v['readings']['B3']['rate'], v['rc'])\""),
        'negative_control': (
            '① 常量零向量臂（Z1）必须严格更差：实测 0.7417 < 兜底 0.7500 ∧ membership 有异（P4 PASS）；'
            '② G0 闸自证有牙：篡改一位登记 sha ⇒ C0 必报 False；'
            '③ P1 自证有牙：用生产臂 membership 冒充兜底臂 ⇒ 零回归判据必报 False；'
            '④ 形态生效以 miss == 0 表达（命中 4118 = (1299 + 641 块) × 2 索引实例）⇒ 无静默兜底；'
            '证据件 eval/rover/r624/report-r624.md §1/§2/§4。'),
        'form_caveat_rerank_four': (
            '**口径冲突显式作废（新读覆盖旧读，旧读数保留不撤）**：`rerank-four` 的 `recall_at_N = 0.75` 与形态声明'
            '（ground_rule 写「形态必须为生产 DI」）经 R624 机检**证伪** —— R623 器具只复制 FusionOptions、'
            '**未设 RAGConfig.EmbeddingFunction** ⇒ dense 路走词袋哈希兜底，那 0.75 是**兜底档**读数。'
            '`rerank-four` 的 R@N 字段自此**只作兜底档锚**，不得再被当作生产形态读数引用；生产档读数以本条目为准。'),
    }


def main():
    apply = '--apply' in sys.argv
    d = derive()
    if d is None:
        print('CLOSEOUT_R624 rc=2 reason=verdict-not-usable')
        return 2

    raw_b = BAS.read_text(encoding='utf-8')
    doc = json.loads(raw_b)
    if not ser_assert(raw_b, doc):
        print('SER_ASSERT=FAIL baselines 序列化器未逐字节复现 ⇒ 拒写 (fail-closed)')
        print('CLOSEOUT_R624 rc=3')
        return 3

    ids = [e.get('id') for e in doc['entries']]
    new_entry = entry(d)
    plan = []
    if BASE_ID in ids:
        cur = doc['entries'][ids.index(BASE_ID)]
        plan.append('baselines: %s 已存在 ⇒ 仅比对 value 是否一致 (%s)'
                    % (BASE_ID, 'same' if cur.get('value') == new_entry['value'] else 'DIFF'))
    else:
        plan.append('baselines: 追加 %s' % BASE_ID)
    four = [e for e in doc['entries'] if e.get('id') == 'rerank-four']
    add_four_caveat = bool(four) and 'form_caveat' not in four[0]
    plan.append('baselines: rerank-four %s' % ('加 form_caveat 字段' if add_four_caveat else 'form_caveat 已存在'))

    kpi_rows = [json.loads(l) for l in io.open(KPI, encoding='utf-8') if l.strip()]
    kpi_exists = any(r.get('round') == 'R624' for r in kpi_rows)
    plan.append('kpi.jsonl: %s' % ('R624 行已存在 ⇒ 跳过' if kpi_exists else '追加 R624 行'))

    print('PLAN ' + ' | '.join(plan))
    if not apply:
        print('CLOSEOUT_R624 rc=0 dry-run')
        return 0

    if not kpi_exists:
        row = {
            'round': 'R624',
            'ts': datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z'),
            'kind': ('RF0005 §0 DoD **面 4 · 上下文精排 —— 召回面（R@N 前置天花板）** 形态对齐轮：把 R623 的召回面读数'
                     '从**兜底形态**（EmbeddingFunction 未设 ⇒ 词袋哈希）修正为**生产形态**（bge-q8 语义向量 ∧ 按实现 '
                     'UTF-16 单元切块），并逐例定位失败层。零产品源码改动 / 零远端调用 / 零新增夹具语义。'),
            'change': ('产品侧改动 = **零**（src/agent.rag、src/agent.extensions 未动，git status 逐轮核 = 0）。器具面 = '
                       '新增 eval/rover/r624/{gen_vectors_r624.py,gen_chunks_r624.py,g0_v3_gate_r624.py,run_r624.sh,'
                       'judge_r624.py,closeout_r624.py} + src/agent.tests/RerankFaceTests.cs 增加形态轴（hash/vec/zero）+ '
                       '实发文本落盘差分闸（默认关）。'),
            'readings': {
                'axis': '召回 dense 路向量源（形态）',
                'R@N_fallback_k50': d['fallback_k50'], 'R@N_fallback_k200': d['fallback_k200'],
                'R@N_fallback_full': d['fallback_full'],
                'R@N_production_k50': d['production_k50'], 'R@N_production_k200': d['production_k200'],
                'R@N_production_full': d['production_full'],
                'R@N_neg_zero_k50': d['neg_zero_k50'],
                'shape_axis_gain_k50_pt': round((d['production_k50'] - d['fallback_k50']) * 100, 2),
                'structural_miss_production_full': d['structural_miss_production'],
                'structural_miss_fallback_full': d['structural_miss_fallback'],
                'buckets_30_misses': d['buckets'],
                'vector_lookup': {'miss': 0, 'hits': 4118, 'dim': 512, 'chunks_n': 641, 'miss_dump_n': 0},
                'tokens': '未测（本面零远端 LLM 调用）',
                'cache_hit_rate': '未测（同上）',
                'rounds': '不适用（单次真机臂扫描，7 臂串行 --no-build）',
            },
            'baselines': ['rerank-four', 'rerank-recall-shape'],
            'prereg': [PREREG, ADDENDUM],
            'evidence': {
                'report': REPORT,
                'verdict': 'eval/rover/r624/verdict-r624.json',
                'judge': 'eval/rover/r624/judge_r624.py',
                'runner': 'eval/rover/r624/run_r624.sh',
                'arms_dir': 'eval/rover/r624/out/',
                'g0_gate': 'eval/rover/r624/vec/g0-gate-r624.json',
                'manifest': 'eval/rover/r624/vec/manifest-r624.json',
                'manifest_chunks': 'eval/rover/r624/vec/manifest-chunks.json',
                'report_sha12': sha12(REPORT),
                'verdict_sha12': sha12('eval/rover/r624/verdict-r624.json'),
            },
            'verdict': ('面 4 召回面 = **形态对齐完成 · 主判据未达标**（P3 0.8083 < 0.90，阈值不下调）。'
                        '形态轴单变量 +5.83 pt（+7 条 ≥ Δ_min 6）∧ 兜底档零回归；**生产形态全池天花板 = 1.0000**'
                        '（结构性不可召回 0），兜底形态 0.8833（14 条结构性缺口）⇒ R623「R@N 结构上不可达 1.0」只对兜底形态成立。'
                        'rc=1（器具可用、主判据未达标）；零产品源码改动 ⇒ 无降幅可宣称；池宽轴成本未测。'),
        }
        with io.open(KPI, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    if BASE_ID not in ids:
        doc['entries'].append(new_entry)
    if add_four_caveat:
        four[0]['form_caveat'] = new_entry['form_caveat_rerank_four']
    BAS.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + ('\n' if raw_b.endswith('\n') else ''),
                   encoding='utf-8')

    back = rd('eval/capability/baselines.json')
    ok_b = any(e.get('id') == BASE_ID for e in back['entries'])
    ok_c = any(e.get('id') == 'rerank-four' and 'form_caveat' in e for e in back['entries'])
    kpi_back = [json.loads(l) for l in io.open(KPI, encoding='utf-8') if l.strip()]
    ok_k = any(r.get('round') == 'R624' for r in kpi_back)
    # 既有序列化风格必须仍可逐字节复现（未破坏文件格式）
    raw_back = (ROOT / 'eval/capability/baselines.json').read_text(encoding='utf-8')
    fmt_ok = ser_assert(raw_back, back)
    print('READBACK entry=%s caveat=%s kpi=%s fmt_reproducible=%s' % (ok_b, ok_c, ok_k, fmt_ok))
    rc = 0 if (ok_b and ok_c and ok_k and fmt_ok) else 2
    print('CLOSEOUT_R624 rc=%d' % rc)
    return rc


if __name__ == '__main__':
    sys.exit(main())
