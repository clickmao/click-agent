#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q33 · C4: 面扩容重开条件**按字面**机检 (不扩面就说清为什么不扩)。

Q32 裁定 `N_MAX = 0` (可扩容器具数 = 0) 并写下重开条件 (`face_cap_recheck_q32.json.reopen_condition`)。
本轮新增 4 件器具 (口径结构化审计 / 依赖裁定 / 面记录确定化 / 本检查器) ⇒ 必须证明它们**没有**偷偷
扩 L2 面 (面别分区: 它们只在 `eval/**` 证据面), 并机检重开条件里的每个常数是否仍成立。

判据 (预注册 §criteria.C4):
  · 源真值 (soft_cap / k_min / hard_cap) 逐字等于 Q32 记录;
  · 面规模 == 27 ∧ 面内**无** exp1-q33 条目 (新器具未混入 L2 面);
  · N_MAX 由**现盘面体量**重算 == 0 (allowance < m_hist);
  · 磁盘余量 > 重开条件里的 needed_soft_cap_for_plus3 (75,497,472 B);
  · 负控: 夹具面 +1 条 ⇒ 必须报 FACE_SIZE_CHANGED (证明该闸非恒真)。
退出码: 0 达标 / 2 越线 / 3 环境失败。
"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
Q32 = 'eval/capability/exp1-q32/face_cap_recheck_q32.json'
MAN = 'eval/capability/instruments.json'
REC = 'eval/capability/instruments-check.json'
OUT = 'eval/capability/exp1-q33/reopen_condition_check_q33.json'
EXPECT_FACE = 27


def check(man_path=MAN, rec_path=REC, root=None):
    root = root or ROOT
    q = json.load(open(os.path.join(root, Q32), encoding='utf-8'))
    man = json.load(open(os.path.join(root, man_path), encoding='utf-8'))
    rec = json.load(open(os.path.join(root, rec_path), encoding='utf-8'))
    src = q['source_of_truth']
    rc_open = q['reopen_condition']
    n = len(man['instruments'])
    q33_in_face = [i['id'] for i in man['instruments']
                   if 'exp1-q33' in json.dumps(i, ensure_ascii=False) or 'q33' in i['id'].lower()]
    log_bytes = (rec.get('side_effect_attribution') or {}).get('trace', {}).get('log_bytes')
    m_hist = q['m_hist_bytes_per_instrument']
    allowance = src['soft_cap'] / src['k_min'] - log_bytes
    n_max = int(allowance // m_hist)
    disk_free = None
    for cand in ('/home/agentuser/AgentFramework', '/tmp'):
        try:
            disk_free = os.statvfs(cand).f_bavail * os.statvfs(cand).f_frsize
            break
        except OSError:
            continue
    verdicts = {
        'soft_cap_unchanged': src['soft_cap'] == 67108864,
        'k_min_unchanged': src['k_min'] == 2.0,
        'hard_cap_unchanged': src['hard_cap'] == 268435456,
        'reopen_needed_soft_cap_literal': rc_open['needed_soft_cap_for_plus3'] == 75497472,
        'face_size_is_27': n == EXPECT_FACE,
        'no_q33_entry_in_l2_face': not q33_in_face,
        'n_max_recomputed_is_0': n_max == 0,
        'disk_free_above_reopen_gate': disk_free is not None and disk_free > rc_open['needed_soft_cap_for_plus3'],
    }
    reds = [k for k, v in verdicts.items() if not v]
    return (2 if reds else 0), {
        'round': 'EXP1-Q33', 'schema': 'face-cap-reopen-check/1',
        'source_of_truth': src, 'reopen_condition_literal': rc_open,
        'live': {'n_instruments': n, 'q33_entries_in_l2_face': q33_in_face,
                 'face_log_bytes_from_record': log_bytes, 'm_hist_bytes_per_instrument': m_hist,
                 'allowance_bytes': allowance, 'n_max_recomputed': n_max,
                 'disk_free_bytes_now': disk_free},
        'verdicts': verdicts, 'n_red': len(reds), 'reds': reds,
        'decision': ('no-expand: 本轮 4 件新器具全部留在 `eval/**` 证据面, L2 面维持 27; '
                     '重开条件按字面执行 (soft_cap 72 MiB + 磁盘闸 + 重审 + 台账新行) —— 未触发, 故不扩'),
    }


def nc_fixture():
    """负控: 夹具面 +1 条 (在 scratch 根下复制最小输入) ⇒ 必须报 face_size 越线。"""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix='q33-reopen-')
    try:
        os.makedirs(os.path.join(tmp, 'eval/capability/exp1-q32'), exist_ok=True)
        shutil.copy(os.path.join(ROOT, Q32), os.path.join(tmp, Q32))
        man = json.load(open(os.path.join(ROOT, MAN), encoding='utf-8'))
        man['instruments'].append({'id': 'nc.extra', 'kind': 'probe',
                                   'cmd': 'python3 -c pass', 'expect_rc': 0, 'expect_substr': '',
                                   'nc_cmd': 'python3 -c "raise SystemExit(2)"', 'nc_expect': 'nonzero',
                                   'kpi_quad': {'单位': 'n/a', '分母': 'n/a', '真值源': 'n/a', '口径档': 'n/a'},
                                   'owner_round': 'NC', 'evidence_path': 'x',
                                   'instrument_sha12': '0' * 12})
        os.makedirs(os.path.join(tmp, 'eval/capability'), exist_ok=True)
        json.dump(man, open(os.path.join(tmp, MAN), 'w', encoding='utf-8'))
        shutil.copy(os.path.join(ROOT, REC), os.path.join(tmp, REC))
        rc, pay = check(root=tmp)
        ok = rc == 2 and 'face_size_is_27' in pay['reds']
        print('  NC face+1 => rc=%d reds=%s %s' % (rc, pay['reds'], 'OK' if ok else 'FAIL'))
        return 0 if ok else 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if '--nc' in sys.argv:
        return nc_fixture()
    rc, pay = check()
    with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(pay, ensure_ascii=False, indent=1) + '\n')
    print('FACE=%d  N_MAX_recomputed=%d  allowance=%.0f B  disk_free=%.2f GB'
          % (pay['live']['n_instruments'], pay['live']['n_max_recomputed'],
             pay['live']['allowance_bytes'], (pay['live']['disk_free_bytes_now'] or 0) / 1e9))
    print('VERDICTS=%s' % json.dumps(pay['verdicts'], ensure_ascii=False))
    print('落盘 %s' % OUT)
    print('REOPEN_CONDITION=%s' % ('OK' if not pay['n_red'] else 'VIOLATED %s' % pay['reds']))
    return rc


if __name__ == '__main__':
    sys.exit(main())
