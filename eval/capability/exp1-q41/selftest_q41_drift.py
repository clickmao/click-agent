#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q41 · H6 成对控制: 冻结证据漂移 (FROZEN_EVIDENCE_DRIFT) 的**噪声 / 可见性**两态。

构造成分 (复刻 EXP1-Q40 ③ 的成对控制做法, 不自己发明):
  ① 真登记表**逐字节复制**到 /tmp scratch (真表零写入; 收尾核 sha256);
  ② 追加一行夹具行: level ∈ COVER_LEVELS ∧ evidence_path = 一个**工作区脏但 HEAD 有 blob**的件
     (HEAD sha12 ≠ 现盘 sha12 ⇒ 「名义脏但字节相同」被显式排除), pin_status=frozen, artifact_sha12 = **HEAD 侧** sha12
     ⇒ 归档自洽 (pin 等于 HEAD 记录) ∧ 工作区漂移 ⇒ 正是 drift 的语义;
  ③ 同一 scratch 上把 pin 改成假值 ⇒ 必须落 VIOLATION (判红) —— 证明红路没被关掉 (成对)。

判据:
  H6a 真仓干净态: bind_evidence --check 的明细行 (FROZEN_DRIFT) = 0 ∧ 通知件**零输出**
  H6b 漂移态: FROZEN_EVIDENCE_DRIFT >= 1 ∧ 通知件**逐条可见**且退出码 0 (永不判红)
  H6c 成对: 同 scratch 假 pin ⇒ rc=2 (VIOLATION)
