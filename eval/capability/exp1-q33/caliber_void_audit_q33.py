#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q33 · C1: 口径并列声明审计 (**结构化字段版**, 替代 Q32 词面窗口启发式)。

Q32 的三口径 (83 / 21 / 14 红) 全部含误红 —— 词面 (±3 行 + 词表) 无法区分
「需要作废/不可比声明的两栏并列」与「自明读数 / 对照组 / 外部第三方数字」。本器具把判据绑到**字段**:

  声明源 = `docs/reports/caliber-declarations.json` (schema caliber-declarations/1)
           条目字段: id/file/line/pair/anchor_sha12/class/scope/supersedes/note/owner_round

判据 (预注册 eval/capability/exp1-q33/prereg_q33.json §criteria.C1):
  · **快照面**内每条目必须定位成功 ∧ `anchor_sha12` 与**快照行字节**逐位一致 ∧ 该对仍在该行
    ⇒ DECLARED (绿); 行被改写 ⇒ ANCHOR_DRIFT (**弃权单列**, 绝不判绿); 文件/行不存在 ⇒ 弃权。
  · 快照面内出现**无条目**的对 ⇒ RED rc=2 (台账与快照不一致 = 覆盖缺口)。
  · 面是**活文档**: 现盘相对快照的漂移 (新增对 / 消失对 / 文件改写) 单列 `live_drift`, 默认 **非红**
    (其它写者随时在写) 但计数 + 明示 `REFRESH_NEEDED`; `--strict-live` 下漂移计红 (判别力控制臂)。
退出码: 0 无红 / 2 有红 / 3 环境失败 (弃权不当红)。
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
OUT = 'eval/capability/exp1-q33/caliber_void_audit_q33.json'
FACE_DIRS = ('docs/reports', 'docs/plans')
PAIR_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:→|->|⇒|vs\.?|至)\s*(\d+(?:\.\d+)?)')
CALIBER_MARK = ('口径', '两栏', '双栏', '不可比', '并列')
REQUIRED = ('id', 'file', 'line', 'pair', 'anchor_sha12', 'class', 'scope', 'supersedes', 'note',
            'owner_round')


