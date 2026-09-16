#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q33 · C1: 口径并列声明的**结构化台账**生成器 (一次性, 幂等)。

背景 (Q32 §AG.5.4): Q32 的 C4 判据是**词面窗口启发式** (±3 行 + 词表), 三口径 (83/21/14) 全部含误红
⇒ 只作候选清单。本步把声明源从「词面」搬到**结构化字段**:

  台账 `docs/reports/caliber-declarations.json` (schema caliber-declarations/1)
  条目字段: id / file / line / pair / anchor_sha12 / class / scope / caliber_from / caliber_to
            / supersedes / note / owner_round
  判据 (见 caliber_void_audit_q33.py): 面内每个数值对必须有条目且 anchor_sha12 与现盘逐位一致。

面定义与 Q32 strict 逐位同源 (行内含口径标记 ∧ 含数值对), 面规模必须 == 44 (Q32 strict n_pairs)
—— 否则本脚本 rc=3 拒写 (面身份不可证即不写)。

分类 (class) 只允许闭集:
  migrated_lexicon_declared  —— Q32 已由词表命中的声明 (迁移; evidence 记命中词 + 偏移)
  same_caliber_trend         —— 同一口径内的演进序列 (无需新声明)
  caliber_change_inline      —— 行内已声明口径变更/登记
  judgment_revision_inline   —— 行内已声明是判定修正/口径扩张
  contrast_arm_declared      —— 对照组/隔离臂并列 (口径确立)
  candidate_delta_declared   —— 候选态 delta (未应用)
  same_value_no_change       —— 两侧同值 (非变化)
  projected_delta_annotated  —— 计划/预期量并带出处标注
  external_thirdparty        —— 外部第三方数字冲突 (非本仓读数面)
  detector_false_positive    —— 数值对抽取器把跨行公式/算式误当并列
  inapplicable_declared      —— 行内声明该口径对本轮不适用
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
LEDGER = 'docs/reports/caliber-declarations.json'
OUT = 'eval/capability/exp1-q33/adjudication_q33.json'
FACE_DIRS = ('docs/reports', 'docs/plans')
PAIR_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:→|->|⇒|vs\.?|至)\s*(\d+(?:\.\d+)?)')
CALIBER_MARK = ('口径', '两栏', '双栏', '不可比', '并列')
DECL_EXT = ('并列', '双栏', '两栏', '不可比', '口径变更', '口径断点', '作废', '可比性',
            '取代', '历史读数', '不再作为当前', '非口径', '不代表当前', '可比性断点',
            '桩口径', '真值口径', '供应商真值', '旧段正文<br>', '参考档', '不并排')
WINDOW = 3
Q32_FACE_PAIRS = 44          # Q32 strict 面规模 (基线, 用于面漂移增量报告; 非硬闸)

CLASSES = ('migrated_lexicon_declared', 'same_caliber_trend', 'caliber_change_inline',
           'judgment_revision_inline', 'contrast_arm_declared', 'candidate_delta_declared',
           'same_value_no_change', 'projected_delta_annotated', 'external_thirdparty',
           'detector_false_positive', 'inapplicable_declared', 'self_referential_example')