三态退出码: 0 全绿 / 2 判据红 / 3 环境不可判。
"""
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = 'docs/verification-registry.json'
SCRATCH = pathlib.Path('/tmp/q41_scratch_drift')
FIX_ID = 'q41.fixture-drift-control'
NOTICE = 'eval/capability/exp1-q41/commit_face_notice_q41.py'
PREFIXES = ('src/', 'eval/', 'docs/', 'tools/', 'scripts/')
COVER_LEVELS = ('L2', 'L3', 'L4')


def sh12(b):
    return hashlib.sha256(b).hexdigest()[:12]


def run(args):
    p = subprocess.run(['python3'] + args, cwd=str(ROOT), capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def git_show_head(rel):
    p = subprocess.run(['git', 'show', 'HEAD:%s' % rel], cwd=str(ROOT), capture_output=True)
    return p.stdout if p.returncode == 0 else None


def pick_dirty_file():
    """现场选取「HEAD 有 blob ∧ 现盘字节不同 ∧ 前缀在作用集内」的件 (不写死路径)。"""
    p = subprocess.run(['git', 'status', '--porcelain'], cwd=str(ROOT), capture_output=True, text=True)
    for ln in p.stdout.splitlines():
        if not ln.strip() or ln[:2].strip() == '??':
            continue
        rel = ln[3:].strip()
        if not rel.startswith(PREFIXES) or not (ROOT / rel).is_file():
            continue
        blob = git_show_head(rel)
        if blob is None:
            continue
        disk = (ROOT / rel).read_bytes()
        if sh12(disk) == sh12(blob):
            continue
        return rel, sh12(blob), sh12(disk)
    return None, None, None


def make_scratch(path, ev_rel, pin):
    raw = (ROOT / REG).read_text(encoding='utf-8')
    doc = json.loads(raw)
    doc['rows'].append({
        'id': FIX_ID, 'owner_round': 'EXP1-Q41', 'level': 'L2',
        'capability': 'EXP1-Q41 夹具行: 工作区脏的冻结证据 (非产品能力, 仅供成对控制)',
        'evidence_cmd': 'python3 eval/capability/exp1-q41/selftest_q41_drift.py',
        'evidence_path': ev_rel,
        'evidence_generated_with': {'evidence_kind': 'artifact', 'pin_status': 'frozen',
                                    'pin_reason': 'archived-per-round', 'artifact_sha12': pin,
                                    'instrument': None, 'instrument_sha12': None,
                                    'binding': 'audit-pin', 'audited_by_round': 'EXP1-Q40'},
        'negative_control': '同 scratch 把 pin 改假值 ⇒ --check 必须判红 (H6c)',
        'covers': [ev_rel], 'note': '夹具行只活在 /tmp scratch; 真登记表零写入',
    })
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='')
    return path


def drift_n(log):
    for ln in log.splitlines():
        if ln.startswith('FROZEN_EVIDENCE_DRIFT='):
            try:
                return int(ln.split('=')[1].split()[0])
            except (IndexError, ValueError):
                return None
    return None


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    reg_before = sh12((ROOT / REG).read_bytes())
    ev_rel, head_pin, disk_pin = pick_dirty_file()
    if not ev_rel:
        print('Q41_DRIFT: 现场无「HEAD≠现盘」的件 ⇒ rc=3 (环境不可判, 不伪造)')
        return 3
    out = {'fixture_evidence': ev_rel, 'head_sha12': head_pin, 'disk_sha12': disk_pin,
           'registry_sha12_before': reg_before}

    # H6b 漂移态 (pin = HEAD 侧)
    sp = make_scratch(SCRATCH / 'reg_drift.json', ev_rel, head_pin)
    rc_d, log_d = run(['eval/capability/bind_evidence.py', '--check', '--registry', str(sp)])
    (SCRATCH / 'log_drift.txt').write_text(log_d, encoding='utf-8')
    n_d = drift_n(log_d)
    rc_n, out_n = run([NOTICE, '--log', str(SCRATCH / 'log_drift.txt')])
    v_n = read_notice(SCRATCH / 'log_drift.txt')

    # H6c 成对: 假 pin ⇒ 判红
    sp_bad = make_scratch(SCRATCH / 'reg_bogus.json', ev_rel, '000000000000')
    rc_b, log_b = run(['eval/capability/bind_evidence.py', '--check', '--registry', str(sp_bad)])
    out['H6c_bogus_pin'] = {'rc': rc_b, 'violations': log_b.count('VIOLATION')}

    # H6a 干净态 (真仓)
    rc_c, log_c = run(['eval/capability/bind_evidence.py', '--check'])
    (SCRATCH / 'log_clean.txt').write_text(log_c, encoding='utf-8')
    rc_nc, out_nc = run([NOTICE, '--log', str(SCRATCH / 'log_clean.txt')])

    reg_after = sh12((ROOT / REG).read_bytes())
    out.update({
        'H6b_drift_fixture': {'drift_n': n_d, 'rc_check': rc_d,
                              'notice_rc': rc_n, 'notice_visible': v_n},
        'H6a_clean_real_repo': {'drift_n': drift_n(log_c), 'notice_rc': rc_nc, 'notice_output': out_nc.strip()},
        'registry_untouched': reg_before == reg_after,
    })
    out['verdict'] = {
        'H6a_zero_noise': (drift_n(log_c) == 0 and out_nc.strip() == '' and rc_nc == 0),
        'H6b_drift_visible': (n_d is not None and n_d >= 1 and v_n >= 1 and rc_n == 0),
        'H6c_pair_red_preserved': out['H6c_bogus_pin']['rc'] == 2,
        'registry_untouched': out['registry_untouched'],
    }
    ok = all(out['verdict'].values())
    out['exit_code'] = 0 if ok else 2
    (HERE / 'selftest_q41_drift.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n',
                                                  encoding='utf-8')
    print('Q41_DRIFT fixture=%s head=%s disk=%s' % (ev_rel, head_pin, disk_pin))
    print('Q41_DRIFT H6b drift_n=%s notice_visible=%s rc=%s' % (n_d, v_n, rc_n))
    print('Q41_DRIFT H6a clean drift_n=%s notice_out=%r' % (drift_n(log_c), out_nc.strip()))
    print('Q41_DRIFT H6c bogus_pin rc=%s violations=%s' % (rc_b, out['H6c_bogus_pin']['violations']))
    print('Q41_DRIFT registry_untouched=%s verdict=%s' % (out['registry_untouched'], out['verdict']))
    print('Q41_DRIFT_EXIT=%d' % out['exit_code'])
    return out['exit_code']


def read_notice(log_path):
    p = subprocess.run(['python3', NOTICE, '--log', str(log_path)], cwd=str(ROOT),
                       capture_output=True, text=True)
    return len([ln for ln in p.stderr.splitlines() if ln.strip()])


if __name__ == '__main__':
    sys.exit(main())
