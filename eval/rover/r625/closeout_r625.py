#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R625 收口件：把「生产口径（K=10）四值 + 成本列」读数**派生**为基准台账条目 + registry 行 + kpi 行 + 文献台账。

纪律（承 R409/R623/R624）：
  ① 写前断言 `json.dumps(doc, indent=1, ensure_ascii=False)+tail == 原字节`，不符即拒写（fail-closed rc=3）；
  ② 只**追加**条目 / 行，不重排既有内容（对既有条目只做**加字段**）；
  ③ 幂等（按 id / round 去重；重跑只 re-pin 自己的行）；④ 写后读回复核。
用法: python3 eval/rover/r625/closeout_r625.py [--apply]
"""
import hashlib
import io
import json
import pathlib
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
VERDICT = ROOT / 'eval/rover/r625/verdict-r625.json'
BAS = ROOT / 'eval/capability/baselines.json'
KPI = ROOT / 'eval/capability/kpi.jsonl'
REG = ROOT / 'docs/verification-registry.json'
LEDGER = ROOT / 'docs/research/lit-review-ledger.md'
REPORT = 'eval/rover/r625/report-r625.md'
INSTR = 'eval/rover/r625/closeout_r625.py'
PREREG = 'eval/rover/r625/prereg-r625.json'
BASE_ID = 'rerank-production-caliber'


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
    if v.get('rc') not in (0, 1) or v.get('defects'):
        print('VERDICT_NOT_USABLE rc=%s defects=%s' % (v.get('rc'), v.get('defects')))
        return None
    r = v['readings']
    c = v['checks']
    p3 = c['P3_production_caliber_four_metrics']
    cost = v['cost_informational']
    return {
        'rc': v['rc'],
        'k10': r['B10'], 'k50': r['B50'], 'a10': r['A10'], 'a50': r['A50'], 'z10': r['Z10'],
        'four_k10': p3['four'],
        'four_thresholds': {k: x['pass'] for k, x in p3['thresholds'].items()},
        'n_thresholds_met': p3['n_thresholds_met'],
        'falsified_pool_width': p3['falsifier_pool_width_hypothesis']['falsified'],
        'buckets': c['P6_conservation']['buckets'],
        'n_missing_base': c['P6_conservation']['n_missing_base'],
        'zero_regression_diff': {a: d['n_membership_diff'] for a, d in c['P1_zero_regression']['detail'].items()},
        'cost': {a: {k: x for k, x in cost[a].items()} for a in cost},
        'gated': {a: r[a]['gated'] for a in r},
    }


def baseline_entry(d):
    return {
        'id': BASE_ID,
        'face': 'F_merge',
        'kind': 'face_measurement',
        'metric': '精排面 4 的**生产口径**读数（召回池宽 = 生产 TopK=10）+ 精排段**成本列**（信息项）：四值 NDCG@k / MRR / Precision@k / Recall@N，k=10，单 gold（grade 2/0），聚合域 = Recall@N==1 的查询',
        'unit': 'queries',
        'value': {
            'pool_k_production': 10,
            'pool_k_previous_measurement': 50,
            'production_k10_r_at_N': d['k10']['rate'],
            'production_k10_gated': d['k10']['gated'],
            'previous_k50_r_at_N': d['k50']['rate'],
            'previous_k50_gated': d['k50']['gated'],
            'fallback_k10_r_at_N': d['a10']['rate'],
            'negative_zero_k10_r_at_N': d['z10']['rate'],
            'ndcg10_median_k10': d['four_k10']['ndcg@10'],
            'mrr_median_k10': d['four_k10']['mrr'],
            'mrr_mean_k10': d['four_k10']['mrr_mean'],
            'p10_median_k10': d['four_k10']['p@10'],
            'n_dod_thresholds_met_of_4': d['n_thresholds_met'],
            'latency_us_pair_diff_median_k10': d['cost']['B10']['latency_us_pair_diff_median'],
            'latency_us_pair_diff_median_k50': d['cost']['B50']['latency_us_pair_diff_median'],
            'assembled_chars_T_sum_k10': d['cost']['B10']['assembled_chars_T_sum'],
            'assembled_chars_T_sum_k50': d['cost']['B50']['assembled_chars_T_sum'],
            'structural_miss_k10': d['n_missing_base'] - d['k10']['gated'],
            'buckets_k10_misses': d['buckets'],
        },
        'threshold': '① **DoD 目标（RF0005 §0 面 4，本轮未达标、不下调）**：NDCG@k ≥0.8 ∧ MRR ≥0.6 ∧ P@k ≥0.8 ∧ R@N =1.0 ⇒ 生产口径实测 2/4；② **饱和声明（禁据此判能力达标）**：K=10 时池宽 == k=10 ⇒ 单 gold 下 NDCG@10 / MRR 两项**分辨率失效**（任一置顶排序即 1.0），真正有分辨率的是 P@10（上界 = 1/k = 0.1，≥0.8 算术不可达）与 R@N；③ **成本列只作信息项**（R410），且 `candidates_scored` 对池宽不敏感（恒 233,040）⇒ 不得作精排成本代理；④ 跨口径**禁相减**（K=10 vs K=50 只并列）。',
        'threshold_source': 'eval/rover/r625/prereg-r625.json + eval/capability/baselines.json#rerank-four（DoD 四值阈值）',
        'source_path': 'eval/rover/r625/verdict-r625.json',
        'source_sha12': sha12('eval/rover/r625/verdict-r625.json'),
        'ground_rule': '唯一单变量轴 = **召回池宽 K**（口径轴）；生产口径 = `src/agent/contextassembler/ContextAssembler.Recall.cs:216 TopK = 10`（同 `RAGConfig.cs:15 MaxRecallResults = 10`），精排在 `RAGRecall.cs:448` Take **之后**执行（`:498`）⇒ 池尺寸 = 精排可重排空间。形态 = fusion ∧ embed = vec（生产 DI）；器具改动**只加成本列信息字段**，零回归已由 A50/B50 对 R624 件 `per_query` 逐位复算证明（diff=0）⇒ R623/R624 既有 pin 不失效。跨轮：与 R585–R624 禁相减、只并列。',
        'check_cmd': "python3 -c \"import io,json;v=json.load(io.open('eval/rover/r625/verdict-r625.json'));print(v['readings']['B10']['rate'], v['readings']['B50']['rate'], v['rc'])\"",
        'negative_control': '① **零向量负控臂（有牙）**：Z10 R@N 0.5417 ≤ 兜底臂 A10 0.6333 ∧ per_query membership 差异 **13** 条；② **零回归自证**：A50/B50 对 R624 `A1`/`B1` 的 `per_query` 集合差异 **0**（器具加字段未动判据路径）；③ **口径自证**：若 K 轴未生效（pool_len_median K=10 不收窄到 10）⇒ P2 判红（本轮实测 10 vs 48）；④ **成本列自证**：`candidates_scored` 跨池宽恒等（233,040）⇒ 该字段被显式判为**非**精排成本代理，防「按字段名读成本」的空心结论；⑤ **守恒**：五桶合计 == 未召回 44 条（严格守恒）。',
        'covers': [BASE_ID, 'rerank-four', 'rerank-recall-shape',
                   'src/agent.tests/RerankFaceTests.cs', 'eval/rover/r625/report-r625.md',
                   'eval/capability/baselines.json'],
    }


def main():
    apply = '--apply' in sys.argv
    d = derive()
    if d is None:
        return 3

    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')
    row_id = 'r625.rerank-production-caliber'

    # ── baselines.json ────────────────────────────────────────────────
    raw = BAS.read_text(encoding='utf-8')
    doc = json.loads(raw)
    if not ser_assert(raw, doc, 'baselines.json'):
        return 3
    ids = [e['id'] for e in doc['entries']]
    action_b = 'skip'
    if BASE_ID not in ids:
        doc['entries'].append(baseline_entry(d))
        action_b = 'append'
    else:
        for i, e in enumerate(doc['entries']):
            if e['id'] == BASE_ID:
                doc['entries'][i] = baseline_entry(d)
                action_b = 'repin'
    # 既有条目：只加口径注记字段（不撤旧读数）
    for e in doc['entries']:
        if e['id'] == 'rerank-recall-shape':
            e['form_caveat_production_caliber'] = (
                '**口径扩展（新读并列，旧读不撤）**：该条目的读数取自测量池 K=50，而生产口径为 '
                '`ContextAssembler.Recall.cs:216 TopK = 10`（R625 机检）。R625 于 K=10 取生产档读数：'
                '生产形态 R@N **0.7333**（gated 88）· 兜底形态 0.6333（gated 76）。'
                '两档**只并列、禁相减**；本条目 K=50 读数自此只作**并列对照档**。生产档读数以 '
                'id `rerank-production-caliber` 为准。'
            )

    # ── registry ──────────────────────────────────────────────────────
    rraw = REG.read_text(encoding='utf-8')
    rdoc = json.loads(rraw)
    if not ser_assert(rraw, rdoc, 'verification-registry.json'):
        return 3
    row = {
        'id': row_id,
        'round': 'R625',
        'owner_round': 'R625',
        'level': 'L2',
        'evidence_generated_with': {
            'evidence_kind': 'artifact',
            'pin_status': 'frozen',
            'pin_reason': 'archived-per-round',
            'artifact_sha12': sha12(REPORT),
            'instrument': INSTR,
            'instrument_sha12': sha12(INSTR),
            'binding': 'audit-pin',
            'audited_by_round': 'R625',
        },
        'capability': (
            'RF0005 §0 DoD **面 4 · 上下文精排** 的**口径收口**轮：R623/R624 的四值读数取自测量池 '
            'K=50，而生产链路的召回池宽为 **TopK = 10**（代码事实 `src/agent/contextassembler/'
            'ContextAssembler.Recall.cs:216` ∧ `RAGConfig.cs:15 MaxRecallResults = 10`；精排在 '
            '`RAGRecall.cs:448` Take 之后执行 ⇒ 池尺寸 = 精排可重排空间）⇒ 本轮把口径对齐到生产档，'
            '并首次采集精排段**成本列**。口径：唯一单变量轴 = 召回池宽 K（口径轴）；形态 = fusion ∧ '
            'embed = vec（生产 DI，承 R624）；冻结件 = `eval/bge/fixtures`（语料 1299 / 查询 120，单 gold，'
            '零新增夹具）；产品源码改动 = **零**。**读数**：R@N 生产档 K=10 **0.7333**（gated 88）vs 旧测量档 '
            'K=50 0.8083（gated 97）· 兜底档 K=10 0.6333（gated 76）· K=50 0.7500（gated 90）· 零向量负控 '
            'K=10 0.5417。**生产口径四值 vs DoD 阈值（不下调）**：NDCG@10 中位 **1.0000** ✓（**饱和**：池宽 == k）· '
            'MRR 中位 **1.0000** ✓（**饱和**）· P@10 中位 **0.1000** ✗（= 1/k，**算术不可达 0.8**）· '
            'R@N **0.7333** ✗ ⇒ 名义 **2/4**，**禁读作能力达标**。**成本列（信息项）**：精排段配对耗时中位 '
            'K=10 **69.0 µs** vs K=50 **1,942.7 µs**（≈28×）；装配面候选集合字符和 498,318 vs 2,420,739（≈4.9×）；'
            '`candidates_scored` 跨池宽**恒等**（233,040）⇒ 显式判为**非**精排成本代理。**零回归**：A50/B50 对 R624 '
            '`A1`/`B1` 的 per_query membership 差异 **0**、gated 90/97 同值 ⇒ 器具改动（只加信息字段）未动判据路径。'
            '**守恒**：A10 未召回 44 条五桶合计 44（仅池宽 4 · 仅形态 3 · 任一路线 10 · 两者皆需 5 · 结构性 22）。'
            '**未测**：tokens / 缓存命中率（本面零远端）· codex 外部真值臂（本地检索面无远端题面）。'
        ),
        'evidence_path': REPORT,
        'evidence_cmd': ('python3 tools/roundcheck/roundcheck.py preflight --round R625 --min-avail-mb 2769 '
                         '--min-disk-gb 1 --need-key AGENTFRAMEWORK_KEYS_DEEPSEEK && bash eval/rover/r625/run_r625.sh '
                         '&& python3 eval/rover/r625/judge_r625.py && python3 eval/rover/r625/closeout_r625.py '
                         '&& python3 eval/capability/status_gen.py --check'),
        'negative_control': (
            '① **零向量负控臂（有牙）**：Z10 R@N 0.5417 ≤ 兜底 A10 0.6333 ∧ per_query membership 差异 13 条；'
            '② **零回归自证**：A50/B50 对 R624 `A1`/`B1` per_query 集合差异 **0**；③ **口径自证**：K=10 池宽中位 10 vs '
            'K=50 中位 48（口径未生效即判 rc=2）；④ **成本列空心防护**：`candidates_scored` 跨池宽恒等 ⇒ 显式排除其作'
            '精排成本代理（防按字段名读成本的假结论）；⑤ **守恒**：五桶合计 == 未召回 44 条；⑥ **预注册证伪条目**：'
            '`R@N(K=10) ≥ R@N(K=50)` ⇒ 未命中（0.7333 < 0.8083）⇒ 池宽假设未被证伪（同向）。'
        ),
        'covers': [BASE_ID, 'rerank-four', 'rerank-recall-shape',
                   'src/agent.tests/RerankFaceTests.cs', REPORT, 'eval/capability/baselines.json'],
        'runs': 5,
        'verdict': (
            '面 4 = **口径收口完成 · 仍未达标**（rc=1，`defects=[]`）。生产口径（K=10）R@N **0.7333** < 旧测量档 '
            '(K=50) 0.8083 ⇒ 前两轮的读数取自产品不使用的池宽，只作并列对照。生产口径四值名义 2/4，但 NDCG@10/MRR '
            '在 K=10 上**饱和**（池宽 == k ⇒ 分辨率失效），真正有分辨率的两项（P@10 = 1/k 算术不可达 · R@N 0.7333）'
            '**双双未达** ⇒ **禁读作能力达标**。成本列首测：精排配对耗时 69 µs(K=10) vs 1,943 µs(K=50)（≈28×）⇒ '
            '池宽轴的成本是真实的（不得当免费收益）。零产品源码改动 ⇒ 无降幅可宣称。'
        ),
        'aot': ('未跑。本面为**组件级 JIT 测试路径**读数（xUnit 驱动产品真身召回路径 + 冻结语料）⇒ 证据阶梯按实定级 '
                '**L2**，不升级；AOT/CLI E2E 未行使（该组件未接 CLI 直通路径）。'),
    }
    existing = [i for i, r in enumerate(rdoc['rows']) if r['id'] == row_id]
    action_r = 'append' if not existing else 'repin'
    if existing:
        rdoc['rows'][existing[0]] = row
    else:
        rdoc['rows'].append(row)
    rdoc['updated_round'] = 'R625'

    # ── kpi 行 ────────────────────────────────────────────────────────
    kpi = {
        'round': 'R625',
        'ts': now,
        'kind': ('RF0005 §0 DoD 面 4「上下文精排」**生产口径对齐（召回池宽 K=10）+ 精排段成本列首测**：'
                 'R623/R624 的四值取自测量池 K=50，而生产召回池宽 = TopK=10（代码事实）⇒ 本轮口径收口。'
                 '零产品源码改动 / 零远端调用 / 零新增夹具语义。'),
        'change': ('产品侧改动 = **零**（src/agent.rag、src/agent.extensions、src/agent 未动，run 前后 SRC_DIRTY=0）。'
                   '器具面 = `src/agent.tests/RerankFaceTests.cs` **只加成本列信息字段**（配对耗时 µs / 装配面字符数 / '
                   '声明估算器 token 估计）+ `eval/rover/r625/{run_r625.sh,judge_r625.py,closeout_r625.py}` + 预注册/DAG。'),
        'readings': {
            'axis': '召回池宽 K（口径轴）：K=10 = 生产口径 / K=50 = R623–R624 测量口径',
            'production_k10_r_at_N': d['k10']['rate'], 'production_k10_gated': d['k10']['gated'],
            'previous_k50_r_at_N': d['k50']['rate'], 'previous_k50_gated': d['k50']['gated'],
            'fallback_k10_r_at_N': d['a10']['rate'], 'fallback_k50_r_at_N': d['a50']['rate'],
            'negative_zero_k10_r_at_N': d['z10']['rate'],
            'four_metrics_production_k10': d['four_k10'],
            'dod_thresholds_met_of_4': d['n_thresholds_met'],
            'dod_threshold_pass': d['four_thresholds'],
            'saturation_note': 'K=10 时池宽 == k ⇒ NDCG@10 / MRR 分辨率失效（单 gold），禁读作能力达标',
            'cost_informational': {
                'latency_us_pair_diff_median_k10': d['cost']['B10']['latency_us_pair_diff_median'],
                'latency_us_pair_diff_median_k50': d['cost']['B50']['latency_us_pair_diff_median'],
                'assembled_chars_T_sum_k10': d['cost']['B10']['assembled_chars_T_sum'],
                'assembled_chars_T_sum_k50': d['cost']['B50']['assembled_chars_T_sum'],
                'candidates_scored_note': '跨池宽恒等 233,040 ⇒ 非精排成本代理（显式排除）',
            },
            'zero_regression_membership_diff': d['zero_regression_diff'],
            'buckets_k10_misses': d['buckets'],
            'tokens': '未测（本面零远端 LLM 调用）',
            'cache_hit_rate': '未测（同上）',
            'external_truth_arm': '未跑（本地检索面，无远端题面）',
        },
        'baselines': ['rerank-production-caliber', 'rerank-four', 'rerank-recall-shape'],
        'prereg': PREREG,
        'evidence': REPORT,
        'verdict': {'rc': d['rc'], 'main_criterion_pass': False,
                    'n_dod_thresholds_met': d['n_thresholds_met'],
                    'defects': [], 'reason': '判据成立但主判据未达标（生产口径四值 2/4）'},
    }

    # ── 文献台账（追加 §22）──────────────────────────────────────────
    ledger_block = (
        '\n### 22. R625 文献小步（2026-09-22）\n\n'
        '| 日期 | 检索式 | 出处（含版本） | 逐字引文 | 机制假设 | 改哪一格 KPI | 单变量轴 + 判据 | 状态 |\n'
        '|---|---|---|---|---|---|---|---|\n'
        '| 2026-09-22 | `"reranking efficiency"`（cat cs.IR, max 8, sort date） | arXiv **2505.14432v1**（cs.IR/cs.CL；'
        'comment「15 pages, 4 figures」；**无 journal-ref ⇒ 纯预印本，权威代理最低档**） | 「Retrieve-and-rerank is a '
        'popular retrieval pipeline because of its ability to make slow but effective rerankers efficient enough at '
        'query time by reducing the number of comparisons.」 | 首级检索池的**宽度**是「慢而准的重排器」在查询时可用的**成本/效果旋钮**：'
        '池越宽 ⇒ 重排器的比较次数与耗时越高，且重排效果的上界由池内可用证据决定 | tokens（成本列：重排段耗时 / 被消费集合规模）+ '
        '质量（R@N 前置天花板） | 轴 = 召回池宽 K（10 vs 50）；判据 = 逐档读数并列 + 「生产口径 K=10 不得优于 K=50」作为证伪点 '
        '（若 K=10 ≥ K=50 ⇒ 池宽非承重、换杆） | **采信（机制支持）**：与本仓代码事实（精排在 `Take(TopK)` 之后 ⇒ 池 = 可重排空间）'
        '同向；**R625 实测** K=10 → K=50 使 R@N 0.7333 → 0.8083（+7.5 pt）而精排段配对耗时 69 µs → 1,943 µs（≈28×）⇒ '
        '「池宽是成本/效果旋钮」在本仓成立；**同时证伪其「可免费收益」读法** |\n'
        '| 2026-09-22 | `"reranking candidate pool size"` / `"recall ceiling retrieval"` | — | — | — | — | — | '
        '**未取到原文 ⇒ 不采信**（两次检索式均 0 结果；本轮检索计 3 式，含本行为 2 式 0 结果） |\n\n'
        '- 本轮**采信 1 条**（2505.14432v1，机制支持档）⇒ 连续 0 采信计数**归零**（`lit-review-ledger §21` 记「第 1 轮」），'
        '**检索不降频**。\n'
        '- 近月预印本 cited_by_count：Semantic Scholar 需 key，本轮**未取**⇒ 引用数「不可用」，不编造。\n'
    )

    if not apply:
        print('DRY-RUN ok: baselines=%s registry=%s kpi_append=1 ledger_append=1' % (action_b, action_r))
        print('report_sha12=%s instrument_sha12=%s' % (sha12(REPORT), sha12(INSTR)))
        return 0

    # 写 baselines
    with io.open(BAS, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        if raw.endswith('\n'):
            f.write('\n')
    # 写 registry
    with io.open(REG, 'w', encoding='utf-8') as f:
        json.dump(rdoc, f, indent=1, ensure_ascii=False)
        if rraw.endswith('\n'):
            f.write('\n')
    # 追加 kpi（幂等：同 round 已存在则不重复）
    seen = False
    with io.open(KPI, encoding='utf-8') as f:
        for line in f:
            if '"round": "R625"' in line:
                seen = True
    if not seen:
        with io.open(KPI, 'a', encoding='utf-8') as f:
            f.write(json.dumps(kpi, ensure_ascii=False) + '\n')
    # 追加文献台账
    lraw = LEDGER.read_text(encoding='utf-8')
    if '### 22. R625 文献小步' not in lraw:
        with io.open(LEDGER, 'a', encoding='utf-8') as f:
            f.write(ledger_block)

    # ── 读回复核 ──────────────────────────────────────────────────────
    b2 = json.loads(BAS.read_text(encoding='utf-8'))
    r2 = json.loads(REG.read_text(encoding='utf-8'))
    ok_b = any(e['id'] == BASE_ID for e in b2['entries'])
    ok_r = any(x['id'] == row_id for x in r2['rows'])
    n_kpi = sum(1 for _ in io.open(KPI, encoding='utf-8'))
    ok_kpi = sum(1 for line in io.open(KPI, encoding='utf-8') if '"round": "R625"' in line) == 1
    ok_l = '### 22. R625 文献小步' in LEDGER.read_text(encoding='utf-8')
    print('READBACK baselines=%s registry=%s kpi_row=%s(n=%d) ledger=%s updated_round=%s'
          % (ok_b, ok_r, ok_kpi, n_kpi, ok_l, r2.get('updated_round')))
    return 0 if (ok_b and ok_r and ok_kpi and ok_l) else 3


if __name__ == '__main__':
    sys.exit(main())
