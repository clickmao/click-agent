#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R637 收口件：把定因读数**派生**为 baselines 条目 + registry 行 + kpi 行（append-only，幂等）。

纪律（承 R409/R625/R636）：
  ① 写前断言 `json.dumps(doc, indent=1, ensure_ascii=False)+tail == 原字节`，不符即拒写（fail-closed rc=3）；
  ② 只**追加**，不重排既有内容；③ 幂等（按 id / round 去重）；④ 写后读回复核；
  ⑤ covers[] 叙述条目**禁含半角斜杠**（承 R636 自捕 E4：被判「路径不存在」⇒ 形式门禁红）。
用法: python3 eval/rover/r637/closeout_r637.py [--apply]
"""
import hashlib
import io
import json
import pathlib
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
V = ROOT / 'eval/rover/r637/verdict-r637.json'
MF = ROOT / 'eval/rover/r637/out/minfix-r637.json'
SL = ROOT / 'eval/rover/r637/family-lift-r637-selftest.json'
BAS = ROOT / 'eval/capability/baselines.json'
KPI = ROOT / 'eval/capability/kpi.jsonl'
REG = ROOT / 'docs/verification-registry.json'
REPORT = 'eval/rover/r637/report-r637.md'
EVID = 'docs/evidence/RF0001/R637-family-block-attribution.md'
INSTR = 'eval/rover/r637/attrib_r637.py'
INSTR2 = 'eval/rover/r637/minfix_r637.py'
INSTR3 = 'eval/rover/r637/family_lift_r637.py'
BASE_ID = 'F_merge.quality.family_lift_min'
ROW_ID = 'r637.family-block-readonly-attribution'


def sha12(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:12]


def ser_assert(raw, doc, tag):
    got = json.dumps(doc, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else '')
    if got != raw:
        print('SER_MISMATCH %s ⇒ 拒写（改用文本插入，禁静默重排）' % tag)
        return False
    return True


def baseline_entry(v, mf, sl):
    return {
        'id': BASE_ID,
        'face': 'F_merge',
        'kind': 'instrument_criterion',
        'metric': ('「**最低族栏**」判据：同一冻结逐例读数上取 **最差跑次** 的族级 Δ示例数（`F_lift_min_worst`），'
                   '与逐窗中位聚合口径**并列**报告；主判 PASS ∧ 最差栏跨阈 ⇒ 禁单读聚合栏。'),
        'unit': 'cases',
        'value': {
            'threshold_cases': -2,
            'selftest_pass': sl.get('pass'),
            'selftest_rc_hint': sl.get('rc_hint'),
            'hollow_gate_demo': {
                'same_frozen_data': True,
                'F_lift_min_median': sl['S2_detail']['F_lift_min_median'],
                'F_lift_min_worst': sl['S2_detail']['F_lift_min_worst'],
                'aggregate_median_D_cases': sl['S2_detail']['aggregate_median_D_cases'],
                'reading': '**空心闸实证**：中位式 PASS（0）而最差式 FAIL（−15）⇒ 只报聚合/中位在构造上掩盖整族归零',
            },
            'minfix_rc': mf.get('rc'),
            'minfix_targets': {t['tag']: t.get('verdict') for t in mf.get('targets', [])},
        },
        'threshold': ('T1 三态无条件发射：判决件必含 `F_lift_min_worst` / `F_lift_min_median` / `aggregate_median_D_cases`；'
                      'T2 阈值 **−2 例**（先声明后算，见 prereg-r637.json）；T3 两侧有牙：S5（单族落后 1 例，未跨阈）必 PASS ∧ '
                      'S4（全族一致落后 6 例）与 S2（单跑次整族归零）必 FAIL。'),
        'threshold_source': 'eval/rover/r637/prereg-r637.json',
        'source_path': 'eval/rover/r637/family-lift-r637-selftest.json',
        'source_sha12': sha12('eval/rover/r637/family-lift-r637-selftest.json'),
        'check_cmd': ("python3 eval/rover/r637/family_lift_r637.py --selftest; python3 -c \"import io,json;"
                      "d=json.load(io.open('eval/rover/r637/family-lift-r637-selftest.json'));"
                      "print(d['pass'],d['S2_detail']['F_lift_min_median'],d['S2_detail']['F_lift_min_worst'])\""),
        'ground_rule': ('裁决式取**最差跑次**而非中位（族级归零在构造上被中位掩盖）；判据与被复算数据同源冻结件；'
                        '只读复算、零重测；不重算任何既有质量列（并列读数）；跨轮禁相减。'),
        'negative_control': ('五态自检（`family-lift-r637-selftest.json`，全过）：S2 单跑次整族归零 ⇒ 最差式 FAIL 而中位式 PASS'
                             '（**空心闸两侧成对**）；S3 同数据旁路本判据 ⇒ 聚合口径判过（判决来自判据非数据）；'
                             'S4 全族一致落后 ⇒ FAIL（非恒绿）；S5 未跨阈 ⇒ PASS（非恒红）。'),
    }


def registry_row(v, mf, sl):
    step = {t['tag']: t.get('wythoff_stepwise', {}).get('pass_by_step') for t in mf.get('targets', [])}
    return {
        'id': ROW_ID,
        'level': 'L3',
        'owner_round': 'R637',
        'capability': (
            'RF0005 §2 固定环 · 「选靶逐例归因」步：R636 判据 `B_family_block` 报 `pair_read_ok=False`（本侧整族归零）'
            '后，本轮做**只读逐例定因**（零产品源码改动 / 零重测 / 零新臂 / 零远端 / 零新增夹具）。'
            '冻结面 = r631/r633/r634/r635/r636 五轮 14 窗 = **61 活跑次 / 1 VOID**（`cli_rc=124` 挂死）/ 逐例 3,538 行。'
            '**判决 rc=1**：J0 oracle 正控 15/15 · J1 census 复现 checked 47 mismatch 0 · '
            'J2/J3 守恒 `205 = 产物 205 + 构造 0 + 判据 0`（`TRUE_WRONG 105 / STATE_FLIP 63 / HARD_CRASH 32 / LEGAL_NONMIN 5`）· '
            '**J4 机制假设 FAIL（预注册被证伪，照原样判）** · J5 变异负控 3/3 · J5b 最小修复实验 4/4 · J6 确定性 5/5。'
            '**结论：5 个整族归零跑次 = 4 处各异的产物缺陷 + 1 处探针覆盖缺口**（`r633:w227/codex` 入口未定义变量 `limit`；'
            '`r635:w232/agentP-r2` 冷集公式第二分量写成 `n`；`r636:w236/codex` **两处叠加**（floor 后多余 ±1 修正 ∧ 走法枚举未限定合法着法，'
            'stepwise 0→13→15）；`r636:w234/agentP-r3` 贪心构造多 1；第 5 个块 `r634:w230/agentP-r3` 属 **sub** 族、'
            '冷集探针**不覆盖** ⇒ 只落逐例分类 14/14 全 `TRUE_WRONG` 状态层误判，**行级定因未测到**）。'
            '每处最小修复实验的成对控制：目标族 **0/n → n/n** ∧ 其它三族**逐例逐字节不变** ∧ **空重写负控仍 0/n**。'
            '**判据侧落地**：新件 `eval/rover/r637/family_lift_r637.py`（最低族栏 `F_lift_min`，阈值 −2 例先声明后算；五态自检 pass=true），'
            '并给出**空心闸实证** —— 同一冻结数据下 `F_lift_min_median=0`（PASS）而 `F_lift_min_worst=-15`（FAIL）。'
            '**事后判别特征（`checks_posthoc`，显式标事后性）**：`intersect == 0 ∧ missing == n_truth`（真值冷点在探针面全丢）'
            'wythoff 块 **4/4 命中** · 非块跑次 **1/21 假阳** · CLEAN **0/36 假阳**；原四变类机制标签分辨率不足'
            '（`ENTRY_ERROR` 在 PARTIAL 与 BLOCK 均出现）⇒ 不可作判别式。'
            '**自捕器具缺陷（不翻案）**：J5-N4 用写死正则锚 ⇒ 冻面四跑次四种实现只命中一种、`applied=false`'
            '（**锚点缺失，不是修复无效**）⇒ 补救件逐跑次显式缺陷行（每处断言替换 == 1）⇒ 4/4 PASS。'
            '**诚实边界：只读复算 ≠ 真机新跑 · sub 族块机理未测到 · 行级定因只证「缺陷在被改那一行」不证「生产已修」· '
            '预注册 FAIL 不翻案 · 不宣称任何收益降幅 · 三档终局目标读数不动不宣称。**'
        ),
        'evidence_cmd': (
            'python3 eval/rover/r637/attrib_r637.py && python3 eval/rover/r637/minfix_r637.py && '
            'python3 eval/rover/r637/family_lift_r637.py --selftest && '
            'python3 eval/capability/decl_sweep.py --check && '
            'python3 eval/capability/status_gen.py --check'
        ),
        'evidence_path': EVID,
        'evidence_generated_with': {
            'evidence_kind': 'artifact',
            'pin_status': 'live',
            'pin_reason': 'worktree-only',
            'artifact_sha12': None,
            'instrument': INSTR,
            'instrument_sha12': sha12(INSTR),
            'binding': 'audit-pin',
            'audited_by_round': 'R637',
        },
        'covers': [
            INSTR,
            INSTR2,
            INSTR3,
            'eval/rover/r637/prereg-r637.json',
            'eval/rover/r637/dag-r637.md',
            'eval/rover/r637/verdict-r637.json',
            'eval/rover/r637/report-r637.md',
            'eval/rover/r637/family-lift-r637-selftest.json',
            'eval/rover/r637/out/percase-r637.json',
            'eval/rover/r637/out/probe-coldset-r637.json',
            'eval/rover/r637/out/negctl-r637.json',
            'eval/rover/r637/out/minfix-r637.json',
            'eval/rover/r610/cases/cases-r521.json',
            'eval/rover/r636/family-block-census-r636.json',
            EVID,
            '只读复算面（重放冻结快照：逐跑次临时副本 + 零写入原树）与 J1 冻结判决件交叉校验（checked 47 mismatch 0）',
            '三态归属守恒（`205 = 产物 205 + 构造 0 + 判据 0`，逐例一次且仅一次）',
            '冷集行为探针（经产物自身接口取隐含冷集，与独立 oracle 的 P 位集合比对）与四变类机制标签',
            '逐跑次最小修复实验（显式缺陷行补丁，每处断言替换次数 == 1）与空重写负控',
            '新判据 `F_lift_min` 的五态自检（含空心闸两侧成对与旁路对照）',
        ],
        'negative_control': (
            '成对/负向控制（现场执行，读数入 `verdict-r637.json` / `family-lift-r637-selftest.json` / '
            '`out/negctl-r637.json` / `out/minfix-r637.json`）：'
            '① **独立 oracle 正控**：15/15（判据器有牙的前提，不绿则整轮弃权）。'
            '② **变异负控三件成对**：同字节空重写 ⇒ 目标族仍 `0/15`（**非「凡改即绿」**）∧ 替换为独立 oracle 实现 ⇒ `15/15` 全 OK（探针**可转绿**）∧ '
            '恒 LOSE ⇒ `4/15`（必被大量判红）。'
            '③ **最小修复实验的成对控制（最承重）**：目标族 `0/n → n/n` ∧ 其它三族**逐例逐字节不变** ∧ 空重写负控仍 `0/n` ⇒ '
            '缺陷归因到**被改那一行**（排除「凡改即绿」与管道面）。'
            '④ **新判据两侧有牙**：S2 单跑次整族归零 ⇒ 最差式 FAIL 而**中位式 PASS**（空心闸两侧成对）∧ '
            'S5 未跨阈 ⇒ PASS（非恒红）∧ S4 全族一致落后 ⇒ FAIL（非恒绿）∧ S3 同数据旁路本判据 ⇒ 聚合口径判过（判决来自判据，不来自数据）。'
            '⑤ **确定性 ×2**：5/5 整族归零跑次逐例逐字节相同（非常数输出冒充——同族跨族读数互异由 `probe-coldset` 四变类分布证）。'
            '⑥ **VOID 前置剔除**：`cli_rc=124` 挂死跑次先剔除并单列，否则「挂死」被读成「整族归零」。'
            '⑦ **锚点缺失 fail-closed**：最小修复实验的锚点替换次数 != 1 ⇒ `ANCHOR_MISS` 且 rc=2（**不静默跳过、不静默判过**）。'
        ),
        'note': (
            '轮次工件: eval/rover/r637/{prereg-r637.json, dag-r637.md, attrib_r637.py, minfix_r637.py, family_lift_r637.py, '
            'family-lift-r637-selftest.json, verdict-r637.json, report-r637.md} + out/{percase-r637.json, percase-r637-partial.json, '
            'probe-coldset-r637.json, negctl-r637.json, minfix-r637.json, attrib-run.log} + evidence/。'
            '自捕 **1 条**（J5-N4 锚点写死 ⇒ `applied=false`；补救件单列，**判据不翻案**）。'
            '跳步「构建/AOT」（零 `src/` 改动 ⇒ 无新二进制可构建）。'
            '跳步「产品侧最小改动」（轮性质 = 只读定因 ⇒ 预注册自陈零产品改动，净产品改动 0）。'
            '跨轮禁相减：R634（rc=1）/ R635（rc=1）/ R636（rc=1）/ 本轮（rc=1）**只并列**。'
            '基线引用: eval/capability/kpi.jsonl 行 R637 带 `baselines` id 列表（RF0004 §4.1 引用义务）；'
            '新增基准条目 `F_merge.quality.family_lift_min`（kind=instrument_criterion）。'
            '推送暂停令在效：只本地 commit，无 push / 无镜像 / 无 gh api 写。'
        ),
    }


def main():
    apply = '--apply' in sys.argv
    v = json.loads(V.read_text(encoding='utf-8'))
    mf = json.loads(MF.read_text(encoding='utf-8'))
    sl = json.loads(SL.read_text(encoding='utf-8'))
    if v.get('rc') not in (0, 1) or sl.get('pass') is not True or mf.get('rc') != 0:
        print('VERDICT_NOT_USABLE rc=%s selftest=%s minfix=%s' % (v.get('rc'), sl.get('pass'), mf.get('rc')))
        return 3
    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')

    # ── baselines.json ────────────────────────────────────────────────
    raw = BAS.read_text(encoding='utf-8')
    doc = json.loads(raw)
    if not ser_assert(raw, doc, 'baselines.json'):
        return 3
    ids = [e['id'] for e in doc['entries']]
    act_b = 'skip'
    if BASE_ID not in ids:
        doc['entries'].append(baseline_entry(v, mf, sl))
        act_b = 'append'
    else:
        for i, e in enumerate(doc['entries']):
            if e['id'] == BASE_ID:
                doc['entries'][i] = baseline_entry(v, mf, sl)
                act_b = 'repin'

    # ── registry ──────────────────────────────────────────────────────
    rraw = REG.read_text(encoding='utf-8')
    rdoc = json.loads(rraw)
    if not ser_assert(rraw, rdoc, 'verification-registry.json'):
        return 3
    rids = [r['id'] for r in rdoc['rows']]
    act_r = 'skip'
    if ROW_ID not in rids:
        rdoc['rows'].append(registry_row(v, mf, sl))
        rdoc['updated_round'] = 'R637'
        act_r = 'append'
    else:
        for i, r in enumerate(rdoc['rows']):
            if r['id'] == ROW_ID:
                rdoc['rows'][i] = registry_row(v, mf, sl)
                act_r = 'repin'

    # ── kpi 行 ────────────────────────────────────────────────────────
    klines = [l for l in KPI.read_text(encoding='utf-8').splitlines() if l.strip()]
    act_k = 'skip'
    if not any(json.loads(l).get('round') == 'R637' for l in klines):
        act_k = 'append'

    print('PLAN baselines=%s registry=%s kpi=%s' % (act_b, act_r, act_k))
    if not apply:
        print('DRY-RUN（未写盘）')
        return 0

    if act_b != 'skip':
        BAS.write_text(json.dumps(doc, indent=1, ensure_ascii=False) +
                       ('\n' if raw.endswith('\n') else ''), encoding='utf-8')
    if act_r != 'skip':
        REG.write_text(json.dumps(rdoc, indent=1, ensure_ascii=False) +
                       ('\n' if rraw.endswith('\n') else ''), encoding='utf-8')
    if act_k == 'append':
        row = {
            'round': 'R637', 'ts': now, 'kind': (
                '**只读逐例定因轮**（承 R636 下轮候选 ①）：`B_family_block` 整族归零的逐例定因；'
                '冻结面 = r631/r633/r634/r635/r636 五轮 14 窗 61 活跑次 / 1 VOID；'
                '零产品源码改动 / 零重测 / 零新臂 / 零远端 / 零新增夹具；跳步「构建/AOT」与「产品侧最小改动」'),
            'change': (
                '零产品源码改动（净产品改动 0）⇒ 本轮唯一变化量 = **新器具两件**：'
                '`eval/rover/r637/attrib_r637.py`（只读定因，J0–J6）+ `eval/rover/r637/family_lift_r637.py`（新判据 `F_lift_min`，五态自检）'
                '+ 补救件 `eval/rover/r637/minfix_r637.py`（逐跑次最小修复实验，4/4 PASS）。'
                '登记：baselines +1 条 `F_merge.quality.family_lift_min`（kind=instrument_criterion）；'
                'registry +1 行 `r637.family-block-readonly-attribution`（append-only，序列化保形断言 OK）；'
                '文献台账追加 R637 段（append-only）。**自捕 1 条**（J5-N4 锚点写死 ⇒ `applied=false`，补救件单列、判据不翻案）。'),
            'readings': {
                'rc': v['rc'], 'rc_semantics': v['rc_semantics'],
                'frozen_face': v['frozen_face'],
                'J4_prereg': 'FAIL（机制假设被证伪，照原样判）',
                'family_block_runs': 5,
                'line_level_root_causes': 4,
                'probe_coverage_gap_runs': 1,
                'minfix_pass': '%d/%d' % (sum(1 for t in mf['targets'] if t['verdict'] == 'PASS'), len(mf['targets'])),
                'minfix_stepwise_w236': {t['tag']: t.get('wythoff_stepwise', {}).get('pass_by_step')
                                         for t in mf['targets'] if t['tag'] == 'r636:w236/codex'},
                'posthoc_discriminator': {
                    'feature': 'intersect == 0 AND missing == n_truth',
                    'hit_on_wythoff_blocks': '4/4', 'false_positive_nonblock': '1/21',
                    'false_positive_clean': '0/36'},
                'hollow_gate_demo': sl['S2_detail'],
            },
            'verdict': (
                '机制次级未过（**rc=1**）：预注册机制假设「整族归零 = 冷集构造错」被证伪 —— '
                '5 个整族归零跑次 = **4 处各异的产物缺陷**（各自归因到具体源码行，最小修复实验 4/4 实证）'
                '+ **1 处探针覆盖缺口**（`sub` 族不可判）。判据侧落地「最低族栏」并把「中位掩盖整族归零」实证为**空心闸**。'),
            'evidence': EVID,
            'prereg': 'eval/rover/r637/prereg-r637.json',
            'report': REPORT,
            'baselines': ['F_merge.quality.family_lift_min', 'F_merge.quality.family_block_scan',
                          'F_merge.quality.cases_median_truth', 'F_merge.quality.allpass',
                          'F_merge.gate.precondition_rc', 'F_merge.ld.frozen_list',
                          'F_orch.wythoff.pass_r606', 'F_env.prefix.legacy_anchor',
                          'F_merge.cache.hit_v_all', 'F_merge.cost.new_prompt_sum'],
        }
        with io.open(KPI, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')

    # ── 写后读回复核 ───────────────────────────────────────────────────
    ok = True
    d2 = json.loads(BAS.read_text(encoding='utf-8'))
    ok &= any(e['id'] == BASE_ID for e in d2['entries'])
    r2 = json.loads(REG.read_text(encoding='utf-8'))
    ok &= any(x['id'] == ROW_ID for x in r2['rows'])
    ok &= any(json.loads(l).get('round') == 'R637'
              for l in KPI.read_text(encoding='utf-8').splitlines() if l.strip())
    print('READBACK baselines=%d registry=%d kpi_rows=%d ok=%s'
          % (len(d2['entries']), len(r2['rows']),
             len([l for l in KPI.read_text(encoding='utf-8').splitlines() if l.strip()]), ok))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
