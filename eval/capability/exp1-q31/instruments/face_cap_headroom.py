#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C4: 器具面规模 × 归因闸阈值台账 (阈值随面规模复测, 数据先行)。

背景 (Q30 AE.6⑤): `LOG_SOFT_CAP=64MiB` 是按 **21 器具 / 47 命令** 实测定的 (实测 28.3 MiB, 余量 ~2.2×)。
器具面继续扩容会再次逼近上限, 而越界语义是 `capped ⇒ 弃权 rc=3` —— 即**阈值过小会让整面悄悄弃权**
(读数消失而非报错)。本器把「面规模 → 阈值 → 余量」钉成可复测的记录项 + 机检判据。

判据:
  P1 阈值单一权威: 从器具源码 (eval/capability/exp1-q22/side_effect_gate.py) 读常量, 不复制数字;
  P2 soft_cap >= K_MIN * 实测 log_bytes (K_MIN = 2.0);
  P3 capped=True 的读数 ⇒ 红 (rc=2);
  N2 缺 log_bytes / 面记录缺失 ⇒ 弃权 (rc=3) —— 不判红不判绿。
用法:
  python3 .../face_cap_headroom.py --check [--record <face.json>]
  python3 .../face_cap_headroom.py --append           # 幂等追加台账
  python3 .../face_cap_headroom.py --selftest
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
GATE = 'eval/capability/exp1-q22/side_effect_gate.py'
FACE = 'eval/capability/instruments-check.json'
LEDGER = 'eval/capability/face-scale-ledger.jsonl'
K_MIN = 2.0


def load_gate():
    spec = importlib.util.spec_from_file_location('seg_q31', os.path.join(ROOT, GATE))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def verdict(record, soft, hard, k_min=K_MIN):
    """纯函数: (面记录, 阈值) -> (violations, readings, exitcode)。"""
    v, r = [], {}
    at = (record or {}).get('side_effect_attribution') or {}
    trace = at.get('trace') or {}
    r['total'] = record.get('total')
    r['commands'] = trace.get('commands')
    r['log_bytes'] = trace.get('log_bytes')
    r['capped'] = trace.get('capped')
    r['soft_cap'] = soft
    r['hard_cap'] = hard
    if trace.get('capped') is True:
        v.append('P3 capped=True: 阈值对当前面规模过小 ⇒ 整面弃权 (soft=%d, log_bytes=%r)'
                 % (soft, trace.get('log_bytes')))
    if not isinstance(trace.get('log_bytes'), int) or trace.get('log_bytes') <= 0:
        return v, r, 3                      # 弃权: 没测到体量
    r['headroom'] = round(soft / trace['log_bytes'], 3)
    if soft < k_min * trace['log_bytes']:
        v.append('P2 余量不足: soft_cap/log_bytes=%.3f < K_MIN=%.2f ⇒ 扩面前先复测并抬阈值'
                 % (r['headroom'], k_min))
    return v, r, (2 if v else 0)


FIXTURES = [
    ('green', {'total': 24, 'side_effect_attribution': {'trace': {'commands': 52, 'log_bytes': 30_000_000, 'capped': False}}}, 67108864, 268435456, 0),
    ('nc_capped', {'total': 24, 'side_effect_attribution': {'trace': {'commands': 52, 'log_bytes': 90_000_000, 'capped': True}}}, 67108864, 268435456, 2),
    ('nc_no_headroom', {'total': 60, 'side_effect_attribution': {'trace': {'commands': 150, 'log_bytes': 60_000_000, 'capped': False}}}, 67108864, 268435456, 2),
    ('nc_missing_bytes', {'total': 3, 'side_effect_attribution': {'trace': {'capped': False}}}, 67108864, 268435456, 3),
]