# 人工复核裁定表 (Q32 §AG.5.4 的 14 项候选, 键 = file:line:pair)
ADJUDICATION = {
    'docs/reports/dynamic-telemetry-eval-rollback-strategy.md:198:941→939': (
        'same_caliber_trend', 'quick-11 同一口径内的五批递降序列; 括号内已标注全量批 1165 属**不同口径**'),
    'docs/reports/dynamic-telemetry-eval-rollback-strategy.md:198:928→860': (
        'same_caliber_trend', '同上一对: 同口径趋势序列 (括号内口径注解在同窗内)'),
    'docs/reports/dynamic-telemetry-eval-rollback-strategy.md:209:1100→1250': (
        'caliber_change_inline', '行内逐字写「健康带 quick tok 上界 1100→1250 (C07 双轮成本口径登记)」⇒ 声明在行内'),
    'docs/reports/dynamic-telemetry-eval-rollback-strategy.md:261:812→176': (
        'contrast_arm_declared', '行内写「行为差分口径确立 / 全隔离臂对照」⇒ 两侧是**对照组**读数, 非同一序列前后值'),
    'docs/reports/iteration-master-plan.md:52:64→97': (
        'detector_false_positive', '抽取器把算式 `(floor(前缀/64)−1)×64 ⇒ 97%` 跨符号误当并列对 (非两栏读数并列); 该行另有「口径修订/旧口径仅作参考」声明'),
    'docs/reports/loop-detection-probe-hardening.md:45:1→5': (
        'judgment_revision_inline', '行内逐字写「open_count 由 1→5 是**判定修正**, 不是计划项变多」'),
    'docs/reports/market-agent-capabilities-R338.md:289:200→500': (
        'external_thirdparty', '外部第三方相互矛盾数字 (免费额度 200 vs 500), 非本仓读数面 ⇒ 不适用本仓口径声明纪律'),
    'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:1103:63→57': (
        'candidate_delta_declared', '表格「C10 口径」列 + 行内「剔除 6 条 index-scope-out」+ `delta_applied=false` (候选态)'),
    'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:1546:4→4': (
        'same_value_no_change', '「P3 计数面不成立 (4→4)」= 两侧同值, 非口径位移'),
    'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:1614:4→2': (
        'projected_delta_annotated', '带出处标注的计划量 (Q16 非重放 4 → 2) + 可复算判据'),
    'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:1626:4→2': (
        'projected_delta_annotated', '行内写「附录 Q 口径: 不可重放 4 → 2」⇒ 口径出处已在行内'),
    'docs/plans/v0.22.0-longterm-backlog.md:82:4→4': (
        'same_value_no_change', '探针读数 ±tools 前后同值 (4→4 token, 静默丢弃) ⇒ 非口径位移'),
    'docs/plans/v0.22.0-longterm-backlog.md:82:7→18': (
        'projected_delta_annotated', '负控合成模板读数 7→18(+11) 且同句给出 md5 判别力说明'),
    'docs/plans/v0.91.0-r475-replay-and-cache-accounting.md:15:900→1.0152': (
        'inapplicable_declared', '行首「口径:」+ 行内「K2b 对该轮不适用」⇒ 已声明该轮超出口径适用面'),
    # --- 面漂移增量 (Q32 面 44 → 本轮快照 46, +2; 均为**其它写者**写入, 见 Q33 读数) ---
    'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:2771:927→39': (
        'self_referential_example', '自指实例: 本行是「记录 Q32 误红」的文本, `927→39 tokens 达标` 是被引用的'
                                    '**自明读数样例**本身 ⇒ 机检不得把「记录缺陷的文本」当活并列; 同族坑 (引用示例须入围栏/标注)'),
    'docs/reports/r489-arm-stability-and-quality-verdict.md:74:6→13': (
        'contrast_arm_declared', '对照组并列: 「调用数三跑完全相同 = 6 vs 13 = −53.85%」两侧是**不同臂**'
                                 '(本地通道臂 vs 分母臂) 的调用数, 非同一序列前后值'),
}


def sha12(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def face_pairs():
    """复刻 Q32 strict 面: 行含口径标记 ∧ 行含数值对 (跳过表格分隔行)。"""
    out = []
    files = []
    for d in FACE_DIRS:
        for fn in sorted(os.listdir(os.path.join(ROOT, d))):
            if fn.endswith('.md'):
                files.append('%s/%s' % (d, fn))
    for f in files:
        lines = open(os.path.join(ROOT, f), encoding='utf-8', errors='replace').read().split('\n')
        for i, ln in enumerate(lines):
            if ln.lstrip().startswith('|') and '---' in ln:
                continue
            if not any(k in ln for k in CALIBER_MARK):
                continue
            for m in PAIR_RE.finditer(ln):
                lo, hi = max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)
                win = '\n'.join(lines[lo:hi])
                terms = [t for t in DECL_EXT if t in win]
                out.append({'file': f, 'line': i + 1, 'pair': '%s→%s' % m.groups(),
                            'line_text': ln, 'anchor_sha12': sha12(ln), 'lexicon_terms': terms})
    return files, out


