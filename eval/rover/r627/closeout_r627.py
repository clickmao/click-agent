#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R627 收口件：把「器具面判据形态修法」读数**派生**为 baselines 条目 + registry 行 + kpi 行 + 收口读回。

纪律（承 R409/R623/R624/R625/R626）：
  ① 写前断言 `json.dumps(doc, indent=1, ensure_ascii=False)(+tail) == 原字节`，不符即拒写（fail-closed rc=3）；
  ② 只**追加**条目 / 行，不重排既有内容；③ 幂等（按 id / round 去重）；
  ④ 写后读回复核，并断言 `artifact_sha12 == sha12(evidence_path)`（该等式曾两次误钉 ⇒ 机检必过）。
用法: python3 eval/rover/r627/closeout_r627.py [--apply]
"""
import hashlib
import io
import json
import pathlib
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
VERDICT = ROOT / 'eval/rover/r627/verdict-r627.json'
ORACLE = ROOT / 'eval/rover/r627/oracle-r627.json'
POSTHOC = ROOT / 'eval/rover/r627/posthoc-r627.json'
BAS = ROOT / 'eval/capability/baselines.json'
KPI = ROOT / 'eval/capability/kpi.jsonl'
REG = ROOT / 'docs/verification-registry.json'
LEDGER = ROOT / 'docs/research/lit-review-ledger.md'
REPORT = 'eval/rover/r627/report-r627.md'
INSTR = 'eval/rover/r627/closeout_r627.py'
PREREG = 'eval/rover/r627/prereg-r627.json'
BASE_ID = 'rerank-oracle-form'
ROW_ID = 'r627.rerank-instrument-form'


def sha12(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:12]


def ser_assert(raw, doc, tag):
    got = json.dumps(doc, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else '')
    if got != raw:
        print('SER_MISMATCH %s ⇒ 拒写（改用文本插入，禁静默重排）' % tag)
        return False
    return True


def derive():
    v = json.loads(VERDICT.read_text(encoding='utf-8'))
    o = json.loads(ORACLE.read_text(encoding='utf-8'))
    p = json.loads(POSTHOC.read_text(encoding='utf-8'))
    ag, hits = o['readings']['agreement_vs_product_B10'], o['readings']['oracle_hits']
    pos = v['checks']['P1_positive_control_sameform']
    assert (pos['n_agree'] == pos['n_queries'] == o['readings']['n_queries'] == 120
            and pos['oracle_hits'] == o['readings']['product_hits'] == 88), 'POS 逐例复现不成立'
    return {
        'rc': v['rc'], 'layers': v['rc_layers'],
        'agreement': {k: round(ag[k], 4) for k in ag},
        'hits': hits, 'product_hits': o['readings']['product_hits'], 'n_queries': o['readings']['n_queries'],
        'n_disagree_pos': len(o['disagree_POS_vs_product']),
        'anchor_bitexact': o['oracle']['anchor_chunk_mapping_bitexact'],
        'nontrivial': o['non_trivial_four_arms_distinct'],
        'diff': {a: p['discriminative_power_audit'][a] for a in ('POS', 'N1', 'N2', 'N3')},
        'merge': p['merge_order_diagnostic'],
        'defects': [d['id'] for d in v['defects']],
    }


def main():
    apply = '--apply' in sys.argv
    d = derive()
    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')[:19] + '+0800'

    # ── baselines 条目 ────────────────────────────────────────────────
    raw = BAS.read_text(encoding='utf-8')
    doc = json.loads(raw)
    if not ser_assert(raw, doc, 'baselines'):
        return 3
    entry = {
        'id': BASE_ID,
        'face': 'F_merge',
        'kind': 'instrument_criterion',
        'metric': ('面 4（上下文精排）的**器具面判据形态**基准：同形（RRF 融合）口径下的独立 oracle 对产品生产口径池的'
                   '逐例复现度，以及三档负控形态的**臂间差异量**（判别力形态）'),
        'unit': 'queries',
        'value': {
            'n_queries': d['n_queries'],
            'sameform_agreement_pos': d['agreement']['POS'],
            'sameform_hits_pos': d['hits']['POS'],
            'product_hits_b10': d['product_hits'],
            'per_query_disagreement_pos': d['n_disagree_pos'],
            'singlearm_agreement_n1': d['agreement']['N1'],
            'mispair_agreement_n2': d['agreement']['N2'],
            'zerovec_agreement_n3': d['agreement']['N3'],
            'hits_by_form': d['hits'],
            'symdiff_hits_vs_product': {a: d['diff'][a]['symdiff_hits_vs_product'] for a in d['diff']},
            'hits_delta_vs_product': {a: d['diff'][a]['hits_delta_vs_product'] for a in d['diff']},
            'merge_order_early_hits': d['merge']['form_early_merge_take_units']['n_hits'],
            'merge_order_late_hits': d['merge']['form_late_merge_take_parents']['n_hits'],
            'merge_order_gain_hits': d['merge']['gain_hits'],
            'early_pool_lt_10_n': d['merge']['pool_len_early_lt_10_n'],
            'instrument_defects_n': len(d['defects']),
        },
        'threshold': (
            '① **同形口径正控（主判据）**：`agreement(POS 同形, 产品 B10) ≥ 0.90`（本轮 **1.0000** ⇒ PASS；'
            'R626 单路口径 0.8409 的 FAIL **不翻案**、并列保留）；② **形态敏感**：`agreement(N1 单路) < agreement(POS)` '
            '且 `≤ 0.90`（本轮 0.8750 < 1.0000 ⇒ PASS）；③ **负控（正确形态 = 臂间差异量）**：`symdiff_hits_vs_产品` '
            '与「命中数差」须**单调可辨**（本轮 0/15/20/29 与 0/−13/−20/−29；POS = 0 ⇒ 逐例复现）；'
            '**旧形态 `agreement ≤ 0.25` 已判定为无牙**（N2 = 0.8333 ≫ 0.25，本轮照原样 FAIL）⇒ '
            '**下轮负控禁用 `agreement(臂, 产品)` 形态**，改用差异量；④ 跨轮**禁相减**、只并列。'),
        'threshold_source': 'eval/rover/r627/prereg-r627.json（P1/P2/P3）+ eval/capability/baselines.json#rerank-production-caliber',
        'source_path': 'eval/rover/r627/oracle-r627.json',
        'source_sha12': sha12('eval/rover/r627/oracle-r627.json'),
        'ground_rule': (
            '唯一自由度 = 判据的**比较形态**（单路 vs 同形融合）；产品源码零改动、冻结件逐字节复用（语料 1299 / 查询 120 / '
            '`eval/rover/r624/vec/*` / `eval/rover/r625/out/B10.json`）。oracle 独立性 = stdlib 纯 Python、零 import 本仓；'
            '**向量源不独立（冻结件，同源性由 R624 G0 覆盖）** ⇒ 该 oracle 与产品**同形**，只作**器具自证**，'
            '不得当作能力面的独立 oracle（能力面用**异形**信号 BM25 + 块粒度 dense，见 R626）。'),
        'check_cmd': ("python3 -c \"import io,json;o=json.load(io.open('eval/rover/r627/oracle-r627.json',encoding='utf-8'));"
                      "a=o['readings']['agreement_vs_product_B10'];assert a['POS']==1.0 and o['readings']['oracle_hits']['POS']==88;print('OK')\""),
        'updated_round': 'R627',
    }
    ids = [i for i, e in enumerate(doc['entries']) if e['id'] == BASE_ID]
    action_b = 'append' if not ids else 'repin'
    if ids:
        doc['entries'][ids[0]] = entry
    else:
        doc['entries'].append(entry)

    # ── registry 行 ──────────────────────────────────────────────────
    rraw = REG.read_text(encoding='utf-8')
    rdoc = json.loads(rraw)
    if not ser_assert(rraw, rdoc, 'registry'):
        return 3
    row = {
        'id': ROW_ID,
        'owner_round': 'R627',
        'level': 'L2',
        'evidence_generated_with': {
            'evidence_kind': 'artifact',
            'pin_status': 'frozen',
            'pin_reason': 'archived-per-round',
            'artifact_sha12': sha12(REPORT),
            'instrument': INSTR,
            'instrument_sha12': sha12(INSTR),
            'binding': 'audit-pin',
            'audited_by_round': 'R627',
        },
        'capability': (
            'RF0005 §0 DoD **面 4 · 上下文精排** 的**器具面判据形态修法**轮（承 R626 单列缺陷 `P4-pos-prereg-form`）：'
            'R626 的正控用**单路**（dense-only）口径对**融合池**读数判 FAIL（0.8409 < 0.90），本轮定位为**比较形态失配**'
            '——产品池 = dense 与 lexical 的 **RRF 融合** top-10（代码事实 `RAGRecall.cs:316-353` + `RrfFuser.cs:22` k0=10、'
            '双权重 1.0），单路与融合池本不必一致。本轮加**同形（RRF 融合）**独立 oracle（stdlib 纯 Python、零 import 本仓）'
            '对 `B10` 冻结产品读数逐例复算：**agreement 1.0000（120/120）· 命中 88/88 · 逐例差异 0**；'
            '前置锚 = 块映射重放 **641/641 逐字节命中**；非平凡 = 四形态归属向量**互异** ∧ 命中 88/75/68/59 单调可辨。'
            '**同时自捕第二件同类器具缺陷**：负控指标 `agreement(臂, 产品)` 分子含产品自身 miss 的 32 条白送一致 ⇒ '
            '配错臂仍 0.8333 ⇒ **该形态对坏臂无牙**（照原样 FAIL、阈值不下调），正确形态 = **臂间差异量**'
            '（symdiff 0/15/20/29 · 命中数差 0/−13/−20/−29，单调可辨）。'
            '**事后诊断（不进 rc）**：归并/截断次序（早归并 Take 单元 vs 晚归并 Take 父文档）**gain 0/120 ⇒ 该轴被否证**，'
            '「同父多块白占槽位」存在（23/120）但不承重 ⇒ 不开实现。'
            '**未测**：tokens / 缓存命中率 / 轮数（本面零远端）· codex 外部真值臂（本地检索面无远端题面）。'
        ),
        'evidence_path': REPORT,
        'evidence_cmd': ('python3 -B -u eval/rover/r627/oracle_fusion_r627.py && python3 -B -u eval/rover/r627/posthoc_r627.py '
                         '&& python3 -B eval/rover/r627/judge_r627.py && python3 eval/rover/r627/closeout_r627.py '
                         '&& python3 eval/capability/status_gen.py --check'),
        'negative_control': (
            '① **形态敏感负控（有牙）**：把 oracle 退化为**单路**（= R626 旧判据形态）⇒ agreement 掉到 **0.8750**、'
            '命中 88→75、symdiff 15 ⇒ 判据对「形态被破坏」有牙；② **配错负控**：查询**向量**移位一格（文本不变，两路同时被打乱）'
            '⇒ 命中 88→68 ⇒ **旧指标形态无牙已被取证**（agreement 仅 0.8333 ≫ 阈值 0.25）；'
            '③ **零向量负控**：查询向量置零 ⇒ 命中 88→59；④ **非平凡成对**：四形态 per-query 归属向量**互异**'
            '（防「恒定输出」冒充可复现）；⑤ **前置锚**：块映射重放 641/641 逐字节；'
            '⑥ **POS 逐例复现**：symdiff=0 ∧ 逐例差异 0 ⇒ 主判据不是「分数巧合」。'
        ),
        'covers': [BASE_ID, 'rerank-production-caliber', 'rerank-four', 'rerank-recall-shape',
                   'src/agent.tests/RerankFaceTests.cs', REPORT, 'eval/capability/baselines.json'],
        'runs': 1,
        'verdict': (
            '面 4 = 器具面判据形态**修法完成 · 仍未达标**（rc=1，`defects=[P3-negctl-metric-form]`）。'
            '主判据（同形口径正控）**PASS**：agreement 1.0000 ≥ 0.90，且逐例复现产品（88/88、差异 0）⇒ '
            'R626 的 0.8409 全部由**比较形态**解释。器具层另 1 条缺陷（负控指标形态）**未闭合**⇒ rc=1；'
            '**零产品源码改动 ⇒ 无任何能力/成本增益宣称**；生产口径 R@N 0.7333 < 0.9 的达标路径**待用户放行**。'
        ),
        'aot': ('未跑（本面为零远端 / 纯 Python 器具轮，未构建、未发布产品件）⇒ 证据阶梯按实定级 **L2**，不升级；'
                'AOT 校验按 registry `aot_check_policy` 仅在【发布 tag】时执行。'),
    }
    existing = [i for i, r in enumerate(rdoc['rows']) if r['id'] == ROW_ID]
    action_r = 'append' if not existing else 'repin'
    if existing:
        rdoc['rows'][existing[0]] = row
    else:
        rdoc['rows'].append(row)
    rdoc['updated_round'] = 'R627'

    # ── kpi 行（带 baselines）────────────────────────────────────────
    kpi = {
        'round': 'R627',
        'ts': now,
        'kind': ('RF0005 §0 DoD 面 4「上下文精排」**器具面判据形态修法**：把 R626 的正控从**单路**口径改为**同形（RRF 融合）**'
                 '口径，并自捕负控指标形态缺陷。零产品源码改动 / 零远端调用 / 零真机臂 / 零新增夹具。'),
        'change': ('产品侧改动 = **零**（`git status --porcelain src/` 空）。器具面 = 新增 `eval/rover/r627/'
                   '{oracle_fusion_r627.py,posthoc_r627.py,judge_r627.py,closeout_r627.py}` + 预注册/DAG/报告；'
                   '既有器具与登记表**未改**（R623–R626 的 pin 不失效）。'),
        'readings': {
            'axis': '无（器具轮，非臂轮）——唯一自由度 = 判据的**比较形态**（单路 → 同形融合）',
            'sameform_agreement_pos': d['agreement']['POS'],
            'sameform_hits_pos': d['hits']['POS'],
            'product_hits_b10': d['product_hits'],
            'per_query_disagreement_pos': d['n_disagree_pos'],
            'singlearm_agreement_n1': d['agreement']['N1'],
            'mispair_agreement_n2': d['agreement']['N2'],
            'zerovec_agreement_n3': d['agreement']['N3'],
            'hits_by_form': d['hits'],
            'discriminative_power_audit_symdiff': {a: d['diff'][a]['symdiff_hits_vs_product'] for a in d['diff']},
            'anchor_chunk_bitexact': d['anchor_bitexact'],
            'non_trivial_four_arms_distinct': d['nontrivial'],
            'merge_order_gain_hits_informational': d['merge']['gain_hits'],
            'early_pool_lt_10_n_informational': d['merge']['pool_len_early_lt_10_n'],
            'instrument_defects': d['defects'],
            'tokens': '未测（本面零远端 LLM 调用）',
            'cache_hit_rate': '未测（同上）',
            'external_truth_arm': '未跑（本地检索面，无远端题面）',
        },
        'baselines': ['rerank-oracle-form', 'rerank-production-caliber', 'rerank-four'],
        'prereg': PREREG,
        'evidence': REPORT,
        'verdict': {'rc': d['rc'], 'rc_layers': d['layers'], 'main_criterion_pass': True,
                    'defects': d['defects'],
                    'reason': '主判据 PASS（同形正控 1.0000）· 器具层另 1 条缺陷未闭合 ⇒ rc=1 · 无增益宣称'},
    }

    if not apply:
        print('DRY-RUN ok: baselines=%s registry=%s kpi_append=1 ledger_present=%s'
              % (action_b, action_r, '### 24. R627 文献小步' in LEDGER.read_text(encoding='utf-8')))
        print('report_sha12=%s instrument_sha12=%s' % (sha12(REPORT), sha12(INSTR)))
        return 0

    with io.open(BAS, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        if raw.endswith('\n'):
            f.write('\n')
    with io.open(REG, 'w', encoding='utf-8') as f:
        json.dump(rdoc, f, indent=1, ensure_ascii=False)
        if rraw.endswith('\n'):
            f.write('\n')
    seen = any('"round": "R627"' in line for line in io.open(KPI, encoding='utf-8'))
    if not seen:
        with io.open(KPI, 'a', encoding='utf-8') as f:
            f.write(json.dumps(kpi, ensure_ascii=False) + '\n')

    # ── 读回复核 ─────────────────────────────────────────────────────
    b2 = json.loads(BAS.read_text(encoding='utf-8'))
    r2 = json.loads(REG.read_text(encoding='utf-8'))
    ok_b = any(e['id'] == BASE_ID for e in b2['entries'])
    rrow = [x for x in r2['rows'] if x['id'] == ROW_ID]
    ok_r = bool(rrow)
    ok_v = ok_r and rrow[0]['evidence_generated_with']['artifact_sha12'] == sha12(rrow[0]['evidence_path'])
    ok_kpi = sum(1 for line in io.open(KPI, encoding='utf-8') if '"round": "R627"' in line) == 1
    ok_l = '### 24. R627 文献小步' in LEDGER.read_text(encoding='utf-8')
    print('READBACK baselines=%s registry=%s verdict_pin=%s kpi_row=%s ledger=%s updated_round=%s'
          % (ok_b, ok_r, ok_v, ok_kpi, ok_l, r2.get('updated_round')))
    return 0 if (ok_b and ok_r and ok_v and ok_kpi and ok_l) else 3


if __name__ == '__main__':
    sys.exit(main())