def selftest():
    bad = 0
    for name, rec, soft, hard, want in FIXTURES:
        v, r, rc = verdict(rec, soft, hard)
        ok = (rc == want)
        if not ok:
            bad += 1
        print('%-20s expect_rc=%d got=%d headroom=%s viol=%d %s'
              % (name, want, rc, r.get('headroom'), len(v), 'OK' if ok else 'FAIL'))
    print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', len(FIXTURES) - bad, len(FIXTURES)))
    return 0 if bad == 0 else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    # EXP1-Q36: 轮号**参数化** —— 旧版把 payload['round'] 硬编码为 'EXP1-Q31' ⇒ 跨轮追加会把本轮
    #   读数记到 Q31 名下 (归属错标)。--append 时缺 --round ⇒ fail-closed 拒跑 (不用默认值静默记账)。
    rnd = sys.argv[sys.argv.index('--round') + 1] if '--round' in sys.argv else None
    if '--append' in sys.argv and not rnd:
        print('ENV_FAIL (fail-closed): --append 必须显式带 --round <轮号> '
              '(行内 round 不得硬编码, 也不得用默认值)')
        return 3
    rnd = rnd or 'UNSPECIFIED'
    rec_path = sys.argv[sys.argv.index('--record') + 1] if '--record' in sys.argv else FACE
    rec_abs = os.path.join(ROOT, rec_path)
    if not os.path.isfile(rec_abs):
        print('ENV_FAIL (弃权): 面记录不存在 %s' % rec_path)
        return 3
    rec = json.load(open(rec_abs, encoding='utf-8-sig'))
    g = load_gate()
    soft, hard = g.LOG_SOFT_CAP, g.LOG_HARD_CAP
    print('CAP_SOURCE %s LOG_SOFT_CAP=%d LOG_HARD_CAP=%d' % (GATE, soft, hard))
    v, r, rc = verdict(rec, soft, hard)
    payload = {
        'round': rnd, 'face_record': rec_path,
        'face_manifest_sha12': rec.get('manifest_sha12'), 'instrument_sha12': rec.get('instrument_sha12'),
        'n_instruments': rec.get('total'), 'n_commands': r.get('commands'),
        'log_bytes': r.get('log_bytes'), 'capped': r.get('capped'),
        'soft_cap': soft, 'hard_cap': hard, 'headroom': r.get('headroom'), 'k_min': K_MIN,
        'kpi_quad': {'单位': '面', '分母': '器具面规模', '真值源': '全量面记录 side_effect_attribution.trace',
                     '口径档': 'log_bytes(字节)/命令数'},
    }
    print('FACE_SCALE n_instruments=%s n_commands=%s log_bytes=%s headroom=%s'
          % (payload['n_instruments'], payload['n_commands'], payload['log_bytes'], payload['headroom']))
    for x in v:
        print('  VIOLATION %s' % x)
    if '--append' in sys.argv and rc in (0, 2):
        led = os.path.join(ROOT, LEDGER)
        key = (payload['round'], payload['face_manifest_sha12'], payload['n_instruments'],
               payload['n_commands'], payload['log_bytes'])
        seen = set()
        rows = []
        if os.path.isfile(led):
            for line in open(led, encoding='utf-8-sig'):
                line = line.strip()
                if not line:
                    continue
                j = json.loads(line)
                rows.append(j)
                seen.add((j.get('round'), j.get('face_manifest_sha12'), j.get('n_instruments'),
                          j.get('n_commands'), j.get('log_bytes')))
        if key in seen:
            print('LEDGER_IDEMPOTENT=OK (同键已存在, 不追加)')
        else:
            with open(led, 'a', encoding='utf-8', newline='') as f:
                f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            back = [json.loads(l) for l in open(led, encoding='utf-8-sig') if l.strip()]
            print('LEDGER_APPENDED rows=%d (读回校验 %s)' % (len(back), 'OK' if len(back) == len(rows) + 1 else 'MISMATCH'))
            if len(back) != len(rows) + 1:
                return 2
    print('CAP_HEADROOM=%s (rc=%d)' % ('FAIL' if rc == 2 else ('ABSTAIN' if rc == 3 else 'OK'), rc))
    return rc


if __name__ == '__main__':
    sys.exit(main())
