#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R623 收口件：DoD 面 4（上下文精排）读数的**派生 + 登记**机械件。

为什么需要它：四值读数由 C# 器具（`src/agent.tests/RerankFaceTests.cs`）落盘，但
「基准台账条目 + kpi 行」若靠手写 ⇒ 阈值来源与读数会随轮次漂移。本件把两者做成**幂等派生**：

  * 读 `eval/rover/r623/rerank-face-readings-fusion-k50.json`（唯一权威读数件）
  * 断言其判据(§criteria)全 true，否则 rc=2（器具/读数不成立，禁登记）
  * 幂等追加 `eval/capability/baselines.json` 的 `rerank-four` 条目（写前断言序列化器逐字节复现原文件）
  * 幂等追加 `eval/capability/kpi.jsonl` 的 R623 行（按 round 去重）
  * stdout 恒打 `CLOSEOUT_R623 rc=<n> ...` 机读行

用法: python3 eval/rover/r623/closeout_r623.py [--apply]
  无参 = 只读检查（打印将要写入的内容 + 现有条目是否存在），rc: 0 一致 / 2 读数或判据不成立 / 3 序列化器不复现
  --apply = 落盘追加（幂等）
"""
import hashlib
import io
import json
import pathlib
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
READ = ROOT / 'eval/rover/r623/rerank-face-readings-fusion-k50.json'
BAS = ROOT / 'eval/capability/baselines.json'
KPI = ROOT / 'eval/capability/kpi.jsonl'
REPORT = 'eval/rover/r623/report-r623.md'
PREREG = 'eval/rover/r623/prereg-r623.json'
PREREG2 = 'eval/rover/r623/prereg-r623-v2addendum.json'
BASE_ID = 'rerank-four'


def sha12(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]


def read_readings():
    d = json.loads(READ.read_text(encoding='utf-8'))
    crit = d.get('criteria') or {}
    bad = [k for k, v in crit.items() if (isinstance(v, bool) and not v)]
    if bad:
        print('CRITERIA_FAIL=' + ','.join(bad))
        return None, None
    rows = [r for r in d['per_query'] if r.get('gold_in_pool')]
    better = sum(1 for r in rows if r['T']['gold_rank'] < r['C']['gold_rank'])
    worse = sum(1 for r in rows if r['T']['gold_rank'] > r['C']['gold_rank'])
    same = len(rows) - better - worse
    mrr = lambda arm: sum(r[arm]['mrr'] for r in rows) / max(1, len(rows))
    val = {
        'gated_n': len(rows),
        'pool_k': d['pool_k'],
        'shape': d['shape'],
        'recall_at_N': round(d['telemetry']['gated_recall_at_N_eq_1'] / d['frozen']['n_queries'], 4),
        'ndcg10_median_T': round(d['aggregates']['T']['median_ndcg@10'], 4),
        'ndcg10_median_C': round(d['aggregates']['C']['median_ndcg@10'], 4),
        'mrr_median_T': round(d['aggregates']['T']['median_mrr'], 4),
        'mrr_mean_T': round(mrr('T'), 4),
        'mrr_mean_C': round(mrr('C'), 4),
        'paired_better': better, 'paired_worse': worse, 'paired_same': same,
        'rerank_applied_T': crit['P1_T_rerank_applied'],
        'rerank_applied_C': crit['P1_C_rerank_applied'],
        'swaps_positive_queries': crit['P1_T_swaps_positive_queries'],
        'pool_set_identical': d['telemetry']['pool_set_identical'],
        'pos_median_ndcg10': round(d['aggregates']['POS']['median_ndcg@10'], 4),
        'neg_median_ndcg10': round(d['aggregates']['NEG']['median_ndcg@10'], 4),
    }
    return d, val


def baseline_entry(val, read_sha12):
    return {
        'id': BASE_ID,
        'face': 'F_merge',
        'kind': 'contrast_arm',
        'metric': ('精排四值（NDCG@k / MRR / Precision@k / Recall@N），k=10，单 gold 分级（grade 2/0）；'
                   '聚合域 = Recall@N==1 的查询（gold 在召回池内）'),
        'unit': 'queries',
        'value': val,
        'threshold': (
            '① DoD 目标（RF0005 §0 面 4，**本轮未达标、不下调**）：NDCG@k ≥0.8 ∧ MRR ≥0.6 ∧ P@k ≥0.8 ∧ R@N =1.0；'
            '② 本基准可判门（有分辨率的形态）：变好查询数 ≥ 6（配对精确检验 p<0.05 反解 @n=90）∧ 变差查询数 = 0（零回归）∧ '
            'MRR 均值 ≥ 轴关臂（粗排 / 旧行为）；'
            '③ 分辨率外声明（禁据此下结论）：单 gold ⇒ P@k 上界 = 1/k（k≥2 时 ≥0.8 结构性不可达）；'
            '63/90 并列 ⇒ 中位数被钳制，禁以「中位持平」判精排无效；'
            '④ 补召回不在本面（精排只重排已召回池）⇒ R@N 只作前置天花板。'),
        'threshold_source': f'{PREREG} + {PREREG2}',
        'source_path': 'eval/rover/r623/rerank-face-readings-fusion-k50.json',
        'source_sha12': read_sha12,
        'ground_rule': ('唯一单变量轴 = RAGConfig.RerankEnabled（T=true 精排 / C=false 旧行为）；两侧共用同一召回池（pool_set_identical 断言）；'
                        '跨轮禁相减（与 R585–R622 冻结件轮只可并列）；'
                        '改器具（src/agent.tests/RerankFaceTests.cs）或重跑读数件（ts 变）⇒ 必须重取本 pin 并重钉；'
                        '形态必须为生产 DI（fusion：ServiceCollectionExtensions.cs:240），legacy 路只作诊断列。'),
        'check_cmd': ("python3 -c \"import io,json;d=json.load(io.open('eval/rover/r623/rerank-face-readings-fusion-k50.json'));"
                      "print(round(d['aggregates']['T']['median_ndcg@10'],4), round(d['aggregates']['C']['median_ndcg@10'],4))\""),
        'negative_control': ('① 轴关臂 = 旧行为（C：RerankApplied 必须恒 0，实测 0/120）；'
                             '② 退化打分器 NEG（-coarseScore）必须不优于 C（实测中位 NDCG@10 0.0 ≤ C 中位 0.5 + 0.02）；'
                             '③ oracle 置顶打分器 POS 必须近满分（实测 1.0）⇒ 度量对「把 gold 置顶」敏感；'
                             '④ 确定性 ∧ 非平凡成对：同二进制复跑 n=3 payload（去 ts）逐字节同一 ∧ 跨臂读数互异；'
                             '证据件 eval/rover/r623/report-r623.md §3/§4/§5。'),
    }


def append_baseline(entry, apply):
    raw = BAS.read_text(encoding='utf-8')
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL baselines.json 序列化器未逐字节复现 ⇒ 拒写 (fail-closed)')
        return 3
    ids = [e.get('id') for e in doc['entries']]
    if BASE_ID in ids:
        cur = doc['entries'][ids.index(BASE_ID)]
        same = json.dumps(cur, sort_keys=True, ensure_ascii=False) == json.dumps(entry, sort_keys=True, ensure_ascii=False)
        print('BASELINE_EXISTS=1 idempotent=%s' % same)
        return 0
    doc['entries'].append(entry)
    if not apply:
        print('BASELINE_APPEND=dry-run id=%s value=%s' % (BASE_ID, json.dumps(entry['value'], ensure_ascii=False)))
        return 0
    BAS.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    back = json.loads(BAS.read_text(encoding='utf-8'))
    got = [e for e in back['entries'] if e.get('id') == BASE_ID]
    print('BASELINE_APPEND=ok id=%s readback=%d' % (BASE_ID, len(got)))
    return 0


def append_kpi(val, apply):
    rows = [json.loads(l) for l in KPI.read_text(encoding='utf-8').splitlines() if l.strip()]
    if any(r.get('round') == 'R623' for r in rows):
        print('KPI_EXISTS=1 round=R623 (幂等)')
        return 0
    row = {
        'round': 'R623',
        'ts': datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z'),
        'kind': ('RF0005 §0 DoD **面 4 · 上下文精排**从「未测」推进为「有读数」（NDCG@k / MRR / Precision@k / Recall@N）+ 生效遥测。'
                 '零产品源码改动（既有开关 RAGConfig.RerankEnabled 单变量轴）/ 零远端调用 / 零新增夹具（复用 eval/bge/fixtures 冻结件）。'),
        'change': ('产品侧改动 = **零**。器具面 = 新增 `src/agent.tests/RerankFaceTests.cs`（产品真身路径 RAGRecall 上测四值 + 池同一性 + '
                   '两侧控制 + 先落盘后断言）+ `eval/rover/r623/{repro-r623.sh,closeout_r623.py}`。'
                   '首跑 v1（legacy 形态 × 池 10）与 v2a（池同一性判据写成 id 序列）两处**器具缺陷**原样入档、不翻案，修正形态单列 checks_posthoc。'),
        'readings': {
            'arms': 'T = 精排开（LexicalRerankScorer(0.5) 生产默认） / C = 轴关（旧行为，粗排序） / NEG = 退化打分器 / POS = oracle 置顶锚',
            'frozen': 'eval/bge/fixtures：语料 1299 篇 sha12 fa7c448c505d · 查询 120 条 sha12 b37fbe564e23（零新增夹具）',
            'rerank_four': val,
            'dod_threshold_verdict': 'NDCG@k ≥0.8 ✗（0.5）· MRR ≥0.6 ✗（中位 0.3333 / 均值 0.4929）· P@k ≥0.8 ✗（上界 1/k，结构性不可达）· R@N =1.0 ✗（0.75）',
            'determinism': '同二进制 --no-build 复跑 n=3：payload（去 ts）逐字节同一 sha12=9272c0b6da2d；非平凡性由跨臂互异保证',
            'unmeasured': 'tokens（调用数 / 新算 prompt / completion）与缓存命中率**未测**（本面零远端 / 零 LLM）',
        },
        'baselines': [BASE_ID],
        'prereg': f'{PREREG} + {PREREG2}（written_before_run=true）',
        'evidence': REPORT,
        'verdict': ('面 4 = **有读数（未达标）**。精排段接线通且真机生效（RerankApplied 120/120 · 错位 120/120）· 池集合逐条相同（120/120）· '
                    '配对 27 升 / 0 降 / 63 平（零回归）· MRR 均值 0.4772→0.4929（+0.0157, +3.3% rel）· rc=0（仅表本轮判据全绿）· 禁下调阈值'),
    }
    if not apply:
        print('KPI_APPEND=dry-run round=R623 baselines=%s' % row['baselines'])
        return 0
    with io.open(KPI, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    back = [json.loads(l) for l in KPI.read_text(encoding='utf-8').splitlines() if l.strip()]
    print('KPI_APPEND=ok lines=%d round=R623 count=%d' % (len(back), sum(1 for r in back if r.get('round') == 'R623')))
    return 0


def main():
    apply = '--apply' in sys.argv
    d, val = read_readings()
    if d is None:
        print('CLOSEOUT_R623 rc=2 读数判据未全绿 ⇒ 禁登记')
        return 2
    rc = append_baseline(baseline_entry(val, sha12(READ)), apply)
    if rc:
        return rc
    rc = append_kpi(val, apply)
    print('CLOSEOUT_R623 rc=%d apply=%s read_sha12=%s' % (rc, apply, sha12(READ)))
    return rc


if __name__ == '__main__':
    sys.exit(main())
