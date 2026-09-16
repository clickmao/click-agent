#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q34 · 候选③ 台账追加: 把本轮全量面规模 × 阈值余量读数落 `face-scale-ledger.jsonl`。

为什么另立入口 (而不直接给器具加 `--round`): 器具 `eval/capability/exp1-q31/instruments/face_cap_headroom.py`
**本身是全量面的成员** (`exp1q31.cap-headroom`) —— 面在跑时改它的字节 = 测到一半换被测物
(harness 纪律「测旧二进制」同类事故), 且会让记录里的成员 sha 与现盘分叉, 下轮面**恒红假警**。
⇒ 复用器具的判据 (importlib 调用, 不复制一份阈值逻辑), 台账轮号由本入口注入:
   轮号是「谁记的」而非「判据是什么」, 判据单源、轮号参数化。

用法: python3 eval/capability/exp1-q34/append_ledger_q34.py [--round EXP1-Q34] [--record <face.json>]
幂等键 = (face_manifest_sha12, n_instruments, n_commands, log_bytes); 追加后读回校验行数 +1。
"""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      cwd=HERE, check=False).stdout.strip() or os.getcwd()
INSTR = 'eval/capability/exp1-q31/instruments/face_cap_headroom.py'
LEDGER = 'eval/capability/face-scale-ledger.jsonl'
FACE = 'eval/capability/instruments-check.json'


def load_instrument():
    spec = importlib.util.spec_from_file_location('cap_q31', os.path.join(ROOT, INSTR))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    args = sys.argv[1:]
    rnd = args[args.index('--round') + 1] if '--round' in args else 'EXP1-Q34'
    rec_rel = args[args.index('--record') + 1] if '--record' in args else FACE
    rec_abs = os.path.join(ROOT, rec_rel)
    if not os.path.isfile(rec_abs):
        print('ENV_FAIL (弃权): 面记录不存在 %s' % rec_rel)
        return 3
    rec = json.load(open(rec_abs, encoding='utf-8-sig'))
    ins = load_instrument()
    g = ins.load_gate()
    v, r, rc = ins.verdict(rec, g.LOG_SOFT_CAP, g.LOG_HARD_CAP)
    payload = {
        'round': rnd, 'face_record': rec_rel,
        'face_manifest_sha12': rec.get('manifest_sha12'),
        'instrument_sha12': rec.get('instrument_sha12'),
        'n_instruments': rec.get('total'), 'n_commands': r.get('commands'),
        'log_bytes': r.get('log_bytes'), 'capped': r.get('capped'),
        'soft_cap': g.LOG_SOFT_CAP, 'hard_cap': g.LOG_HARD_CAP,
        'headroom': r.get('headroom'), 'k_min': ins.K_MIN,
        'kpi_quad': {'单位': '面', '分母': '器具面规模', '真值源': '全量面记录 side_effect_attribution.trace',
                     '口径档': 'log_bytes(字节)/命令数'},
    }
    print('FACE_SCALE n_instruments=%s n_commands=%s log_bytes=%s headroom=%s rc=%d'
          % (payload['n_instruments'], payload['n_commands'], payload['log_bytes'], payload['headroom'], rc))
    for x in v:
        print('  VIOLATION %s' % x)
    if rc == 3:
        print('LEDGER_ABSTAIN (没测到体量, 不追加)')
        return 3
    led = os.path.join(ROOT, LEDGER)
    rows, seen = [], set()
    if os.path.isfile(led):
        for line in open(led, encoding='utf-8-sig'):
            line = line.strip()
            if not line:
                continue
            j = json.loads(line)
            rows.append(j)
            seen.add((j.get('face_manifest_sha12'), j.get('n_instruments'), j.get('n_commands'),
                      j.get('log_bytes')))
    key = (payload['face_manifest_sha12'], payload['n_instruments'], payload['n_commands'],
           payload['log_bytes'])
    if key in seen:
        print('LEDGER_IDEMPOTENT=OK (同键已存在, 不追加) rows=%d' % len(rows))
        return 0
    with open(led, 'a', encoding='utf-8', newline='') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    back = [json.loads(l) for l in open(led, encoding='utf-8-sig') if l.strip()]
    ok = len(back) == len(rows) + 1
    print('LEDGER_APPENDED rows=%d (读回校验 %s) round=%s' % (len(back), 'OK' if ok else 'MISMATCH', rnd))
    print('LEDGER_EXIT=%d' % (0 if ok else 2))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