def main():
    files, pairs = face_pairs()
    entries, adj_rows, unresolved = [], [], []
    for k, p in enumerate(pairs, 1):
        key = '%s:%d:%s' % (p['file'], p['line'], p['pair'])
        if key in ADJUDICATION:                       # 人工复核优先于词表迁移
            cls, note = ADJUDICATION[key]
        elif p['lexicon_terms']:
            cls, note = 'migrated_lexicon_declared', 'Q32 词表命中: %s' % ','.join(p['lexicon_terms'])
        else:
            unresolved.append(key)
            continue
        if cls not in CLASSES:
            print('CLASS_FAIL: %s 非法 class %s (rc=3)' % (key, cls))
            return 3
        supersedes = cls in ('caliber_change_inline', 'migrated_lexicon_declared', 'inapplicable_declared')
        e = {'id': 'cd-%03d' % k, 'file': p['file'], 'line': p['line'], 'pair': p['pair'],
             'anchor_sha12': p['anchor_sha12'], 'class': cls,
             'scope': 'external_nonmetric' if cls == 'external_thirdparty' else 'internal_caliber',
             'caliber_from': None, 'caliber_to': None, 'supersedes': supersedes,
             'note': note, 'owner_round': 'EXP1-Q33'}
        entries.append(e)
        if cls != 'migrated_lexicon_declared':
            adj_rows.append({'key': key, 'pair': p['pair'], 'class': cls, 'supersedes': supersedes,
                             'note': note, 'anchor_sha12': p['anchor_sha12']})
    if unresolved:
        print('UNRESOLVED: %d 对未裁定 ⇒ 拒写 (rc=3):\n  %s' % (len(unresolved), '\n  '.join(unresolved)))
        return 3

    snap = {}
    for p in pairs:
        snap.setdefault(p['file'], set()).add((p['line'], p['pair']))
    face_snapshot = {'n_files': len(snap), 'n_pairs': len(pairs),
                     'files': {f: {'file_sha12': sha12(open(os.path.join(ROOT, f), encoding='utf-8',
                                                            errors='replace').read()),
                                   'pairs': sorted(['%d:%s' % (l, q) for l, q in v])}
                               for f, v in sorted(snap.items())}}
    ledger = {'schema': 'caliber-declarations/1', 'owner_round': 'EXP1-Q33',
              'rule': ('面内 (行含口径标记 ∧ 含数值对) 每个数值对必须在本台账有条目, 且 anchor_sha12 与快照行'
                       '逐位一致; 行被改写 ⇒ ANCHOR_DRIFT (弃权单列), 不判绿。class 只允许闭集; 新对须重跑'
                       '本脚本 (未裁定即拒写)。面为**活文档**, 快照 + 漂移单列 (见 caliber_void_audit_q33.py)。'),
              'face_snapshot': face_snapshot,
              'n_entries': len(entries), 'entries': sorted(entries, key=lambda x: x['id'])}
    path = os.path.join(ROOT, LEDGER)
    new = json.dumps(ledger, ensure_ascii=False, indent=1) + '\n'
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(new)
    by_class = {}
    for e in entries:
        by_class[e['class']] = by_class.get(e['class'], 0) + 1
    payload = {'round': 'EXP1-Q33', 'schema': 'caliber-adjudication/1',
               'face': {'n_files': len(snap), 'n_pairs': len(pairs), 'q32_baseline_pairs': Q32_FACE_PAIRS,
                        'delta_vs_q32': len(pairs) - Q32_FACE_PAIRS},
               'face_delta_note': ('面为活文档: Q32 审计 (13:21) 之后其它写者新增 2 对 ⇒ 快照 46; '
                                   '增量已逐条裁定 (见 manual_rows 中 self_referential_example / contrast_arm_declared)'),
               'ledger': LEDGER, 'ledger_sha12': sha12(new), 'n_entries': len(entries),
               'by_class': by_class, 'n_manual_reviewed': len(adj_rows),
               'n_migrated_from_lexicon': by_class.get('migrated_lexicon_declared', 0),
               'manual_rows': sorted(adj_rows, key=lambda x: x['key']),
               'conservation': {'entries': len(entries), 'face_pairs': len(pairs),
                                'ok': len(entries) == len(pairs), 'unresolved': unresolved}}
    with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('FACE files=%d pairs=%d (Q32 baseline %d, delta %+d)'
          % (len(snap), len(pairs), Q32_FACE_PAIRS, len(pairs) - Q32_FACE_PAIRS))
    print('ENTRIES=%d  by_class=%s' % (len(entries), json.dumps(by_class, ensure_ascii=False)))
    print('MANUAL_REVIEWED=%d (Q32 候选 14 项 + 面漂移增量)' % len(adj_rows))
    print('LEDGER=%s sha12=%s' % (LEDGER, payload['ledger_sha12']))
    print('落盘 %s' % OUT)
    print('ADJUDICATE=%s' % ('OK' if payload['conservation']['ok'] else 'FAIL'))
    return 0 if payload['conservation']['ok'] else 2


if __name__ == '__main__':
    sys.exit(main())