def sha12(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def read_lines(path):
    if not os.path.exists(path):
        return None
    return open(path, encoding='utf-8', errors='replace').read().split('\n')


def live_pairs(root=None):
    """现盘面 (行含口径标记 ∧ 行含数值对); 与台账快照同口径。"""
    root = root or ROOT
    out = []
    for d in FACE_DIRS:
        if not os.path.isdir(os.path.join(root, d)):
            continue
        for fn in sorted(os.listdir(os.path.join(root, d))):
            if not fn.endswith('.md'):
                continue
            f = '%s/%s' % (d, fn)
            for i, ln in enumerate(read_lines(os.path.join(root, f)) or []):
                if ln.lstrip().startswith('|') and '---' in ln:
                    continue
                if not any(k in ln for k in CALIBER_MARK):
                    continue
                for m in PAIR_RE.finditer(ln):
                    out.append({'file': f, 'line': i + 1, 'pair': '%s→%s' % m.groups()})
    return out


def audit(ledger_path=LEDGER, strict_live=False, root=None):
    root = root or ROOT
    lp = os.path.join(root, ledger_path)
    if not os.path.exists(lp):
        return 3, {'error': 'LEDGER_MISSING', 'ledger': ledger_path}, []
    led = json.loads(open(lp, encoding='utf-8').read())
    entries = led.get('entries') or []
    snap = led.get('face_snapshot') or {}
    log = []
    problems = []
    for e in entries:
        miss = [k for k in REQUIRED if k not in e]
        if miss:
            log.append('MALFORMED_ENTRY %s 缺字段 %s' % (e.get('id'), miss))
            problems.append('MALFORMED_ENTRY:%s' % e.get('id'))
    if problems:
        return 3, {'error': 'LEDGER_MALFORMED', 'details': log}, log

    declared, drift, oor = [], [], []
    for e in entries:
        lines = read_lines(os.path.join(root, e['file']))
        if lines is None:
            oor.append({'id': e['id'], 'reason': 'file_missing', 'file': e['file']})
            continue
        idx = e['line'] - 1
        if idx < 0 or idx >= len(lines):
            oor.append({'id': e['id'], 'reason': 'line_out_of_range', 'file': e['file'], 'line': e['line']})
            continue
        line = lines[idx]
        if sha12(line) != e['anchor_sha12']:
            drift.append({'id': e['id'], 'file': e['file'], 'line': e['line'], 'pair': e['pair'],
                          'reason': 'anchor_sha12_mismatch', 'now_sha12': sha12(line)})
            continue
        in_line = {'%s→%s' % m.groups() for m in PAIR_RE.finditer(line)}
        if e['pair'] not in in_line:            # 由抽取器派生 (行内可能是 '->' / ' → ' 等形态)
            drift.append({'id': e['id'], 'file': e['file'], 'line': e['line'], 'pair': e['pair'],
                          'reason': 'pair_not_in_line', 'derived': sorted(in_line)})
            continue
        declared.append({'id': e['id'], 'class': e['class'], 'supersedes': e['supersedes'],
                         'scope': e['scope'], 'file': e['file'], 'line': e['line'], 'pair': e['pair']})

    # 快照 vs 现盘
    snapped = set()
    for f, meta in snap.get('files', {}).items():
        for p in meta.get('pairs', []):
            ln, pair = p.split(':', 1)
            snapped.add('%s:%s:%s' % (f, ln, pair))
    live = live_pairs(root)
    live_keys = {'%s:%d:%s' % (p['file'], p['line'], p['pair']) for p in live}
    new_keys = sorted(live_keys - snapped)
    gone_keys = sorted(snapped - live_keys)
    files_changed = []
    for f, meta in sorted(snap.get('files', {}).items()):
        lines = read_lines(os.path.join(root, f))
        now = sha12('\n'.join(lines)) if lines is not None else None
        if now != meta.get('file_sha12'):
            files_changed.append({'file': f, 'snapshot': meta.get('file_sha12'), 'now': now})

    # RED 语义 = 覆盖缺口: 快照对 ∩ 现盘对 中, 台账没有 DECLARED 记录者 (条目丢失/被改写)
    # 注意: 条目被改写会在上面记入 drift (弃权) —— 两者都不允许静默判绿。
    live_set = {(p['file'], p['line'], p['pair']) for p in live}
    snap_set = {(k.split(':')[0], int(k.split(':')[1]), k.split(':', 2)[2]) for k in snapped}
    entry_keys = {'%s:%d:%s' % (e['file'], e['line'], e['pair']) for e in entries}
    # RED = 快照面内某对**完全没有台账条目** (真覆盖缺口); 有条目但锚点/定位失配 ⇒ drift/oor (弃权, 不判绿)
    uncovered = sorted(['%s:%d:%s' % t for t in (snap_set & live_set) if ('%s:%d:%s' % t) not in entry_keys])
    if strict_live:
        uncovered = sorted(set(uncovered) | set(new_keys))

    by_class = {}
    for d in declared:
        by_class[d['class']] = by_class.get(d['class'], 0) + 1
    payload = {
        'round': 'EXP1-Q33', 'schema': 'caliber-void-audit/2', 'caliber': 'structured_fields'
                                                                        + ('+strict_live' if strict_live else ''),
        'ledger': ledger_path, 'ledger_sha12': sha12(open(lp, encoding='utf-8').read()),
        'n_entries': len(entries), 'n_declared': len(declared), 'n_anchor_drift': len(drift),
        'n_out_of_range': len(oor), 'n_uncovered': len(uncovered), 'n_red': len(uncovered),
        'reds': uncovered, 'drift': drift, 'out_of_range': oor, 'by_class': by_class,
        'live_drift': {'n_live_pairs': len(live), 'n_snapshot_pairs': len(snapped),
                       'n_new': len(new_keys), 'n_gone': len(gone_keys),
                       'new_sample': new_keys[:8], 'gone_sample': gone_keys[:8],
                       'files_changed': files_changed},
        # EXP1-Q34 判据收窄: 「需重审」= **候选对集合**发生变化 (新增/消失/未裁定) —— 只有它才会产生
        #   覆盖率缺口。面文件字节变化 (docs/plans 每轮被追加) 与覆盖面无关: 把它算进 refresh_needed
        #   会让该标志**恒真** (记录本轮审计的附录本身就是一次文件写入) ⇒ 真信号被噪声淹没。
        #   字节变化降级为信息项 face_files_changed (可追溯), 配对仍逐条由 ADJUDICATION 覆盖。
        'refresh_needed': bool(new_keys or gone_keys),
        'snapshot_sha_stale': bool(files_changed),
        'conservation': {'declared + drift + oor == entries': len(declared) + len(drift) + len(oor) == len(entries),
                         'declared': len(declared), 'drift': len(drift), 'oor': len(oor),
                         'entries': len(entries)},
        'caliber_note': ('判据绑**字段** (台账 class/scope/supersedes + anchor_sha12); 词面只用于面定义'
                         '(行含口径标记) 与 Q32 迁移证据。漂移/越界 = 弃权单列, 不判绿。'),
    }
    return (2 if uncovered else 0), payload, log


def selftest():
    """判别力自证 (6 例): 条目齐 ⇒ 绿; 快照对无条目 ⇒ RED; anchor 失配 ⇒ DRIFT 非红;
    文件缺失 ⇒ 弃权非红; 条目缺字段 ⇒ fail-closed rc=3; 面字节变化但候选对不变 ⇒ 非重审信号。"""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix='q33-caliber-')
    bad = 0
    try:
        os.makedirs(os.path.join(tmp, 'docs/reports'), exist_ok=True)
        doc = 'docs/reports/fixture.md'
        line_ok = '余量 2.019 → 2.010 (两栏并列声明: 旧口径作废)'
        line_other = '口径: 余量 9 → 8'
        open(os.path.join(tmp, doc), 'w', encoding='utf-8').write('# f\n' + line_ok + '\n' + line_other + '\n')
        cases = {}

        def mk(name, entries, extra_doc=None):
            p = os.path.join(tmp, 'ledger-%s.json' % name)
            if extra_doc:
                open(os.path.join(tmp, extra_doc[0]), 'w', encoding='utf-8').write(extra_doc[1])
            snap = {'n_files': 1, 'n_pairs': 2,
                    'files': {doc: {'file_sha12': sha12('# f\n' + line_ok + '\n' + line_other),
                                    'pairs': ['2:2.019→2.010', '3:9→8']}}}
            json.dump({'entries': entries, 'face_snapshot': snap}, open(p, 'w', encoding='utf-8'))
            return p

        base_entry = {'id': 'cd-001', 'file': doc, 'line': 2, 'pair': '2.019→2.010',
                      'anchor_sha12': sha12(line_ok), 'class': 'caliber_change_inline',
                      'scope': 'internal_caliber', 'supersedes': True, 'note': 'fixture',
                      'owner_round': 'SELFTEST'}
        other_entry = dict(base_entry, id='cd-002', pair='9→8', line=3, anchor_sha12=sha12(line_other))
        # 逐例: 显式把 root 指到夹具目录 (不依赖全局态)
        if True:
            rc, pay, _ = audit(mk('full', [base_entry, other_entry]), root=tmp)
            cases['both_entries_declared_green'] = (rc == 0 and pay['n_declared'] == 2)
            rc, pay, _ = audit(mk('missing_entry', [base_entry]), root=tmp)
            cases['snapshot_pair_without_entry_red'] = (rc == 2 and pay['n_red'] == 1 and pay['reds'][0].endswith('9→8'))
            rc, pay, _ = audit(mk('stale_anchor', [dict(base_entry, anchor_sha12='deadbeefdead'), other_entry]), root=tmp)
            cases['stale_anchor_is_drift_not_green'] = (rc == 0 and pay['n_anchor_drift'] == 1 and pay['n_declared'] == 1)
            # 缺文件的分支: 额外条目指向不存在的文件 (其 pair 不在快照面内) ⇒ 该条目弃权, 覆盖不受影响
            ghost = dict(base_entry, id='cd-003', file='docs/reports/nope.md', line=9, pair='1→2',
                         anchor_sha12='aaaaaaaaaaaa')
            rc, pay, _ = audit(mk('missing_file', [base_entry, other_entry, ghost]), root=tmp)
            cases['missing_file_is_abstain_not_red'] = (rc == 0 and pay['n_out_of_range'] == 1
                                                        and pay['n_red'] == 0 and pay['n_declared'] == 2)
            mal = dict(base_entry)
            mal.pop('class')
            rc, pay, _ = audit(mk('malformed', [mal, other_entry]), root=tmp)
            cases['malformed_entry_fail_closed'] = (rc == 3 and pay.get('error') == 'LEDGER_MALFORMED')
            # EXP1-Q34: 面文件**字节**变了但候选对集合不变 ⇒ 不是「需重审」。
            #   恒真陷阱: 记录本轮审计的附录本身就是一次面文件写入 ⇒ 旧判据 (bytes 变化即 refresh)
            #   会让 REFRESH_NEEDED 永远为真, 真信号(新增候选对)被噪声淹没。字节变化降为信息项。
            rc, pay, _ = audit(
                mk('bytes_only', [base_entry, other_entry],
                   extra_doc=(doc, '# f\n' + line_ok + '\n' + line_other + '\n' + '本轮新增附录 (审计自身产物)\n')),
                root=tmp)
            cases['bytes_churn_alone_is_not_refresh_needed'] = (
                rc == 0 and pay['refresh_needed'] is False and pay['snapshot_sha_stale'] is True
                and pay['n_declared'] == 2 and pay['n_red'] == 0)
        for k, v in cases.items():
            print('  %-40s %s' % (k, 'OK' if v else 'FAIL'))
            bad += 0 if v else 1
        n = len(cases)
        print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', n - bad, n))
        return 0 if bad == 0 else 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if '--selftest' in sys.argv:
        return selftest()
    strict = '--strict-live' in sys.argv
    ledger = LEDGER
    for i, a in enumerate(sys.argv):
        if a == '--ledger' and i + 1 < len(sys.argv):
            ledger = sys.argv[i + 1]
    rc, payload, log = audit(ledger, strict_live=strict)
    for l in log:
        print(l)
    if rc == 3:
        print('CALIBER_VOID=ABSTAIN (%s) rc=3' % payload.get('error'))
        return 3
    out = OUT if ledger == LEDGER else OUT.replace('.json', '_ctl.json')
    with open(os.path.join(ROOT, out), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('ENTRIES=%d DECLARED=%d DRIFT=%d OOR=%d UNCOVERED=%d'
          % (payload['n_entries'], payload['n_declared'], payload['n_anchor_drift'],
             payload['n_out_of_range'], payload['n_uncovered']))
    print('BY_CLASS=%s' % json.dumps(payload['by_class'], ensure_ascii=False))
    print('LIVE n_pairs=%d new=%d gone=%d files_changed=%d REFRESH_NEEDED=%s'
          % (payload['live_drift']['n_live_pairs'], payload['live_drift']['n_new'],
             payload['live_drift']['n_gone'], len(payload['live_drift']['files_changed']),
             payload['refresh_needed']))
    print('CONSERVATION=%s' % json.dumps(payload['conservation'], ensure_ascii=False))
    print('落盘 %s' % out)
    print('CALIBER_VOID=%s' % ('FAIL' if payload['n_red'] else 'OK'))
    return rc


if __name__ == '__main__':
    sys.exit(main())
