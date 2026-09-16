#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C2: 面扩容前的阈值复测与 K_MIN 重定裁定 (数据先行; 先量体量再动面)。

预注册判据 (prereg_q32.json §criteria.C2):
  · 单一权威: soft_cap / K_MIN 从**器具源码**取 (side_effect_gate.py LOG_SOFT_CAP/HARD_CAP、
    face_cap_headroom.py K_MIN), 文档不作权威;
  · 不变式: soft_cap >= K_MIN × 实测 log_bytes;
  · m_hist = (Q31 bytes − Q30 bytes) / (27 − 21)  (台账两行实测, 同机同面口径);
  · N_max = floor((soft_cap/K_MIN − bytes) / m_hist); N_max < 1 ⇒ 本轮**不扩 L2 面** (新守卫登记为
    证据面器具, 不进 instruments.json), 并给出 cap 重锚算式与重开条件。

纪律: 台账 `face-scale-ledger.jsonl` 追加行的**键集必须与既有同族行逐键相同** (不做 schema 漂移);
裁定与算式落独立产物 `face_cap_recheck_q32.json`。幂等 (同 round 已存在同 log_bytes 行 ⇒ 不重复追加) +
追加前断言「序列化器逐字节复现原文件」+ 写后读回全文件逐行可解析。
退出码: 0 通过 (含幂等) / 2 断言失败 / 3 环境失败。
"""
import json
import os
import re
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
LEDGER = 'eval/capability/face-scale-ledger.jsonl'
REC = 'eval/capability/instruments-check.json'
OUT = 'eval/capability/exp1-q32/face_cap_recheck_q32.json'
ROUND = 'EXP1-Q32'


def parse_cap(src, name):
    m = re.search(r'%s\s*=\s*([0-9*\s]+)' % name, src)
    if not m:
        return None
    expr = m.group(1).strip().rstrip('*').strip()
    if not re.fullmatch(r'[0-9*\s]+', expr):
        return None
    v = 1
    for part in [p.strip() for p in expr.split('*') if p.strip()]:
        v *= int(part)
    return v


def main():
    raw = open(os.path.join(ROOT, LEDGER), encoding='utf-8', newline='').read()
    lines = [x for x in raw.split('\n') if x.strip()]
    rows = [json.loads(x) for x in lines]
    # 序列化器逐字节复现断言
    ser = '\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n'
    if ser != raw:
        print('SER_ASSERT=FAIL (逐字节序列化器不能复现台账 ⇒ 拒写)')
        return 3
    print('SER_ASSERT=OK (%d 行)' % len(rows))
    keysets = {tuple(r.keys()) for r in rows}
    if len(keysets) != 1:
        print('KEYSET_ASSERT=FAIL (既有行键集不唯一: %s)' % [sorted(k) for k in keysets])
        return 3

    rec = json.load(open(os.path.join(ROOT, REC), encoding='utf-8'))
    trace = (rec.get('side_effect_attribution') or {}).get('trace') or {}
    lb, cmds, capped = trace.get('log_bytes'), trace.get('commands'), trace.get('capped')
    n_ins = rec.get('total')
    if not isinstance(lb, int) or lb <= 0 or not cmds:
        print('ENV_FAIL: 面记录缺 log_bytes/commands ⇒ 弃权 (不判红不判绿)')
        return 3

    src = open(os.path.join(ROOT, 'eval/capability/exp1-q22/side_effect_gate.py'), encoding='utf-8',
               errors='replace').read()
    hsrc = open(os.path.join(ROOT, 'eval/capability/exp1-q31/instruments/face_cap_headroom.py'),
                encoding='utf-8', errors='replace').read()
    soft, hard = parse_cap(src, 'LOG_SOFT_CAP'), parse_cap(src, 'LOG_HARD_CAP')
    kmin = float(re.search(r'K_MIN\s*=\s*([\d.]+)', hsrc).group(1))
    if not soft or not hard:
        print('ENV_FAIL: 未能从源码派生 LOG_SOFT_CAP/LOG_HARD_CAP')
        return 3
    headroom = round(soft / lb, 3)

    # 历史两点 → 每器具边际字节
    prev = [r for r in rows if r['round'] == 'EXP1-Q31']
    m_hist = None
    if len(prev) >= 2:
        a, b = prev[0], prev[-1]
        m_hist = (b['log_bytes'] - a['log_bytes']) / (b['n_instruments'] - a['n_instruments'])
    allowance = int(soft / kmin - lb)
    n_max = int(allowance // m_hist) if m_hist else None
    target3 = int(lb + 3 * m_hist) if m_hist else None
    cap_need3 = int(kmin * target3) if target3 else None
    cap_need3_8mib = ((cap_need3 + 8 * 1024 * 1024 - 1) // (8 * 1024 * 1024)) * 8 * 1024 * 1024 if cap_need3 else None

    df = subprocess.run(['df', '-B1', '--output=avail', '/'], capture_output=True, text=True).stdout.split()
    disk_free = int(df[-1]) if df and df[-1].isdigit() else None

    payload = {'round': ROUND, 'schema': 'face-cap-recheck/1',
               'source_of_truth': {'soft_cap': soft, 'hard_cap': hard, 'k_min': kmin,
                                   'derived_from': ['eval/capability/exp1-q22/side_effect_gate.py',
                                                    'eval/capability/exp1-q31/instruments/face_cap_headroom.py']},
               'face': {'n_instruments': n_ins, 'n_commands': cmds, 'log_bytes': lb, 'capped': capped,
                        'headroom': headroom, 'manifest_sha12': rec.get('manifest_sha12')},
               'stability_two_readings': [33388259, lb],
               'm_hist_bytes_per_instrument': round(m_hist, 1) if m_hist else None,
               'allowance_bytes_at_kmin': allowance,
               'n_max_expandable_instruments': n_max,
               'decision': ('no-expand: L2 面不扩容; 本轮新守卫登记为**证据面器具** (面别分区), '
                            '并记下沿与重开条件' if (n_max is not None and n_max < 1) else 'expand-allowed'),
               'reopen_condition': {
                   'trigger': '需要新增 L2 面器具 (面别分区不适用) 时',
                   'needed_soft_cap_for_plus3': cap_need3_8mib,
                   'formula': 'ceil8MiB(k_min × (log_bytes + 3 × m_hist))',
                   'disk_gate_bytes_free_now': disk_free,
                   'hard_cap_now': hard},
               'kpi_quad': {'单位': '面', '分母': '器具面规模', '真值源': '全量面记录 side_effect_attribution.trace',
                            '口径档': 'log_bytes(字节)/命令数'}}

    newrow = {'round': ROUND, 'face_record': REC, 'face_manifest_sha12': rec.get('manifest_sha12'),
              'instrument_sha12': rec.get('instrument_sha12'), 'n_instruments': n_ins,
              'n_commands': cmds, 'log_bytes': lb, 'capped': bool(capped), 'soft_cap': soft,
              'hard_cap': hard, 'headroom': headroom, 'k_min': kmin, 'kpi_quad': payload['kpi_quad']}
    if set(newrow.keys()) != set(keysets.pop()):
        print('KEYSET_ASSERT=FAIL (新行键集 != 既有同族行键集)')
        return 3
    dup = [r for r in rows if r['round'] == ROUND and r['log_bytes'] == lb]
    if dup:
        print('IDEMPOTENT=OK (台账已含同轮同读数行)')
    else:
        rows.append(newrow)
        out = '\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n'
        open(os.path.join(ROOT, LEDGER), 'w', encoding='utf-8', newline='').write(out)
        back = open(os.path.join(ROOT, LEDGER), encoding='utf-8', newline='').read()
        print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
        if back != out:
            return 2
        ok_parse = all(json.loads(x) for x in back.strip().split('\n'))
        print('READBACK_PARSE=%s (%d 行)' % ('OK' if ok_parse else 'FAIL', len(back.strip().split('\n'))))

    with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('FACE_SCALE n=%s commands=%s log_bytes=%s headroom=%s (K_MIN=%s soft=%s)'
          % (n_ins, cmds, lb, headroom, kmin, soft))
    print('MARGINAL m_hist=%s B/器具 | ALLOWANCE=%s B | N_MAX=%s' % (payload['m_hist_bytes_per_instrument'],
                                                                     allowance, n_max))
    print('DECISION %s' % payload['decision'])
    print('REOPEN +3 器具 ⇒ soft_cap 需 %s (现 %s); 磁盘可用 %s B'
          % (cap_need3_8mib, soft, disk_free))
    print('落盘 %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
